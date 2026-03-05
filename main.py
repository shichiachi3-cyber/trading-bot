import os
import json
import logging
from flask import Flask, request, jsonify

# 設定 L7 動態監控日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 從 GCP Secret Manager/環境變數獲取配置
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
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"TG 發送失敗: {e}")
        return None

def analyze_with_gemini(signal_data):
    """L2 多維評估層：調用 Gemini 進行決策分析"""
    try:
        import google.generativeai as genai
        
        if not GEMINI_API_KEY:
            return "❌ 系統錯誤：未偵測到 GEMINI_API_KEY 環境變數"

        genai.configure(api_key=GEMINI_API_KEY)
        
        # 修正模型路徑問題，改用最穩定的名稱
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 根據 V3.5 指南設定的 L2 規則庫 Prompt
        prompt = f"""
        您現在是 AIES-2026 決策大腦。請針對以下 XAUUSD 訊號進行深度分析：
        數據：{json.dumps(signal_data)}
        
        請嚴格依照以下 V3.5 格式回傳：
        1. 【信度評估】：Σ(規則匹配度 × 权重) / 總權重 (請給出 0-100 分)
        2. 【行動建議】：買入/賣出/觀望 (若信度 > 75% 建議自動執行)
        3. 【風險分析】：建議止損價位 (基於當前波動率)
        4. 【成本審核】：預期收益是否 > 2.5倍成本？
        """
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text
        else:
            return "⚠️ AI 回傳內容為空，請檢查訊號格式"
            
    except Exception as e:
        logger.error(f"Gemini 模組崩潰: {str(e)}")
        return f"❌ AI 分析模組出錯: {str(e)}"

@app.route('/webhook', methods=['POST'])
def webhook():
    """L1 監控與初篩入口"""
    # 1. 捕捉原始數據並記錄日誌 (L7 監控)
    data = request.get_json(silent=True)
    logger.info(f"收到 Webhook 訊號: {data}")

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    # 2. L6 安全執行驗證
    incoming_token = data.get("token")
    if incoming_token != WEBHOOK_TOKEN:
        logger.warning(f"驗證失敗！收到 Token: {incoming_token}")
        return jsonify({"error": "Unauthorized"}), 403

    # 3. 執行 L2 分析
    analysis_result = analyze_with_gemini(data)
    
    # 4. 推送至 L5 Telegram 終端
    ticker = data.get('ticker', '未知標的')
    price = data.get('price', '手動觸發')
    
    tg_text = (
        f"🔔 *AIES-2026 訊號觸發*\n\n"
        f"📍 標的：{ticker}\n"
        f"💰 價格：{price}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"*AI 決策報告：*\n\n{analysis_result}"
    )
    
    send_tg_message(tg_text)

    # 5. 立即回傳 200 給 TradingView 避免 503/500 逾時
    return jsonify({"status": "success", "processed": True}), 200

@app.route('/test-tg')
def test_tg():
    """通訊層測試路由"""
    res = send_tg_message("🚀 AIES-2026 通訊層測試成功 (V3.5)")
    return jsonify(res)

if __name__ == "__main__":
    # 對齊 GCP Cloud Run 埠號規範
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))