import os
import json
import logging
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def send_tg_message(text):
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"TG 發送失敗: {e}")

def analyze_with_gemini(signal_data):
    try:
        import google.generativeai as genai
        if not GEMINI_API_KEY:
            return "❌ 錯誤：未偵測到 GEMINI_API_KEY"

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"您現在是 AIES-2026 決策大腦。請分析數據並提供建議：{json.dumps(signal_data)}"
        response = model.generate_content(prompt)
        
        return response.text if response else "⚠️ AI 回傳內容為空"
    except Exception as e:
        return f"❌ AI 錯誤: {str(e)}"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True)
    if not data or data.get("token") != WEBHOOK_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    analysis_result = analyze_with_gemini(data)
    
    tg_text = f"🔔 *AIES-2026 訊號*\n📍 標的：{data.get('ticker', 'XAUUSD')}\n━━━━━━━━━━━━\n{analysis_result}"
    send_tg_message(tg_text)
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))