import os
import logging
import requests
from flask import Flask, request, jsonify

# 1. 日誌設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_env_config():
    return {
        "GEMINI_KEY": os.environ.get("GEMINI_API_KEY", "").strip(),
        "TG_TOKEN": os.environ.get("TELEGRAM_TOKEN", "").strip(),
        "TG_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID", "").strip(),
        "WEBHOOK_TOKEN": "my_private_token_123"
    }

def send_tg_message(token, chat_id, text):
    if not token or not chat_id:
        return "Missing Config"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=15)
        logger.info(f"📢 TG API Response: {res.text}")
        return res.text
    except Exception as e:
        return str(e)

@app.route("/test-tg")
def test_tg():
    config = get_env_config()
    # 這裡只測試 Telegram，完全不碰 Gemini，確保路徑先通
    result = send_tg_message(config["TG_TOKEN"], config["TG_CHAT_ID"], "🚀 <b>AIES 通訊測試成功</b>")
    return f"Telegram 測試發送完成。API 回傳: {result}", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    config = get_env_config()
    data = request.get_json(silent=True)
    if not data or data.get("token") != config["WEBHOOK_TOKEN"]:
        return jsonify({"status": "unauthorized"}), 401

    ticker = data.get("ticker", "Unknown")
    action = data.get("action", "none").upper()
    
    # AI 分析邏輯：放在 Try 裡面，即使 AI 壞了，Telegram 也要能報信
    ai_opinion = "AI 模組調用失敗"
    if config["GEMINI_KEY"]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=config["GEMINI_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"分析{ticker}的{action}訊號，給1-10分。")
            ai_opinion = response.text
        except Exception as e:
            ai_opinion = f"AI Error: {str(e)}"

    report = f"<b>【AIES 訊號報告】</b>\n標的: {ticker}\n動作: {action}\n\n🤖 AI 評估:\n{ai_opinion}"
    send_tg_message(config["TG_TOKEN"], config["TG_CHAT_ID"], report)
    return jsonify({"status": "success"}), 200

@app.route("/")
def health():
    return "AIES Agent is Running", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)