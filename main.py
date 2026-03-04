import os
import logging
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify

# 1. 強力日誌設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 2. 安全獲取環境變數
def get_env_config():
    return {
        "GEMINI_KEY": os.environ.get("GEMINI_API_KEY", "").strip(),
        "TG_TOKEN": os.environ.get("TELEGRAM_TOKEN", "").strip(),
        "TG_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID", "").strip(),
        "WEBHOOK_TOKEN": "my_private_token_123"
    }

def send_tg_message(token, chat_id, text):
    """底層發送函數"""
    if not token or not chat_id:
        logger.error("❌ Telegram 參數缺失，跳過發送")
        return "Missing Config"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload, timeout=15)
        logger.info(f"📢 TG API Response: {res.status_code} - {res.text}")
        return res.text
    except Exception as e:
        logger.error(f"❌ TG 發送異常: {e}")
        return str(e)

@app.route("/test-tg")
def test_tg():
    """極簡診斷路由"""
    config = get_env_config()
    logger.info(f"執行診斷: Token長度={len(config['TG_TOKEN'])}, ID={config['TG_ID']}")
    
    result = send_tg_message(
        config["TG_TOKEN"], 
        config["TG_CHAT_ID"], 
        "🚀 <b>AIES 測試連線</b>\n如果你看到這條，代表網絡路徑已打通！"
    )
    return f"診斷已執行。API回傳: {result}", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    config = get_env_config()
    data = request.get_json(silent=True)
    
    if not data or data.get("token") != config["WEBHOOK_TOKEN"]:
        return jsonify({"status": "unauthorized"}), 401

    ticker = data.get("ticker", "Unknown")
    action = data.get("action", "none").upper()
    
    # AI 分析邏輯
    ai_opinion = "AI 尚未配置"
    if config["GEMINI_KEY"]:
        try:
            genai.configure(api_key=config["GEMINI_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"分析{ticker}的{action}訊號，給1-10分。")
            ai_opinion = response.text
        except Exception as e:
            ai_opinion = f"AI Error: {e}"

    report = f"<b>【AIES 訊號】</b>\n標的: {ticker}\n動作: {action}\n\n🤖 AI 分析:\n{ai_opinion}"
    send_tg_message(config["TG_TOKEN"], config["TG_CHAT_ID"], report)
    
    return jsonify({"status": "success"}), 200

@app.route("/")
def health():
    return "AIES Agent is Running", 200

if __name__ == "__main__":
    # 這裡不要放任何初始化邏輯，確保 Cloud Run 能啟動
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)