import os
import logging
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify

# 1. 設定日誌格式
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 2. 從環境變數讀取安全設定 (GCP Cloud Run 設置)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
WEBHOOK_TOKEN = "my_private_token_123"

# 啟動時自檢 (在 GCP 日誌中可以看到)
print(f"--- AIES 系統啟動中 ---")
print(f"環境變數檢查: Gemini={'已設定' if GEMINI_KEY else '缺失'}, TG_Token={'已設定' if TG_TOKEN else '缺失'}, Chat_ID={TG_CHAT_ID}")

# 3. 初始化 Gemini AI
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("✅ Gemini AI 模組初始化成功")
    except Exception as e:
        logger.error(f"❌ Gemini 初始化失敗: {e}")

def send_tg_message(text):
    """L5 通訊模組：發送訊息到 Telegram"""
    if not TG_TOKEN or not TG_CHAT_ID:
        logger.error("❌ Telegram 配置缺失，無法發送訊息")
        return
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code != 200:
            logger.error(f"❌ TG API 回傳錯誤: {res.text}")
        else:
            logger.info("✅ Telegram 訊息發送成功")
    except Exception as e:
        logger.error(f"❌ Telegram 發送異常: {e}")

@app.before_request
def log_request():
    """診斷用：記錄所有進入的請求路徑"""
    logger.info(f"🚩 請求進來了: {request.method} {request.path}")

@app.route("/webhook", methods=["POST"])
def webhook():
    """L1 & L2 決策核心：接收 TradingView 訊號並分析"""
    data = request.get_json(silent=True)
    
    # 安全驗證
    if not data or data.get("token") != WEBHOOK_TOKEN:
        logger.warning(f"⚠️ 攔截到未授權請求: {data}")
        return jsonify({"status": "unauthorized"}), 401

    ticker = data.get("ticker", "Unknown")
    action = data.get("action", "none").upper()
    
    # 調用 AI 進行分析 (L1 層)
    ai_opinion = "AI 分析模組未啟動"
    if GEMINI_KEY:
        try:
            prompt = f"你是 AIES-2026 專家。標的: {ticker}, 動作: {action}。請給予 1-10 分推薦度並簡述理由(50字內)。"
            response = model.generate_content(prompt)
            ai_opinion = response.text
        except Exception as e:
            ai_opinion = f"AI 分析發生錯誤: {str(e)}"

    # 組合回報訊息 (L5 層)
    emoji = "🟢" if "BUY" in action else "🔴"
    report = (
        f"<b>【AIES-2026 系統回報】</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{emoji} 標的：{ticker}\n"
        f"⚡ 動作：{action}\n\n"
        f"🤖 <b>AI 決策分析：</b>\n"
        f"{ai_opinion}"
    )
    
    # 發送通知
    send_tg_message(report)
    
    return jsonify({"status": "processed", "ticker": ticker}), 200

@app.route("/test-tg")
def test_tg():
    """診斷用：手動測試 Telegram 連通性"""
    send_tg_message("🚀 <b>AIES 測試訊息</b>\n如果你看到這條，代表 Telegram 通訊完全正常！")
    return "已嘗試發送測試訊息，請檢查手機 Telegram。", 200

@app.route("/")
def health():
    """健康檢查"""
    return "AIES Agent is Active and Running", 200

if __name__ == "__main__":
    # Cloud Run 會提供 PORT 環境變數
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)