# 📡 TrumpTrueSocial_Bot — Truth Social 監控通知機器人

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![Discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)
![Oracle Cloud](https://img.shields.io/badge/Oracle%20Cloud-F80000?style=for-the-badge&logo=oracle&logoColor=white)

</div>

## 專案簡介

24/7 常駐雲端 worker，監控 Truth Social 上的新貼文，並即時推播通知到 Telegram 與 Discord，每 5 分鐘穩定檢查一次，不需綁定任何一台個人電腦。早期版本採用 GitHub Actions cron 排程，但因排程延遲、觸發堆積等限制，改為常駐迴圈架構後才達成穩定的即時性。

## 技術棧

| 類別 | 技術 |
|---|---|
| 語言 | Python |
| 資料來源 | Truth Social 官方 API（主）→ trumpstruth.org RSS（備援，遇 Cloudflare 阻擋自動切換） |
| 通知 | Telegram Bot API、Discord Webhook |
| 部署 | Oracle Cloud Always Free VM（systemd 常駐服務）/ Fly.io（容器化備選） |
| 狀態管理 | seen.json 記錄已推播貼文 ID，避免重複通知 |

## 運作原理

• 常駐迴圈每 INTERVAL_SEC（預設 300 秒）檢查一次新貼文
• 冷啟動保護：首次啟動時只記錄不推播，避免重啟後整批重發
• 單一 instance 限制：確保只有一條推播路徑，避免重複通知

## 安裝與設定

**1. 準備憑證**（設為環境變數，不寫入 Git）

TELEGRAM_TOKEN：Telegram Bot Token（透過 @BotFather 取得）
TELEGRAM_CHAT_ID：Telegram 使用者 ID（透過 @userinfobot 取得）
DISCORD_WEBHOOK：Discord 頻道 Webhook URL

**2. 本機測試**

```
pip install -r requirements.txt
python monitor.py
```

**3. 正式部署**

詳細的 24/7 常駐部署步驟（Oracle Cloud / Fly.io）請參考 SELF_HOSTING.md。

## 使用方式

啟動後程式會持續於背景執行，偵測到新貼文時自動發送通知，無需手動觸發。

## 專案結構（節錄）

```
TrumpTrueSocial_Bot/
├── monitor.py                   主程式：常駐迴圈、抓貼文、去重、發通知
├── requirements.txt
├── SELF_HOSTING.md              正式部署指南
├── Dockerfile / fly.toml        Fly.io 容器化部署
├── deploy/trump-monitor.service systemd unit
└── docs/OPERATIONS.md           維運備註
```

## 注意事項

seen.json 為執行期狀態，不進版本控制，保存在部署主機磁碟中，跨重啟維持已讀貼文紀錄。
