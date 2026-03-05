FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 安裝基礎編譯工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 先安裝依賴項，利用 Docker 快取機制
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製其餘程式碼
COPY . .

# 設定 Cloud Run 所需的 Port
ENV PORT=8080

# 啟動命令：確保只保留這一行，並正確指向 main:app
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app