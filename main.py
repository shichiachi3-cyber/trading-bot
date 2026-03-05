import os
import json
import logging
from flask import Flask, request, jsonify

# 設定 L7 動態監控日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 從環境變數獲取配置
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def send_tg_message(text):
    """L5 人機協同層：發送訊息至 Telegram"""
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text, 
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"TG 發送失敗: {e}")

def analyze_with_gemini(signal_data):
    """L2 多維評估層：修正 404 模型路徑問題"""
    try:
        import google.generativeai as genai
        
        if not GEMINI_API_KEY:
            return "❌ 錯誤：未偵測到 GEMINI_API_KEY 環境變數"

        # 設定 API Key
        genai.configure(api_key=GEMINI_API_KEY)
        
        # 使用最穩定的模型標識符，不帶 models/ 前綴以避免某些 SDK 版本的解析錯誤
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        您現在是 AIES-2026 決策大腦。請針對以下 XAUUSD 訊號進行深度分析：
        數據：{json.dumps(signal_data)}
        
        請嚴格依照以下格式回傳：
        1. 【信度評估】：0-100分
        2. 【行動建議】：買入/賣出/觀望
        3. 【風險分析】：建議止損價位
        4. 【成本審核】：預期收益是否 > 2.5倍成本？
        """
        
        # 執行 AI 生成
        response = model.generate_content(prompt)
        
        if response and response.