# TrumpTrueSocial_Bot

監控川普 Truth Social 新貼文，發通知到 **Telegram** + **Discord**。
免費、不用伺服器，靠 GitHub Actions 每 5 分鐘自動跑。

## 運作原理

1. 先試 Truth Social 官方 API；被 Cloudflare 擋就退回 `trumpstruth.org` RSS。
2. 用 `seen.json` 記住看過的貼文 ID，只對新貼文發通知。
3. 發完通知把 `seen.json` 推回 repo。

## 設定步驟

1. repo → **Settings → Secrets and variables → Actions → New repository secret**，建 3 個：
   - `TELEGRAM_TOKEN` — 你的 Telegram Bot Token（@BotFather 拿）
   - `TELEGRAM_CHAT_ID` — 你的 Telegram user id（@userinfobot 拿）
   - `DISCORD_WEBHOOK` — Discord 頻道 Webhook URL
2. 去 Telegram **對你的 bot 按 Start**（否則 bot 不能私訊你）。
3. repo → **Actions** 分頁 → 選 workflow → **Run workflow** 手動測一次。
4. 成功後每 5 分鐘自動跑。

## 本機測試（選用）

```bash
pip install -r requirements.txt

# Windows PowerShell 設環境變數後執行
$env:TELEGRAM_TOKEN="..."; $env:TELEGRAM_CHAT_ID="..."; $env:DISCORD_WEBHOOK="..."
python monitor.py
```

## 檔案說明

| 檔案 | 作用 |
|------|------|
| `monitor.py` | 主程式：抓貼文 → 去重 → 發通知 |
| `requirements.txt` | Python 套件 |
| `.github/workflows/monitor.yml` | GitHub Actions 排程 |
| `seen.json` | 看過的貼文 ID（自動更新） |
