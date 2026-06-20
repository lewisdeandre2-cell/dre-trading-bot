import os
import logging
import anthropic
from flask import Flask, request, jsonify
import telegram
import asyncio

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_TOKEN  = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_KEY   = os.environ["ANTHROPIC_API_KEY"]
CHAT_ID         = os.environ["TELEGRAM_CHAT_ID"]  # Your personal Telegram chat ID

claude  = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
bot     = telegram.Bot(token=TELEGRAM_TOKEN)

# ── ALERT ANALYSIS PROMPT ─────────────────────────────────────────────────────
def build_alert_prompt(pair, price, alert_type, zone_type, session):
    return f"""
You are Dre's trading assistant. A TradingView price alert just fired.

ALERT DETAILS:
- Pair: {pair}
- Current Price: {price}
- Alert Type: {alert_type}
- Zone Type: {zone_type}
- Session: {session} (CDT)

Based on Dre's trading plan, provide an instant alert analysis using this format:

🚨 PRICE ALERT FIRED
📈 {pair} | 💰 {price}
⏰ Session: {session} CDT

🎯 ZONE: {zone_type}
📊 BIAS: [BULLISH/BEARISH based on zone type and alert]

💡 IF/THEN:
• IF price shows rejection from this zone → [action | Entry: X | Stop: X | Target: X]
• IF price pushes through this zone → [action — zone fail, flip bias]

⚠️ CHECK:
• DXY confirming this bias? [yes/no based on zone type]
• Any red news events right now? Check Forex Factory
• Is this within your session window? {session}

📋 ACTION: [One clear sentence — what to do RIGHT NOW]

🔔 Send a screenshot of the chart for full analysis!

Keep it concise and mobile-friendly.
"""

# ── WEBHOOK ENDPOINT ──────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    TradingView sends alerts here as JSON or plain text.
    
    Set up your TradingView alert message like this:
    {
        "pair": "XAUUSD",
        "price": "{{close}}",
        "alert_type": "price_crossed",
        "zone_type": "supply",
        "session": "London"
    }
    """
    try:
        # Handle both JSON and plain text from TradingView
        if request.is_json:
            data = request.get_json()
            pair       = data.get("pair", "Unknown")
            price      = data.get("price", "Unknown")
            alert_type = data.get("alert_type", "price_crossed")
            zone_type  = data.get("zone_type", "key_level")
            session    = data.get("session", "Unknown")
        else:
            # Plain text alert from TradingView
            raw = request.data.decode("utf-8")
            logger.info(f"Raw alert received: {raw}")
            # Parse simple format: "XAUUSD,4350,supply,London"
            parts = [p.strip() for p in raw.split(",")]
            pair       = parts[0] if len(parts) > 0 else "Unknown"
            price      = parts[1] if len(parts) > 1 else "Unknown"
            zone_type  = parts[2] if len(parts) > 2 else "key_level"
            session    = parts[3] if len(parts) > 3 else "Unknown"
            alert_type = "price_crossed"

        logger.info(f"Alert received: {pair} @ {price} | {zone_type} | {session}")

        # Get Claude analysis
        prompt = build_alert_prompt(pair, price, alert_type, zone_type, session)
        response = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        analysis = response.content[0].text

        # Send to Telegram
        asyncio.run(send_telegram(analysis))

        return jsonify({"status": "ok", "message": "Alert sent to Telegram"}), 200

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/alert", methods=["POST"])
def simple_alert():
    """
    Simplified endpoint for TradingView plain text alerts.
    Set TradingView alert message to just the pair name like: XAUUSD supply London
    """
    try:
        raw = request.data.decode("utf-8").strip()
        parts = raw.split()
        pair     = parts[0] if len(parts) > 0 else "Unknown"
        zone     = parts[1] if len(parts) > 1 else "key_level"
        session  = parts[2] if len(parts) > 2 else "Unknown"
        price    = parts[3] if len(parts) > 3 else "check chart"

        msg = (
            f"🚨 PRICE ALERT — {pair}\n\n"
            f"💰 Price: {price}\n"
            f"📍 Zone: {zone.upper()} ZONE HIT\n"
            f"⏰ Session: {session} CDT\n\n"
            f"📋 ACTION:\n"
            f"1. Open TradingView immediately\n"
            f"2. Check DXY bias\n"
            f"3. Send screenshot for full analysis\n"
            f"4. Wait for LTF confirmation before entering\n\n"
            f"🔔 Send chart screenshot now!"
        )
        asyncio.run(send_telegram(msg))
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"Simple alert error: {e}")
        return jsonify({"status": "error"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Dre's Trading Bot webhook is live!"}), 200


async def send_telegram(message):
    async with bot:
        if len(message) > 4000:
            for i in range(0, len(message), 4000):
                await bot.send_message(chat_id=CHAT_ID, text=message[i:i+4000])
        else:
            await bot.send_message(chat_id=CHAT_ID, text=message)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
