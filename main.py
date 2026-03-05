import os
import json
import logging
from flask import Flask, request, jsonify

# 設定日誌監控 (對齊 V3.5 L7 監控指標)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 從環境變數獲取配置
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN", "default_token")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_tg_message(text):
    """L5 通訊層：發送訊息至 Telegram"""
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.json()
    except Exception as e:
        logger.error(f"TG 發送失敗: {e}")
        return None

def analyze_with_gemini(signal_data):
    """L2 決策層：調用 Gemini 進行多維分析"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 建立符合 V3.5 邏輯的 Prompt 
        prompt = f"""
        你現在是 AIES-2026 決策大腦。請分析以下交易訊號：
        數據：{json.dumps(signal_data)}
        
        請嚴格依照以下格式回傳：
        1. 【信度評估】：0-100分 (依據規則引擎權重)
        2. 【行動建議】：買入/賣出/觀望
        3. 【風險分析】：VIX 狀態與止損建議
        4. 【成本分析】：預期收益是否 > 2.5倍成本
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AI 分析模組出錯: {str(e)}"

@app.route('/webhook', methods=['POST'])
def webhook():
    # 1. 立即捕捉原始數據 (診斷 503 用)
    data = request.get_json(silent=True)
    logger.info(f"收到 Webhook 訊號: {data}")

    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    # 2. 安全驗證 (L6 安全執行) [cite: 4]
    if data.get("token") != WEBHOOK_TOKEN:
        logger.warning("Token 驗證失敗！")
        return jsonify({"error": "Unauthorized"}), 403

    # 3. 執行分析 (MVP 階段採同步執行，確保你能看到結果)
    # 若未來訊號過多導致 503，此處需改為異步處理
    analysis_result = analyze_with_gemini(data)
    
    # 4. 推送至 L5 人機協同層 [cite: 3]
    tg_text = f"🔔 *AIES-2026 訊號觸發*\n\n"
    tg_text += f"標的：{data.get('ticker', '未知')}\n"
    tg_text += f"價格：{data.get('price', '未知')}\n"
    tg_text += f"---\n*AI 分析報告：*\n{analysis_result}"
    
    send_tg_message(tg_text)

    return jsonify({"status": "processed", "message": "Signal received and analyzed"}), 200

@app.route('/test-tg')
def test_tg():
    res = send_tg_message("🚀 AIES 通訊測試成功")
    return jsonify(res)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))