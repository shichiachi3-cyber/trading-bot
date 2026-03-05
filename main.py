import os
import json
import logging
from flask import Flask, request, jsonify

# 設定日誌紀錄，方便在 Cloud Run Logs 中查看除錯資訊
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 從環境變數中讀取設定
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def send_tg_message(text):
    """將分析結果發送到 Telegram"""
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text, 
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Telegram 訊息發送成功")
    except Exception as e:
        logger.error(f"TG 發送失敗: {e}")

def analyze_with_gemini(signal_data):
    """呼叫 Gemini API 進行 AI 分析"""
    try:
        import google.generativeai as genai
        if not GEMINI_API_KEY:
            return "❌ 錯誤：環境變數中未偵測到 GEMINI_API_KEY"

        # 設定 Gemini API
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 建立分析提示詞
        prompt = (
            f"您現在是 AIES-2026 專業交易決策大腦。\n"
            f"請根據以下 TradingView 訊號數據進行深度分析，並提供具體的操盤建議：\n"
            f"{json.dumps(signal_data, indent=2, ensure_ascii=False)}"
        )
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text
        else:
            return "⚠️ AI 分析完成，但回傳內容為空。"
    except Exception as e:
        logger.error(f"Gemini 分析錯誤: {e}")
        return f"❌ AI 決策模組出錯: {str(e)}"

@app.route('/', methods=['GET'])
def index():
    """根目錄回應，用來消除瀏覽器或自動監測產生的 404 錯誤"""
    return "AIES-2026 決策核心系統已上線，準備接收訊號中。", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """處理來自 TradingView 的 Webhook 請求"""
    # 讀取 JSON 數據
    data = request.get_json(silent=True)
    
    # 安全驗證：檢查 Token 是否正確
    if not data or data.get("token") != WEBHOOK_TOKEN:
        logger.warning(f"攔截到未授權的請求: {data}")
        return jsonify({"error": "Unauthorized"}), 403

    logger.info(f"接收到交易訊號: {data.get('ticker', '未知標的')}")

    # 執行 AI 分析
    analysis_result = analyze_with_gemini(data)
    
    # 組合訊息格式
    ticker = data.get('ticker', '未知標的')
    price = data.get('price', '未知價格')
    action = data.get('action', '觀察')
    
    tg_text = (
        f"🔔 *AIES-2026 交易訊號通知*\n"
        f"📍 標的：{ticker}\n"
        f"💰 價格：{price}\n"
        f"🚀 行動：{action}\n"
        f"━━━━━━━━━━━━\n"
        f"🤖 *AI 決策分析：*\n\n{analysis_result}"
    )
    
    # 發送訊息到 Telegram
    send_tg_message(tg_text)
    
    return jsonify({"