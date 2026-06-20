import os
import logging
import base64
import anthropic
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_KEY  = os.environ["ANTHROPIC_API_KEY"]
client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

SYSTEM_PROMPT = """
You are Dre's personal AI trading assistant. Dre is a day trader based in Oklahoma City, Oklahoma.
All times must be given in CDT (Central Daylight Time).

You have two modes:
1. SESSION MODE — Day Trading Plan v5 (default)
2. SCALP MODE — Scalping System v1

Always state which mode is active at the top of every response:
📊 MODE: Session Trading  OR  ⚡ MODE: Scalping

SESSION MODE RULES:
- Instruments: EUR/USD, XAU/USD (Gold), USD/JPY, GBP/USD
- Asia session 7PM-1AM CDT: observe only, mark High/Low, no trades
- London open 2AM-6AM CDT: PRIMARY entry window
- NY open 7AM-11AM CDT: SECONDARY entry window
- Hard close: 11AM CDT — all trades closed, no exceptions
- Check DXY FIRST before any pair analysis
- DXY Bullish = Short EUR/USD, Short Gold, Long USD/JPY
- DXY Bearish = Long EUR/USD, Long Gold, Short USD/JPY
- Red news event = NO TRADE 30 min before and after
- Only buy demand zones in uptrends (HH+HL structure)
- Only sell supply zones in downtrends (LL+LH structure)
- Fresh zone = highest probability. Retested zone = skip.
- Zone fail (price breaks through) = flip bias direction
- Risk: 1% per trade max. Min R:R 1:2. Ideal 1:3+
- Asia Low swept = look for LONG at demand zone
- Asia High swept = look for SHORT at supply zone
- LTF structure break must confirm HTF direction before entry

SCALP MODE RULES:
- Best windows: London 2AM-4AM CDT, NY 7AM-9AM CDT
- Timeframes: 1M entry, 5M setup, 15M context
- 5 setups: Asia Sweep, Session Open Break, S/D Scalp, Imbalance Fill, Structure Break
- A+ setup: 1% risk, 1:3 R:R min
- A setup: 0.5% risk, 1:2 R:R min
- B setup: 0.25% risk, 1:2 R:R min
- 3 consecutive losses = END SESSION IMMEDIATELY
- Max daily loss: 2% of account
- Hard stop: 11AM CDT

RESPONSE FORMAT:
📊 MODE: [Session Trading / Scalping]
📈 PAIR: [pair] | ⏰ [CDT session]

🔍 NARRATIVE:
[2-3 sentences on who is in control and why]

📍 KEY LEVELS:
• Supply/Resistance: [levels]
• Demand/Support: [levels]
• Asia High: [level] | Asia Low: [level]

🎯 BIAS: [BULLISH/BEARISH/NEUTRAL] — [reason]

💡 IF/THEN:
• IF [condition] → THEN [action] | Entry: X | Stop: X | Target: X
• IF [condition] → THEN [action] | Entry: X | Stop: X | Target: X

⚠️ WATCH: [news or cautions]

📋 BOTTOM LINE: [one clear action sentence]

Keep responses concise and mobile-friendly.
"""

user_mode = {}

def get_mode(user_id):
    return user_mode.get(user_id, "session")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 What's good Dre! Your trading bot is live.\n\n"
        "📊 Default: Session Trading Mode\n\n"
        "COMMANDS:\n"
        "/session — Day trading mode\n"
        "/scalp — Scalping mode\n"
        "/mode — Check current mode\n"
        "/presession — Pre-session briefing\n"
        "/checklist — Daily routine\n"
        "/risk — Position size help\n"
        "/ifthen — If/Then scenarios\n"
        "/news — News rules\n"
        "/dxy — DXY guide\n\n"
        "📸 Send any chart screenshot for instant analysis!"
    )

async def session_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_mode[update.effective_user.id] = "session"
    await update.message.reply_text("📊 SESSION TRADING MODE ACTIVE\n\nUsing Day Trading Plan v5\nLondon: 2AM-6AM CDT | NY: 7AM-11AM CDT\nHard close: 11AM CDT\n\nSend a chart! 📸")

async def scalp_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_mode[update.effective_user.id] = "scalp"
    await update.message.reply_text("⚡ SCALP MODE ACTIVE\n\nUsing Scalping System v1\nBest: London 2AM-4AM | NY 7AM-9AM CDT\nHard stop: 11AM CDT\n3 losses = STOP SESSION\n\nSend a chart! 📸")

async def mode_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = get_mode(update.effective_user.id)
    label = "📊 SESSION TRADING MODE" if mode == "session" else "⚡ SCALP MODE"
    await update.message.reply_text(f"Current mode: {label}")

async def presession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 PRE-SESSION CHECKLIST\n\n"
        "☐ Forex Factory — red events (CDT)\n"
        "☐ DXY 4H bias confirmed\n"
        "☐ HTF trend confirmed\n"
        "☐ Zones + imbalances marked\n"
        "☐ If/Then scenarios written\n"
        "☐ Asia H/L marked\n"
        "☐ Alerts set\n\n"
        "LONDON (2AM CDT):\n"
        "☐ News + DXY checked\n"
        "☐ Asia sweep confirmed\n"
        "☐ Zone fresh + LTF confirmed\n\n"
        "NY (7AM CDT):\n"
        "☐ News checked\n"
        "☐ LTF break confirmed\n\n"
        "🔴 HARD CLOSE: 11AM CDT"
    )

async def checklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ DAILY CHECKLIST\n\n"
        "☐ Forex Factory checked\n"
        "☐ DXY 4H bias confirmed\n"
        "☐ HTF trend confirmed\n"
        "☐ Zones marked\n"
        "☐ If/Then written\n"
        "☐ Asia H/L marked\n"
        "☐ Trades logged\n"
        "☐ ALL closed by 11AM CDT"
    )

async def risk_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 POSITION SIZE\n\n"
        "Lots = (Account × 1%) ÷ (Stop × Pip Value)\n\n"
        "$5,000 | 20 pip stop | EUR/USD\n"
        "= $50 ÷ 200 = 0.25 lots\n\n"
        "Pip Values:\n"
        "EUR/USD: $10/pip\n"
        "GBP/USD: $10/pip\n"
        "USD/JPY: ~$9/pip\n"
        "Gold: $1 per $1\n\n"
        "Send: ACCOUNT, STOP, PAIR\n"
        "Example: $5000, 20, EURUSD"
    )

async def ifthen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = get_mode(update.effective_user.id)
    if mode == "session":
        await update.message.reply_text(
            "💡 SESSION IF/THEN\n\n"
            "• DXY bullish + supply → SHORT\n"
            "• DXY bearish + demand → LONG\n"
            "• Asia Low swept → LONG at demand\n"
            "• Asia High swept → SHORT at supply\n"
            "• Supply fails → flip LONG\n"
            "• Demand fails → flip SHORT\n"
            "• LTF + HTF agree → EXECUTE\n"
            "• Red news → NO TRADE"
        )
    else:
        await update.message.reply_text(
            "⚡ SCALP IF/THEN\n\n"
            "• Asia Low swept + reversal → LONG\n"
            "• Asia High swept + reversal → SHORT\n"
            "• London breaks Asia High → LONG\n"
            "• London breaks Asia Low → SHORT\n"
            "• 5M rejection at supply → SHORT\n"
            "• 5M rejection at demand → LONG\n"
            "• DXY spikes UP → short EU/Gold\n"
            "• DXY drops DOWN → long EU/Gold\n"
            "• 3 losses → STOP NOW"
        )

async def news_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📰 NEWS RULES\n\n"
        "🔴 RED = NO TRADE\n"
        "30 min before + after\n"
        "FOMC = skip entire session\n\n"
        "🟠 ORANGE = CAUTION\n"
        "Reduce size + wider stops\n\n"
        "🟡 YELLOW = NORMAL\n\n"
        "forexfactory.com\n"
        "Filter: Red | Timezone: CDT"
    )

async def dxy_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💵 DXY GUIDE\n\n"
        "Check 4H BEFORE any pair.\n\n"
        "DXY BULLISH:\n"
        "Short EUR/USD | Short Gold | Long UJ\n\n"
        "DXY BEARISH:\n"
        "Long EUR/USD | Long Gold | Short UJ\n\n"
        "DXY CONSOLIDATION:\n"
        "No bias — reduce all sizes\n\n"
        "Send DXY chart for analysis! 📸"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = get_mode(user_id)
    mode_instruction = (
        "You are in SESSION TRADING MODE. Apply Day Trading Plan v5 rules."
        if mode == "session"
        else "You are in SCALP MODE. Apply Scalping System v1 rules."
    )

    if update.message.photo:
        await update.message.reply_text("📸 Analyzing your chart... hang tight Dre!")
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        import httpx
        async with httpx.AsyncClient() as http:
            img_resp = await http.get(file.file_path)
        img_b64 = base64.standard_b64encode(img_resp.content).decode("utf-8")
        caption = update.message.caption or ""
        user_content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
            {"type": "text", "text": f"{mode_instruction}\n\nAnalyze this trading chart. {caption}"}
        ]
    else:
        text = update.message.text or ""
        if not text:
            return
        user_content = [{"type": "text", "text": f"{mode_instruction}\n\nDre asks: {text}"}]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}]
        )
        reply = response.content[0].text
        if len(reply) > 4000:
            for i in range(0, len(reply), 4000):
                await update.message.reply_text(reply[i:i+4000])
        else:
            await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("⚠️ Something went wrong. Try again!")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("session",    session_mode))
    app.add_handler(CommandHandler("scalp",      scalp_mode))
    app.add_handler(CommandHandler("mode",       mode_check))
    app.add_handler(CommandHandler("presession", presession))
    app.add_handler(CommandHandler("checklist",  checklist))
    app.add_handler(CommandHandler("risk",       risk_calc))
    app.add_handler(CommandHandler("ifthen",     ifthen))
    app.add_handler(CommandHandler("news",       news_reminder))
    app.add_handler(CommandHandler("dxy",        dxy_guide))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Dre Trading Bot is live!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
