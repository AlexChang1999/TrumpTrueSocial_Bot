# 常駐 worker 容器（給 Fly.io / 任何支援 Docker 的免費雲端用）
FROM python:3.13-slim

WORKDIR /app

# 先裝依賴（利用 layer 快取）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再複製程式
COPY monitor.py .

# 預設常駐迴圈（不設 RUN_ONCE）。INTERVAL_SEC / FETCH_LIMIT 可由環境變數覆寫。
CMD ["python", "monitor.py"]
