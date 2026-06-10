# -*- coding: utf-8 -*-
"""
監控川普 Truth Social 新貼文 → 發 Telegram + Discord

執行模式（兩種，預設常駐）：
- **常駐 worker（預設）**：`python monitor.py` → 無限迴圈，每 INTERVAL_SEC 秒檢查一次。
  跑在免費雲端 24/7（見 SELF_HOSTING.md），不靠 GitHub Actions cron。
  → 為什麼換掉 GH Actions：`schedule:` cron 是 best-effort，會被延遲數小時、堆積觸發被合併，
    所以「每 5 分」實際跑成「每幾小時、一次吐一批」。常駐迴圈才有真正穩定的 5 分鐘節奏。
- **單次模式**：設環境變數 `RUN_ONCE=1` → 只檢查一次就結束（給 workflow_dispatch / 手動測試用）。

策略：先試官方 API，被 Cloudflare 擋就退回 trumpstruth.org RSS。
去重：用 seen.json 記住看過的貼文 ID（常駐進程也保留在記憶體，跨輪去重）。
"""
import os
import re
import json
import time
import requests
import feedparser  # 解析 RSS 用

# === 設定 ===
TRUMP_ID = "107780249214731732"            # 川普固定帳號 ID
API_URL = f"https://truthsocial.com/api/v1/accounts/{TRUMP_ID}/statuses"
RSS_URL = "https://trumpstruth.org/feed"
SEEN_FILE = "seen.json"
MAX_SEEN = 200                              # seen.json 只留最近 200 筆，避免無限變大

# 每輪抓最新幾篇。調高（原本 5）→ 即使某輪延遲/重啟造成空檔，也不會吞掉第 6 篇起的舊貼文。
FETCH_LIMIT = int(os.getenv("FETCH_LIMIT", "20"))
# 常駐迴圈每隔幾秒檢查一次（預設 300 = 5 分鐘）。
INTERVAL_SEC = int(os.getenv("INTERVAL_SEC", "300"))

# 從環境變數讀密碼（雲端 host / GitHub Secrets 注入，不寫死在程式裡）
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


def fetch_from_api(limit=FETCH_LIMIT):
    """方案 A：直打官方 API。成功回 list，失敗回 None"""
    try:
        r = requests.get(
            API_URL,
            headers=HEADERS,
            params={"limit": limit, "exclude_replies": "true"},
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


def fetch_from_rss(limit=FETCH_LIMIT):
    """方案 B：退回 trumpstruth.org RSS"""
    feed = feedparser.parse(RSS_URL)
    posts = []
    for entry in feed.entries[:limit]:
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
    r = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT_ID, "text": text},
        timeout=15,
    )
    if not r.ok:
        raise RuntimeError(f"Telegram 發送失敗 {r.status_code}: {r.text}")


def send_discord(text):
    r = requests.post(DISCORD_WEBHOOK, json={"content": text}, timeout=15)
    if not r.ok:
        raise RuntimeError(f"Discord 發送失敗 {r.status_code}: {r.text}")


def run_once(seen, *, seed_only=False):
    """
    跑一輪檢查：抓貼文 → 比對 seen → （seed_only=False 時）發通知。

    :param seen: 已看過的 ID 清單（會就地更新；常駐迴圈跨輪共用同一份）。
    :param seed_only: True = 只把目前貼文記進 seen、不發送。用於「冷啟動防洗頻」：
        雲端免費方案多為 ephemeral 檔案系統，重啟後 seen.json 會消失。若不 seed，
        第一輪會把最新一批舊貼文當成全新的整批重發。seed 後它們進 seen，下輪起才正常推新文。
    :return: 這輪實際發送的則數。
    """
    posts = fetch_from_api()
    if posts is None:
        posts = fetch_from_rss()

    new_posts = [p for p in posts if p["id"] not in seen]
    if not new_posts:
        print("沒有新貼文")
        return 0

    if seed_only:
        for p in new_posts:
            seen.append(p["id"])
        print(f"冷啟動 seed：記錄 {len(new_posts)} 筆既有貼文（不發送）")
        return 0

    # 發通知（舊到新）+ 記錄 ID
    sent = 0
    for p in reversed(new_posts):
        msg = f"🦅 川普新貼文\n\n{p['text']}\n\n🔗 {p['url']}"
        send_telegram(msg)
        send_discord(msg)
        seen.append(p["id"])
        sent += 1
        print(f"已通知：{p['id']}")
    return sent


def main():
    """常駐迴圈：每 INTERVAL_SEC 秒檢查一次。單輪失敗只記錄、不讓整支崩。"""
    seen = load_seen()
    # 沒有任何歷史（首跑 / ephemeral 重啟後 seen.json 不見）→ 第一輪只記錄不發，避免洗頻。
    seed_first = len(seen) == 0
    print(f"[monitor] 啟動：每 {INTERVAL_SEC}s 檢查一次、抓最新 {FETCH_LIMIT} 篇"
          + ("（冷啟動第一輪只記錄不發）" if seed_first else ""))
    while True:
        try:
            run_once(seen, seed_only=seed_first)
            save_seen(seen)
            seed_first = False
        except Exception as e:  # noqa: BLE001  best-effort，單輪失敗不讓 worker 死掉
            print(f"[monitor] 這輪失敗，下輪再試：{e}")
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    if os.getenv("RUN_ONCE") == "1":
        # 單次模式：給 GitHub Actions workflow_dispatch / 手動測試用，不進無限迴圈。
        _seen = load_seen()
        run_once(_seen, seed_only=False)
        save_seen(_seen)
    else:
        main()
