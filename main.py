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
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"TG 發送失敗: {e}")

def analyze_with_gemini(signal_data):
    """L2 多維評估層：解決 404 模型路徑與 API 版本衝突"""
    try:
        import google.generativeai as genai
        
        if not GEMINI_API_KEY:
            return "❌ 錯誤：未偵測到 GEMINI_API_KEY"

        genai.configure(api_key=GEMINI_API_KEY)
        
        # 策略 1：嘗試標準模型名稱 (最推薦)
        prompt = f"您現在是 AIES-2026 決策大腦。請分析：{json.dumps(signal_data)}。請提供：1.信度評估(0-100) 2.行動建議 3.止損建議 4.成本審核(收益>2.5x)"
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e1:
            logger.warning(f"標準路徑失敗，嘗試備用路徑: {e1}")
            # 策略 2：嘗試帶有 models/ 前綴的完整路徑
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
            
    except Exception as e:
        logger.error(f"Gemini 模組終極崩潰: {str(e)}")
        return f"❌ AI 分析模組出錯 (請確認 GCP 已啟用 Generative Language API): {str(e)}"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True)
    if not data: return jsonify({"error": "No JSON"}), 400

    # L6 安全驗證
    if data.get("token") != WEBHOOK_TOKEN:
        logger.warning("收到未經授權的 Token")
        return jsonify({"error": "Unauthorized"}), 403

    # 執行分析
    analysis_result = analyze_with_gemini(data)
    
    # 推送 Telegram
    tg_text = (
        f"🔔 *AIES-2026 訊號觸發*\n\n"
        f"📍 標題：{data.get('ticker', 'XAUUSD')}\n"
        f"💰 價格：{data.get('price', '手動觸發')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"*AI 決策報告：*\n\n{analysis_result}"
    )
    
    send_tg_message(tg_text)
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    # 確保 Cloud Run 環境能正確讀取 Port
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)