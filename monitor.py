# -*- coding: utf-8 -*-
"""
監控川普 Truth Social 新貼文 → 發 Telegram + Discord
策略：先試官方 API，被 Cloudflare 擋就退回 trumpstruth.org RSS
去重：用 repo 內的 seen.json 記住看過的貼文 ID
"""
import os
import re
import json
import requests
import feedparser  # 解析 RSS 用

# === 設定 ===
TRUMP_ID = "107780249214731732"            # 川普固定帳號 ID
API_URL = f"https://truthsocial.com/api/v1/accounts/{TRUMP_ID}/statuses"
RSS_URL = "https://trumpstruth.org/feed"
SEEN_FILE = "seen.json"
MAX_SEEN = 200                              # seen.json 只留最近 200 筆，避免無限變大

# 從環境變數讀密碼（GitHub Secrets 注入，不寫死在程式裡）
TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def strip_html(text):
    """簡單去掉 HTML 標籤，讓貼文好讀"""
    return re.sub(r"<[^>]*>", "", text or "").strip()


def fetch_from_api():
    """方案 A：直打官方 API。成功回 list，失敗回 None"""
    try:
        r = requests.get(
            API_URL,
            headers=HEADERS,
            params={"limit": 5, "exclude_replies": "true"},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            # 統一格式：{id, text, url}
            return [
                {"id": str(p["id"]),
                 "text": strip_html(p.get("content", "")),
                 "url": p.get("url", "")}
                for p in data
            ]
        print(f"[API] 被擋或失敗，status={r.status_code}，改用 RSS")
        return None
    except Exception as e:
        print(f"[API] 例外：{e}，改用 RSS")
        return None


def fetch_from_rss():
    """方案 B：退回 trumpstruth.org RSS"""
    feed = feedparser.parse(RSS_URL)
    posts = []
    for entry in feed.entries[:5]:
        posts.append({
            "id": entry.get("id") or entry.get("link"),  # guid 當唯一 ID
            "text": strip_html(entry.get("title", "")),
            "url": entry.get("link", ""),
        })
    return posts


def load_seen():
    """讀已看過的 ID 清單"""
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_seen(seen):
    """存回 ID 清單（只留最近 MAX_SEEN 筆）"""
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen[-MAX_SEEN:], f, ensure_ascii=False, indent=2)


def send_telegram(text):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT_ID, "text": text},
        timeout=15,
    )


def send_discord(text):
    requests.post(DISCORD_WEBHOOK, json={"content": text}, timeout=15)


def main():
    # 1. 抓貼文：先 API，失敗退 RSS
    posts = fetch_from_api()
    if posts is None:
        posts = fetch_from_rss()

    # 2. 比對去重
    seen = load_seen()
    new_posts = [p for p in posts if p["id"] not in seen]

    if not new_posts:
        print("沒有新貼文")
        return

    # 3. 發通知（舊到新）+ 記錄 ID
    for p in reversed(new_posts):
        msg = f"🦅 川普新貼文\n\n{p['text']}\n\n🔗 {p['url']}"
        send_telegram(msg)
        send_discord(msg)
        seen.append(p["id"])
        print(f"已通知：{p['id']}")

    save_seen(seen)


if __name__ == "__main__":
    main()
