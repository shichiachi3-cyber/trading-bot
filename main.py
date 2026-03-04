import os
import logging
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify

# 1. 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 2. 讀取環境變數 (GCP Cloud Run)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
WEBHOOK_TOKEN = "my_private_token_123"

# 啟動自檢
print(f"--- AIES 系統檢查 ---")
print(f"TG_TOKEN 狀態: {'已設定' if TG_TOKEN else '缺失'}")
print(f"TG_CHAT_ID 狀態: {'已設定' if TG_CHAT_ID else '缺失'}")

# 3. 初始化 Gemini
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        logger.error(f"Gemini 初始化失敗: {e}")

def send_tg_message(text):
    """L5 通訊模組：含診斷功能的發送函數"""
    if not TG_TOKEN or not TG_CHAT_ID:
        logger.error("❌ Telegram 配置缺失 (Token 或 Chat_ID 為空)")
        return

    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        # 增加 timeout 避免伺服器卡死
        res = requests.post(url, json=payload, timeout=10)
        
        # 【關鍵診斷】印出 Telegram API 的真實反應
        logger.info(f"📢 Telegram API 狀態碼: {res.status_code}")
        logger.info(f"📢 Telegram API 回