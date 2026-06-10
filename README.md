# TrumpTrueSocial_Bot

監控川普 Truth Social 新貼文，發通知到 **Telegram** + **Discord**。
跑成**免費雲端常駐 worker**，每 5 分鐘穩定檢查一次（24/7、不綁任何一台電腦）。

> 早期版本靠 GitHub Actions `cron` 每 5 分鐘跑，但 GH 排程會被延遲數小時、堆積觸發被合併，
> 實際變成「每幾小時、一次吐一批」。改成常駐迴圈後才有真正的 5 分鐘節奏。
> 部署步驟見 [`SELF_HOSTING.md`](SELF_HOSTING.md)。

## 運作原理

1. 常駐迴圈：每 `INTERVAL_SEC`（預設 300＝5 分）檢查一次。
2. 先試 Truth Social 官方 API；被 Cloudflare 擋就退回 `trumpstruth.org` RSS（每輪抓最新 `FETCH_LIMIT`＝20 篇）。
3. 用 `seen.json` 記住看過的貼文 ID（常駐進程也保留在記憶體，跨輪去重），只對新貼文發通知。
4. 冷啟動防洗頻：`seen.json` 空時第一輪只記錄不發，避免重啟後整批重發。

## 設定步驟

1. 準備 3 把密碼（之後設成雲端 host 的環境變數，**不寫進 git**）：
   - `TELEGRAM_TOKEN` — Telegram Bot Token（@BotFather 拿）
   - `TELEGRAM_CHAT_ID` — Telegram user id（@userinfobot 拿）
   - `DISCORD_WEBHOOK` — Discord 頻道 Webhook URL
2. 去 Telegram **對你的 bot 按 Start**（否則 bot 不能私訊你）。
3. 依 [`SELF_HOSTING.md`](SELF_HOSTING.md) 部署常駐 worker（Oracle Always Free VM 或 Fly.io）。
4. 換電腦／換主機時，照 `SELF_HOSTING.md` 重做一次即可。

> `.github/workflows/monitor.yml` 已停用排程，只留 **手動 Run workflow**（單次）當測試用。

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
| `monitor.py` | 主程式：常駐迴圈，抓貼文 → 去重 → 發通知（`RUN_ONCE=1` 可單次） |
| `requirements.txt` | Python 套件 |
| `SELF_HOSTING.md` | 24/7 常駐部署指南（Oracle VM / Fly.io） |
| `Dockerfile` / `fly.toml` | Fly.io 容器化部署 |
| `deploy/trump-monitor.service` | Oracle/Linux 用的 systemd unit |
| `.github/workflows/monitor.yml` | 只剩手動測試（排程已停用） |
| `seen.json` | 看過的貼文 ID（自動更新） |
