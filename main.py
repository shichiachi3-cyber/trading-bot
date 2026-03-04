import logging
from typing import Any, Dict

from flask import Flask, request, jsonify


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook() -> Any:
    """
    TradingView Webhook 接收端

    功能：
    - 驗證 token 是否等於 my_private_token_123
    - 讀取幣種(symbol)與方向(side)，印出到 log/console
    - 成功時回傳 200 OK

    建議 TradingView 傳入的 JSON 格式類似：
    {
      "token": "my_private_token_123",
      "symbol": "BTCUSDT",
      "side": "long"  // 或 "short" / "buy" / "sell" 依你自己定義
    }
    """
    # 解析 JSON
    payload: Dict[str, Any] | None = request.get_json(silent=True)  # type: ignore
    if payload is None:
        return jsonify({"error": "invalid_json"}), 400

    # 1. 安全性：檢查 token
    token = payload.get("token")
    if token != "my_private_token_123":
        logger.warning("Invalid token from TradingView: %s", token)
        return jsonify({"error": "unauthorized"}), 401

    # 2. 取得幣種與方向
    symbol = payload.get("symbol")
    side = payload.get("side")

    # 這裡先簡單防呆一下
    if not symbol or not side:
        return jsonify({"error": "missing_symbol_or_side"}), 400

    # 3. AI 邏輯預留：先印出幣種與方向
    print(f"Received signal - symbol: {symbol}, side: {side}")
    logger.info("Received signal - symbol: %s, side: %s", symbol, side)

    # 之後你可以在這裡接入 Kimi / Gemini / Binance 等 AI + 交易邏輯

    # 4. 成功回覆
    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # 本地啟動：python main.py
    app.run(host="0.0.0.0", port=8080, debug=True)

