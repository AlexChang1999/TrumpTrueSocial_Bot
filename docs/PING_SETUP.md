> ⚠️ **已棄用（DEPRECATED）。** 此路與 VM 常駐 worker 並跑會造成 split-brain `seen.json`
> → 重複推送。`monitor.yml` 已移除、`seen.json` 已退出 git。正式運作改走
> [`../SELF_HOSTING.md`](../SELF_HOSTING.md) 的 VM 常駐 worker。本文僅留作歷史。
> 若 cron-job.org 仍有那支定時任務，請到後台關閉。

# 路 A：免費、不綁卡 — cron-job.org 戳 GitHub Actions（已棄用）

完全不用雲端主機、不用信用卡。靠兩個免費東西：

- **GitHub Actions**：public repo 免費無限分鐘。
- **cron-job.org**：免費排程器（不綁卡），每 5 分鐘打一次 GitHub API 觸發 `workflow_dispatch`。

> 為什麼用 `workflow_dispatch` 而不是 `schedule:` cron？
> `schedule:` 是 best-effort、會被延遲數小時；`workflow_dispatch`（手動/API 觸發）**不被節流**，
> 由外部 pinger 每 5 分鐘準時戳 → 穩定。`monitor.yml` 已設 `RUN_ONCE=1`（單輪就結束）+ 把
> `seen.json` 推回 repo 做跨次去重，**不用再改任何 code**。
>
> 代價：每次跑有 ~1 分鐘 Actions 冷啟動（非即時，但遠勝 4 小時）。

---

## 前置：先把分支合併到 main

`workflow_dispatch` 只認 **預設分支（main）** 上的 workflow。先把 `feat/always-on-worker`
合併進 main（新版 `monitor.yml` 才生效、舊的 `*/5` schedule 才消失）。

```bash
gh pr create --base main --head feat/always-on-worker --fill
gh pr merge --merge
```

設好 3 個 repo secret（**Settings → Secrets and variables → Actions**）：
`TELEGRAM_TOKEN`、`TELEGRAM_CHAT_ID`、`DISCORD_WEBHOOK`。

---

## 步驟 1：開一把 GitHub Fine-grained PAT（給 cron-job.org 用來觸發）

1. GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**。
2. **Repository access** → Only select repositories → 選 `TrumpTrueSocial_Bot`。
3. **Permissions → Repository permissions → Actions** → 設 **Read and write**。（觸發 workflow 只需這個）
4. Generate → **複製 token**（只顯示一次，貼進 cron-job.org，別貼進 git）。

## 步驟 2：在 cron-job.org 建一個 cronjob

註冊 https://cron-job.org （免費、Email 即可，不綁卡）→ Create cronjob：

- **URL**：
  ```
  https://api.github.com/repos/AlexChang1999/TrumpTrueSocial_Bot/actions/workflows/monitor.yml/dispatches
  ```
- **Schedule**：Every 5 minutes（`*/5`）。
- 展開 **Advanced / Request**：
  - **Request method**：`POST`
  - **Headers**（逐條加）：
    ```
    Accept: application/vnd.github+json
    Authorization: Bearer <步驟1的PAT>
    X-GitHub-Api-Version: 2022-11-28
    ```
  - **Request body**：
    ```json
    {"ref":"main"}
    ```
- Save 並啟用。

> GitHub 觸發成功回 **HTTP 204**（No Content）。cron-job.org 把 2xx 當成功；可開「失敗才通知」盯著。

## 步驟 3：驗證

1. cron-job.org 看執行紀錄：每 5 分一筆、回應 204。
2. GitHub → **Actions** 分頁：每 ~5 分一個 run（觸發者顯示 API/你的 token），不再是 schedule、不再 4 小時一坨。
3. 川普發文後，下一輪（≤5 分 + ~1 分冷啟動）就到 Discord/Telegram。
4. seen.json 會被每次 run 推回 repo → 跨次去重正常、不重發。

## 換電腦時

這條路**不綁任何電腦** —— cron-job.org 在雲端跑、Actions 在雲端跑。換電腦什麼都不用做，
只要那把 PAT 沒過期、cron-job.org 帳號還在即可。
（fine-grained PAT 預設會過期；到期前去 GitHub regenerate，更新進 cron-job.org 的 header。）

---

## 手動測試（不等 5 分鐘）

GitHub → **Actions → Truth Social Monitor (manual test only) → Run workflow**（選 main）→ 跑一次看有沒有發。
或用 CLI：`gh workflow run monitor.yml --ref main`。
