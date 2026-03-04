import os
import logging
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

# 配置環境變數
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
WEBHOOK_TOKEN = "my_private_token_123"

# 初始化 Gemini
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

def send_tg_message(text):
    """L5 通訊模組：發送訊息到 Telegram"""
    if not TG_TOKEN or not TG_CHAT_ID:
        logger.warning("Telegram 設定不完整，跳過發送")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text})
        res.raise_for_status()
    except Exception as e:
        logger.error(f"Telegram 推送失敗: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data or data.get("token") != WEBHOOK_TOKEN:
        return jsonify({"status": "unauthorized"}), 401

    ticker = data.get("ticker", "Unknown")
    action = data.get("action", "none")
    
    # L1 AI 評分
    prompt = f"你是 AIES-2026 專家。標的:{ticker} 動作:{action}。請給予 1-10 分推薦度並簡述理由。"
    try:
        response = model.generate_content(prompt)
        ai_opinion = response.text
    except Exception as e:
        ai_opinion = f"AI 分析暫時不可用: {e}"

    # 組合訊息推送到手機
    status_emoji = "🟢" if "buy" in action.lower() else "🔴"
    report = (
        f"AIES-2026 系統回報\n"
        f"------------------\n"
        f"{status_emoji} 標的: {ticker}\n"
        f"⚡ 動作: {action}\n\n"
        f"🤖 AI 分析:\n{ai_opinion}"
    )
    send_tg_message(report)
    
    return jsonify({"status": "processed"}), 200

@app.route("/")
def health():
    return "AIES Agent is Active", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))