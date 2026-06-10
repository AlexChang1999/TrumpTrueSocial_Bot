# 24/7 常駐部署指南（換電腦／換主機照這份重做）

## 為什麼不再用 GitHub Actions 排程

原本靠 `.github/workflows/monitor.yml` 的 `cron: "*/5 * * * *"` 每 5 分鐘跑。
但 **GitHub Actions 的 `schedule:` 是 best-effort、不保證準時**：排程 job 進佇列會被延遲
（數十分鐘～數小時），public repo 優先序最低，堆積的觸發還會被合併。結果「每 5 分」
實際跑成「每幾小時、一次吐一批」。再加上舊版 `monitor.py` 每輪只抓最新 5 篇，看起來就像
「集滿 5 則才發」，而且空檔內超過 5 篇的舊貼文會被永久漏掉。

**解法**：把 `monitor.py` 改成常駐迴圈（`while True: 檢查; sleep(INTERVAL_SEC)`），
丟到免費雲端 24/7 跑 → 真正穩定的 5 分鐘節奏、不綁任何一台 PC、無 GH cron 延遲。
`monitor.yml` 只留 `workflow_dispatch` 當手動測試。

> 電腦不用一直開。常駐 worker 跑在雲端，你的電腦關機也照跑。

## 環境變數（三把密碼，絕不進 git）

| 變數 | 來源 |
|------|------|
| `TELEGRAM_TOKEN` | @BotFather 拿的 Bot Token |
| `TELEGRAM_CHAT_ID` | @userinfobot 拿的 user id |
| `DISCORD_WEBHOOK` | Discord 頻道 → 整合 → Webhook URL |

可選調參：`INTERVAL_SEC`（預設 300＝5 分）、`FETCH_LIMIT`（預設 20，每輪抓最新幾篇）。

---

## 方案 A：Oracle Cloud Always Free VM（首選，永久免費 + 最穩）

Oracle 的 Always Free VM 是真・永久免費，跑成 `systemd` service → 開機自啟、崩潰自動重起。

1. 開一台 Always Free VM（Ampere/ARM 或 x86 皆可，Ubuntu）。
2. SSH 進去，裝環境並 clone：
   ```bash
   sudo apt update && sudo apt install -y python3-venv git
   git clone https://github.com/AlexChang1999/TrumpTrueSocial_Bot.git
   cd TrumpTrueSocial_Bot
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```
3. 建密碼檔 `.env`（已被 .gitignore 擋掉，不會進 git）：
   ```bash
   cat > .env <<'EOF'
   TELEGRAM_TOKEN=你的token
   TELEGRAM_CHAT_ID=你的chatid
   DISCORD_WEBHOOK=你的webhook
   EOF
   chmod 600 .env
   ```
4. 裝 systemd service（unit 範本在 `deploy/trump-monitor.service`，先依你的路徑/使用者改）：
   ```bash
   sudo cp deploy/trump-monitor.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now trump-monitor
   sudo systemctl status trump-monitor      # 看狀態
   journalctl -u trump-monitor -f           # 看即時 log
   ```

> Oracle VM 有持久磁碟，`seen.json` 會留著 → 重啟後不漏、也不重發。

## 方案 B：Fly.io（替代，容器化最快）

附了 `Dockerfile` + `fly.toml`，把它當「背景程式」跑（不是 web service、不會閒置縮到 0）。

```bash
fly launch --no-deploy            # 產生 app（app 名稱要全域唯一，去 fly.toml 改）
fly secrets set TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=... DISCORD_WEBHOOK=...
fly deploy
fly logs                          # 看 log
```

> ⚠️ Fly 免費機器的磁碟是 ephemeral：重啟後 `seen.json` 會消失。`monitor.py` 已做
> **冷啟動 seed**（重啟後第一輪只記錄不發），所以不會重發整批舊貼文；代價是重啟期間的新貼文可能漏一次。
> 要完全不漏可加 Fly volume 掛在工作目錄保存 `seen.json`。

## 避雷

- **Render 免費**：只有 web service 且閒置 15 分鐘會休眠 → 不適合常駐迴圈。
- **Railway**：已非長期免費。
- 這兩個不要拿來跑這支。

---

## 本機測試（部署前先確認會動）

```powershell
pip install -r requirements.txt
$env:TELEGRAM_TOKEN="..."; $env:TELEGRAM_CHAT_ID="..."; $env:DISCORD_WEBHOOK="..."
$env:INTERVAL_SEC="60"          # 測試時縮短到 1 分鐘，看快一點
python monitor.py               # 常駐迴圈；Ctrl+C 停
# 只想跑一次：$env:RUN_ONCE="1"; python monitor.py
```

驗證重點：
- 每輪都印「沒有新貼文」或「已通知：<id>」，節奏穩定。
- 冷啟動（seen.json 空）第一輪印「冷啟動 seed」、不洗頻。
- 川普連發 6+ 篇，確認不再漏第 6 篇起（`FETCH_LIMIT=20`）。
- 部署雲端後關掉本機電腦，確認仍持續發 → 證明不綁 PC。
