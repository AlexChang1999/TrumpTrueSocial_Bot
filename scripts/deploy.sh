#!/usr/bin/env bash
# ============================================================
# VM 部署腳本（在常駐 VM 上執行；由 GitHub Actions deploy job 透過 SSH 呼叫）
# ============================================================
# 流程：記住目前版本 → 拉新碼 → 裝依賴 → 重啟 worker → 健康檢查（is-active）
#       → 失敗就回滾到上一版，確保 VM 永遠停在「跑得起來」的版本。
#
# 用法（在 repo 根目錄）：bash scripts/deploy.sh [branch]   # branch 預設 main
#
# 前置（VM 一次性）：
#   - venv 在 ~/TrumpTrueSocial_Bot/.venv（見 SELF_HOSTING.md）
#   - 密碼在 .env（不進 git）；systemd unit 見 deploy/trump-monitor.service
#   - 給 deploy 帳號免密碼 sudo 重啟該服務：
#       echo "$USER ALL=(root) NOPASSWD: /bin/systemctl restart trump-monitor" \
#         | sudo tee /etc/sudoers.d/trump-deploy
set -euo pipefail

BRANCH="${1:-main}"
SERVICE="trump-monitor"

cd "$(dirname "$0")/.."

PREV="$(git rev-parse HEAD)"
echo "▶ 目前版本 ${PREV:0:8}，準備部署 origin/${BRANCH}"

git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"
NEW="$(git rev-parse HEAD)"
echo "▶ 已更新到 ${NEW:0:8}"

deploy_current() {
  .venv/bin/pip install -q -r requirements.txt
  sudo systemctl restart "$SERVICE"
  sleep 5
}

deploy_current

# 健康檢查：worker 無 HTTP 端點 → 看 systemd 是否還 active（沒在啟動階段崩）。
if systemctl is-active --quiet "$SERVICE"; then
  echo "✅ 部署成功，${SERVICE} active @ ${NEW:0:8}"
else
  echo "❌ ${SERVICE} 未 active → 回滾到 ${PREV:0:8}"
  git reset --hard "$PREV"
  deploy_current
  if systemctl is-active --quiet "$SERVICE"; then
    echo "↩️  已回滾且 active @ ${PREV:0:8}（本次部署失敗）"
  else
    echo "🔥 回滾後仍非 active，請人工介入：journalctl -u $SERVICE -n 50"
  fi
  exit 1
fi
