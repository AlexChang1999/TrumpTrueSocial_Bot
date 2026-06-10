# 維運備註（OPERATIONS）

正式運作方式 = **路 A**（見 [`PING_SETUP.md`](PING_SETUP.md)）：
cron-job.org 每 1 分鐘打 GitHub API 觸發 `workflow_dispatch` → Actions 跑 `monitor.py`（`RUN_ONCE=1`）
→ 抓川普新文 → 發 Telegram + Discord。`concurrency:` 防重疊、抓取上限 20、`seen.json` 去重。
**全程雲端，不綁任何電腦。**

---

## 會讓 bot 靜默停掉的事（按重要性顧好）

1. ⭐ **PAT 過期**（最容易中）
   cron-job.org 用的 fine-grained PAT 預設會到期。到期後戳會收 **401**、GitHub 不再觸發、
   **不會有任何 Discord 告警**，bot 默默死掉。對策：
   - 開 PAT 時設較長／最長到期，並記到行事曆提醒。
   - **在 cron-job.org 開「失敗才通知（非 2xx 寄 email）」** → 401 立刻收到信。
   - 到期前去 GitHub regenerate，更新進 cron-job.org 的 `Authorization` header。

2. **repo 必須維持 public**
   public 的 Actions 免費無限。若改成 private，1 分鐘 = 1440 runs/天，會爆掉免費 2000 分鐘/月、
   月中直接停。要嘛維持 public，要嘛把 cron-job.org 間隔改回 5 分鐘。

3. **run 內失敗（RSS 掛了 / secret 設錯）沒人通知**
   這種情況 GitHub run 會變紅，但對 cron-job.org 仍回 204 → cron-job.org 的失敗通知抓不到。
   對策：確認 **GitHub 帳號的 Actions 失敗 email 通知開著**（預設會寄給 repo owner）。
   → 兩層告警：cron-job.org email 抓「PAT/URL 問題」；GitHub email 抓「run 內部錯誤」。

## 已知、可接受、不用動

- 官方 Truth Social API 每次回 **403**（Cloudflare 擋）→ 自動退 `trumpstruth.org` RSS。功能正常；
  代價是依賴該 RSS 站可用性。
- `seen.json` 靠每次 run 的 `git push` 持久化（只在有新文時 commit，一天約幾十個）。
  `MAX_SEEN=200` 限制檔案大小。萬一 `seen.json` 被清空，下一輪會補發最新 ≤20 篇一次（可接受）。
- 每次 run 約 20–30 秒冷啟動 → 川普發文到 tg/dc 約 ≤1 分鐘 + 半分鐘，非秒級即時（路 A 本質，OK）。

## 換電腦 = 不用動任何設定

整條鏈都在雲端：cron-job.org（雲端帳號）、GitHub repo + 3 個 secret + PAT（全在伺服器端）。
- 換新電腦：bot **照跑，零設定**。新電腦不需要裝任何東西來維持運作。
- 只有當你想「改 code / 本機測試」才需要 `git clone` + `pip install -r requirements.txt`（見 README）。
- 唯一跨機要顧的是帳號層級：GitHub 登入、cron-job.org 登入、PAT 沒過期 —— 跟用哪台電腦無關。

## secrets / 變數一覽

| 放哪 | 名稱 | 用途 |
|------|------|------|
| GitHub repo secret | `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` / `DISCORD_WEBHOOK` | 發通知 |
| cron-job.org header | `Authorization: Bearer <PAT>` | 觸發 workflow_dispatch |
| monitor.py 可選 env | `FETCH_LIMIT`（預設 20）/ `INTERVAL_SEC`（常駐模式才用）/ `RUN_ONCE` | 行為調參 |
