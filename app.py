import os
import logging
from typing import Any, Dict

from flask import Flask, request, jsonify
import requests

from binance.client import Client as BinanceClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/health", methods=["GET"])
    def health() -> Any:
        return jsonify({"status": "ok"}), 200

    @app.route("/webhook", methods=["POST"])
    def webhook() -> Any:
        """
        TradingView Webhook 接收端。

        假設 TradingView 傳來的 JSON 結構類似：
        {
          "symbol": "BTCUSDT",
          "side_hint": "long" or "short" or null,
          "news": "這裡是一段與該標的相關的新聞文字",
          "quantity": 0.001
        }
        你可以依實際 alert message 格式調整 parsing。
        """
        try:
            payload: Dict[str, Any] = request.get_json(force=True, silent=False)  # type: ignore
        except Exception as e:
            logger.exception("Invalid JSON payload: %s", e)
            return jsonify({"error": "invalid_json"}), 400

        logger.info("Received webhook payload: %s", payload)

        if not isinstance(payload, dict):
            return jsonify({"error": "payload_must_be_json_object"}), 400

        symbol = payload.get("symbol")
        news_text = payload.get("news")
        side_hint = payload.get("side_hint")  # 可選，給 decision 模型參考
        quantity = payload.get("quantity", 0.001)

        if not symbol or not news_text:
            return jsonify({"error": "missing_symbol_or_news"}), 400

        # 1) 執行層：呼叫 Kimi API 總結新聞
        try:
            news_summary = call_kimi_summary(news_text)
        except Exception as e:
            logger.exception("Kimi API error: %s", e)
            return jsonify({"error": "kimi_api_failed"}), 500

        # 2) 決策層：將新聞總結丟給 Gemini 3 判斷買賣
        try:
            decision = call_gemini_decision(
                symbol=symbol,
                news_summary=news_summary,
                side_hint=side_hint,
            )
        except Exception as e:
            logger.exception("Gemini decision error: %s", e)
            return jsonify({"error": "gemini_api_failed"}), 500

        logger.info("Decision from Gemini: %s", decision)

        action = decision.get("action")  # "BUY" / "SELL" / "HOLD"
        reason = decision.get("reason")

        if action not in {"BUY", "SELL", "HOLD"}:
            return jsonify(
                {
                    "error": "invalid_decision_action",
                    "decision_raw": decision,
                }
            ), 500

        trade_result: Dict[str, Any] | None = None

        # 3) 透過 Binance API 執行交易（若非 HOLD）
        if action in {"BUY", "SELL"}:
            try:
                trade_result = execute_binance_order(
                    symbol=symbol,
                    side=action,
                    quantity=float(quantity),
                )
            except Exception as e:
                logger.exception("Binance order error: %s", e)
                return jsonify({"error": "binance_order_failed"}), 500

        return (
            jsonify(
                {
                    "symbol": symbol,
                    "news_summary": news_summary,
                    "decision": decision,
                    "trade_result": trade_result,
                }
            ),
            200,
        )

    return app


def call_kimi_summary(news_text: str) -> str:
    """
    呼叫 Kimi API，將原始新聞文字總結成短摘要。

    你需要在 Cloud Run 環境變數中設定：
    - KIMI_API_KEY
    - KIMI_API_BASE （若官方文件有指定 base url，可以改在這裡）

    注意：下面只是「範例呼叫方式」，實際 endpoint / body schema
    以 Kimi 官方最新文件為準，請自行對照調整。
    """
    api_key = os.getenv("KIMI_API_KEY")
    api_base = os.getenv("KIMI_API_BASE", "https://api.moonshot.cn/v1")

    if not api_key:
        raise RuntimeError("KIMI_API_KEY is not set")

    url = f"{api_base}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    prompt = (
        "請以專業量化交易分析師的角度，用 3~5 句話總結以下新聞，"
        "著重於對該資產價格的潛在影響、時間敏感度與風險因子。"
        "\n\n新聞內容：\n"
        f"{news_text}"
    )

    body: Dict[str, Any] = {
        "model": os.getenv("KIMI_MODEL", "moonshot-v1-8k"),
        "messages": [
            {"role": "system", "content": "你是一位專業的金融市場分析師。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }

    resp = requests.post(url, headers=headers, json=body, timeout=60)
    if resp.status_code >= 400:
        logger.error("Kimi API error: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Kimi API error: {resp.status_code}")

    data = resp.json()

    # 依 Kimi 實際回傳格式調整
    try:
        summary = data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.exception("Unexpected Kimi response format: %s", e)
        raise RuntimeError("Unexpected Kimi response format")

    return summary


def call_gemini_decision(symbol: str, news_summary: str, side_hint: str | None) -> Dict[str, Any]:
    """
    呼叫 Gemini 3 API，根據新聞摘要與標的資訊給出交易決策。

    你需要在 Cloud Run 環境變數中設定：
    - GEMINI_API_KEY
    - GEMINI_MODEL_NAME  (例如：gemini-1.5-pro, gemini-2.0-flash-exp 等，待 Gemini 3 正式命名)

    實際 endpoint / schema 以 Google 官方最新文件為準。
    這裡示範使用 google-genai 或 HTTP REST 皆可。
    為保持一般性，這裡以 REST POST 為例。
    """
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro")
    api_base = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    url = f"{api_base}/v1beta/models/{model_name}:generateContent?key={api_key}"

    system_prompt = (
        "你是一個嚴謹保守的量化交易決策引擎，負責根據新聞摘要、"
        "市場情緒與風險管理原則，輸出明確的交易指令。"
        "你只能輸出 JSON 格式，不要加入多餘文字。"
        'JSON 欄位包含：action("BUY"|"SELL"|"HOLD"), '
        'confidence(0~1), reason(中文理由簡述)。'
        "若資訊不足或風險過高應輸出 HOLD。"
    )

    user_prompt = (
        f"標的: {symbol}\n"
        f"新聞摘要:\n{news_summary}\n\n"
        f"方向提示(side_hint): {side_hint or '無'}\n\n"
        "請依照以上資訊，輸出嚴格遵守 JSON schema 的單一 JSON："
        '{"action": "BUY|SELL|HOLD", "confidence": 0~1, "reason": "中文理由"}'
    )

    body = {
        "contents": [
            {"role": "system", "parts": [{"text": system_prompt}]},
            {"role": "user", "parts": [{"text": user_prompt}]},
        ]
    }

    resp = requests.post(url, json=body, timeout=60)
    if resp.status_code >= 400:
        logger.error("Gemini API error: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Gemini API error: {resp.status_code}")

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.exception("Unexpected Gemini response format: %s", e)
        raise RuntimeError("Unexpected Gemini response format")

    # 嘗試把模型輸出的 JSON 解析出來
    import json

    text_stripped = text.strip()
    # 有些模型會外包 ```json ... ```，先清掉
    if text_stripped.startswith("```"):
        text_stripped = text_stripped.strip("`")
        # 移除可能的語言 tag，如 json\n
        if "\n" in text_stripped:
            text_stripped = text_stripped.split("\n", 1)[1]

    try:
        decision = json.loads(text_stripped)
    except Exception as e:
        logger.exception("Failed to parse Gemini JSON: %s; raw: %s", e, text)
        raise RuntimeError("Failed to parse Gemini JSON")

    return decision


def execute_binance_order(symbol: str, side: str, quantity: float) -> Dict[str, Any]:
    """
    使用 python-binance 下市價單。

    需要環境變數：
    - BINANCE_API_KEY
    - BINANCE_API_SECRET
    - BINANCE_TESTNET (可選，"true"/"false")
    """
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    use_testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

    if not api_key or not api_secret:
        raise RuntimeError("BINANCE_API_KEY or BINANCE_API_SECRET is not set")

    client = BinanceClient(api_key, api_secret, testnet=use_testnet)

    order_side = "BUY" if side.upper() == "BUY" else "SELL"

    logger.info(
        "Placing Binance market order: symbol=%s side=%s qty=%s testnet=%s",
        symbol,
        order_side,
        quantity,
        use_testnet,
    )

    order = client.create_order(
        symbol=symbol,
        side=order_side,
        type="MARKET",
        quantity=quantity,
    )

    return order


app = create_app()

if __name__ == "__main__":
    # 本地開發使用，Cloud Run 會用 gunicorn 啟動
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=True)

