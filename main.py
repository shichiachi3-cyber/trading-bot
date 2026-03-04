import logging
import os
from typing import Any, Dict
from flask import Flask, request, jsonify

# 設定日誌格式，這樣你在 GCP Logs 才能看清楚發生什麼事
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook() -> Any:
    """
    TradingView Webhook 接收端
    """
    # 1. 解析 JSON 資料
    payload: Dict[str, Any] | None = request.get_json(silent=True)
    
    if payload is None:
        logger.error("收到空的或無效的 JSON")
        return jsonify({"error": "invalid_json"}), 400

    # 2. 安全性檢查：驗證 Token
    # 請確保 TradingView 的訊息裡有 "token": "my_private_token_123"
    token = payload.get("token")
    if token != "my_private_token_123":
        logger.warning(f"授權失敗！收到錯誤的 Token: {token}")
        return jsonify({"error": "unauthorized"}), 401

    # 3. 取得交易參數 (對應 TradingView 的 JSON 欄位)
    # 這裡我們統一使用 ticker 和 action，避免與 TradingView 內建變數混淆
    ticker = payload.get("ticker", "Unknown")
    action = payload.get("action", "none")

    # 4. 核心邏輯：目前僅先印出訊號，未來在此接入 AI 判斷
    output_msg = f"🚀 收到交易訊號! 標的: {ticker}, 動作: {action}"
    print(output_msg)
    logger.info(output_msg)

    # 5. 回覆成功
    return jsonify({
        "status": "success", 
        "received": {"ticker": ticker, "action": action}
    }), 200

@app.route("/health", methods=["GET"])
@app.route("/", methods=["GET"])
def health() -> Any:
    """讓 GCP 知道這個服務還活著"""
    return "Bot is running!", 200

if __name__ == "__main__":
    # Cloud Run 會提供 PORT 環境變數，如果沒有則預設 8080
    port = int(os.environ.get("PORT", 8080))
    # 部署到雲端時 debug 需設為 False
    app.run(host="0.0.0.0", port=port, debug=False)