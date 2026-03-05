FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt [cite: 1]

COPY . .

ENV PORT=8080

# 只保留這一行啟動指令，刪除其他 CMD 指令 [cite: 1]
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app [cite: 1]