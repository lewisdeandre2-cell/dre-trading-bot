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

═══════════════════════════════════════════
DAY TRADING PLAN v5 — SESSION MODE
═══════════════════════════════════════════

INSTRUMENTS: EUR/USD, XAU/USD (Gold), USD/JPY, GBP/USD, USD/CAD
TIMEZONE: All times in CDT

SESSION WINDOWS (CDT):
- Asia: 7PM–1AM | Observe only. Mark Asia High & Low. No trades.
- London Open: 2AM–6AM | PRIMARY entry window
- New York Open: 7AM–11AM | SECONDARY entry window
- Hard Close: 11AM CDT — ALL trades closed. No exceptions.

DXY CONFLUENCE (check FIRST before any pair):
- DXY Bullish → Short EUR/USD | Short Gold | Long USD/JPY
- DXY Bearish → Long EUR/USD | Long Gold | Short USD/JPY
- DXY Consolidation → Trade with caution, reduced size

NEWS RULES:
- Red event: NO TRADE 30 min before and after
- Orange event: Caution, reduced size
- FOMC/Fed = skip entire session

MARKET STRUCTURE:
- Uptrend = HH + HL → BUY ONLY from demand zones
- Downtrend = LL + LH → SELL ONLY from supply zones
- Consolidation = No trades

SUPPLY & DEMAND ZONES:
- Demand Zone: Last candle before large UP move → buy from top of zone
- Supply Zone: Last candle before large DOWN move → sell from bottom of zone
- Fresh zone = highest probability
- Zone tapped + only correction = weakening, reduce size
- Zone pushed through = INVALID, flip bias
- Multiple retests = exhausted, ignore

IMBALANCE:
- Open imbalance above = bullish magnet
- Open imbalance below = bearish magnet
- Extreme zone = final supply/demand with open imbalance = highest probability

RISK MANAGEMENT:
- Risk per trade: 1% of account maximum
- Minimum R:R: 1:2 | Ideal: 1:3+
- Stop: below demand zone low (long) | above supply zone high (short)
- Move stop to break-even at 1:1 R:R
- Hard close: 11AM CDT

IF/THEN SCENARIOS:
- DXY bullish + pair at supply = maximum confluence SHORT
- DXY bearish + pair at demand = maximum confluence LONG
- Asia Low swept → LONG at demand zone
- Asia High swept → SHORT at supply zone
- Supply zone fail → flip to LONG bias
- Demand zone fail → flip to SHORT bias
- Red news imminent → NO TRADE

WHAT TO AVOID:
- Trading Asia session on major pairs
- Entries after 11AM CDT
- Trading during red news events
- Weakened or retested zones
- Chasing moves
- Forcing trades

═══════════════════════════════════════════
SCALPING SYSTEM v1 — SCALP MODE
═══════════════════════════════════════════

PAIRS: XAU/USD, EUR/USD, GBP/USD, USD/JPY (start with EUR/USD only)
TIMEFRAMES: 1M entry | 5M setup | 15M/1H context | 4H/Daily bias filter

SCALPING WINDOWS (CDT):
- London Open: 2AM–4AM | BEST window
- London Mid: 4AM–6AM | Good
- NY Open: 7AM–9AM | BEST second window
- NY Mid: 9AM–11AM | Acceptable
- AVOID: After 11AM CDT

THE FIVE SCALP SETUPS:
1. Asia Sweep Scalp — Asia High/Low swept on 5M with reversal candle
2. Session Open Break — price breaks pre-session range at London/NY open
3. Supply/Demand Scalp — price taps zone on 5M with rejection candle
4. Imbalance Fill — open price range acting as magnet on 5M
5. Structure Break Scalp — 1M BOS with momentum, enter on retest

SETUP QUALITY & RISK:
- A+ Setup: 1% risk | 1:3 minimum R:R
- A Setup: 0.5% risk | 1:2 minimum R:R
- B Setup: 0.25% risk | 1:2 minimum R:R
- No Setup: 0% — do not trade

DXY FOR SCALPING:
- Check DXY 1M at EVERY session open
- DXY spikes UP = short EUR/USD and Gold, long USD/JPY
- DXY drops DOWN = long EUR/USD and Gold, short USD/JPY

SCALP RISK RULES:
- Maximum daily loss: 2% of account
- 3 consecutive losses = END SESSION IMMEDIATELY
- Move stop to break-even at 1:1
- Exit if target not reached within 10 minutes
- Maximum stop: 15 pips forex | $15 Gold

SCALP IF/THEN:
- Asia Low swept + reversal candle → LONG scalp, stop below sweep, target Asia High
- Asia High swept + reversal candle → SHORT scalp, stop above sweep, target Asia Low
- London breaks Asia High on 1M → LONG scalp
- London breaks Asia Low on 1M → SHORT scalp
- 5M bearish rejection at supply → SHORT scalp
- 5M bullish rejection at demand → LONG scalp
- DXY spikes UP at open → short EU/Gold, long UJ immediately
- 3 consecutive losses → STOP SESSION NOW

SCALP AVOID:
- Scalping against 4H/Daily trend
- Scalping during red news events
- After 11AM CDT
- More than 3 losing scalps
- Holding scalp longer than 15 minutes

═══════════════════════════════════════════
RESPONSE FORMAT — always use this format
═══════════════════════════════════════════

📊 MODE: [Session Trading / Scalping]
📈 PAIR: [pair name] | ⏰ [CDT session window]

🔍 NARRATIVE:
[2-3 sentences — who is in control and why]

📍 KEY LEVELS:
• Supply/Resistance: [levels]
• Demand/Support: [levels]
• Asia High: [level] | Asia Low: [level]

🎯 BIAS: [BULLISH/BEARISH/NEUTRAL] — [reason]

💡 IF/THEN:
• IF [X] → THEN [action] | Entry: [level] | Stop: [level] | Target: [level]
• IF [Y] → THEN [action] | Entry: [level] | Stop: [level] | Target: [level]

⚠️ WATCH: [news events or cautions]

📋 BOTTOM LINE: [one clear actionable sentence]

Keep responses concise and mobile-friendly.
"""

user_mode = {}

def get_mode(user_id): return user_mode.get(user_id, "session")

async def start(update, context):
    await update.message.reply_text(
        "👋 What's good Dre! Your trading bot is live.\n\n"
        "📊 Default: Session Trading (Day Trading Plan v5)\n\n"
        "COMMANDS:\n"
        "/session — Day trading mode\n"
        "/scalp — Scalping mode\n"
        "/mode — Check current mode\n"
        "/presession — Pre-session briefing\n"
        "/checklist — Daily routine\n"
        "/risk — Position size calculator\n"
        "/ifthen — If/Then scenarios\n"
        "/news — News rules reminder\n"
        "/dxy — DXY confluence guide\n\n"
        "📸 Send any chart screenshot for instant analysis!"
    )

async def session_mode(update, context):
    user_mode[update.effective_user.id] = "session"
    await update.message.reply_text(
        "📊 SESSION TRADING MODE ACTIVE\n\n"
        "Using Day Trading Plan v5\n\n"
        "Windows (CDT):\n"
        "• London: 2AM–6AM\n"
        "• NY: 7AM–11AM\n"
        "• Hard close: 11AM\n\n"
        "Send a chart to get started! 📸"
    )

async def scalp_mode(update, context):
    user_mode[update.effective_user.id] = "scalp"
    await update.message.reply_text(
        "⚡ SCALP MODE ACTIVE\n\n"
        "Using Scalping System v1\n\n"
        "Best windows (CDT):\n"
        "• London Open: 2AM–4AM ⭐\n"
        "• NY Open: 7AM–9AM ⭐\n"
        "• Hard stop: 11AM\n\n"
        "Remember: 3 losses = STOP SESSION\n\n"
        "Send a chart to get started! 📸"
    )

async def mode_check(update, context):
    mode = get_mode(update.effective_user.id)
    label = "📊 SESSION TRADING MODE" if mode == "session" else "⚡ SCALP MODE"
    await update.message.reply_text(f"Current mode: {label}")

async def presession(update, context):
    mode = get_mode(update.effective_user.id)
    if mode == "session":
        await update.message.reply_text(
            "📋 PRE-SESSION CHECKLIST (CDT)\n\n"
            "PREP (before 7PM CDT):\n"
            "☐ Forex Factory — red events noted\n"
            "☐ No-trade windows marked\n"
            "☐ DXY 4H bias confirmed\n"
            "☐ HTF trend confirmed on pairs\n"
            "☐ Supply/demand zones marked\n"
            "☐ Open imbalances marked\n"
            "☐ If/Then scenarios written\n"
            "☐ Price alerts set\n\n"
            "ASIA (7PM–1AM CDT):\n"
            "☐ Asia High marked\n"
            "☐ Asia Low marked\n"
            "☐ DO NOT TRADE\n\n"
            "LONDON (2AM CDT):\n"
            "☐ News check\n"
            "☐ DXY confirms bias\n"
            "☐ Asia sweep confirmed\n"
            "☐ Zone fresh + LTF confirmed\n"
            "☐ 1:2 R:R minimum\n\n"
            "NY (7AM CDT):\n"
            "☐ News check\n"
            "☐ London move assessed\n"
            "☐ LTF structure break confirmed\n\n"
            "🔴 HARD CLOSE: 11AM CDT"
        )
    else:
        await update.message.reply_text(
            "⚡ SCALP PRE-SESSION (CDT)\n\n"
            "PREP (by 1:30AM CDT):\n"
            "☐ Forex Factory — red events?\n"
            "☐ DXY 4H bias confirmed\n"
            "☐ HTF trend confirmed\n"
            "☐ Asia High/Low marked on 15M\n"
            "☐ Zones marked on 5M\n"
            "☐ Imbalances marked\n"
            "☐ If/Then written\n"
            "☐ Spread normal on broker\n"
            "☐ DXY 1M chart open\n\n"
            "LONDON (2AM CDT):\n"
            "☐ DXY 1M direction at open\n"
            "☐ Asia sweep on 5M?\n"
            "☐ Setup → 1M confirm → execute\n\n"
            "NY (7AM CDT):\n"
            "☐ News check\n"
            "☐ DXY 1M at open\n"
            "☐ NY reversal setup?\n\n"
            "🔴 RULES:\n"
            "• 3 losses = END SESSION\n"
            "• 2% daily max loss\n"
            "• Hard stop: 11AM CDT"
        )

async def checklist(update, context):
    await update.message.reply_text(
        "✅ DAILY CHECKLIST\n\n"
        "PRE-SESSION:\n"
        "☐ Forex Factory checked\n"
        "☐ No-trade windows marked\n"
        "☐ DXY 4H bias confirmed\n"
        "☐ HTF trend confirmed\n"
        "☐ Zones + imbalances marked\n"
        "☐ If/Then scenarios written\n"
        "☐ Alerts set\n\n"
        "ASIA (7PM–1AM):\n"
        "☐ Asia High + Low marked\n"
        "☐ NO TRADES\n\n"
        "LONDON (2AM–6AM):\n"
        "☐ News + DXY checked\n"
        "☐ Asia sweep confirmed\n"
        "☐ Zone fresh + valid\n"
        "☐ LTF structure confirmed\n"
        "☐ Trade logged\n\n"
        "NY (7AM–11AM):\n"
        "☐ News checked\n"
        "☐ LTF break confirmed\n"
        "☐ Trade logged\n\n"
        "END OF DAY (11AM):\n"
        "☐ ALL trades closed\n"
        "☐ Results logged\n"
        "☐ Rule violations noted"
    )

async def risk_calc(update, context):
    await update.message.reply_text(
        "💰 POSITION SIZE CALCULATOR\n\n"
        "Formula:\n"
        "Lots = (Account × Risk%) ÷ (Stop Pips × Pip Value)\n\n"
        "QUICK GUIDE:\n"
        "$1,000 @ 1% = $10 max risk\n"
        "$5,000 @ 1% = $50 max risk\n"
        "$10,000 @ 1% = $100 max risk\n\n"
        "PIP VALUES:\n"
        "• EUR/USD: $10/pip (standard lot)\n"
        "• GBP/USD: $10/pip\n"
        "• USD/JPY: ~$9/pip\n"
        "• Gold: $1 per $1 move\n\n"
        "EXAMPLE:\n"
        "$5,000 | 1% risk | 20 pip stop | EUR/USD\n"
        "= $50 ÷ (20 × $10) = 0.25 lots\n\n"
        "SCALP RISK:\n"
        "• A+ Setup: 1%\n"
        "• A Setup: 0.5%\n"
        "• B Setup: 0.25%\n\n"
        "Send: ACCOUNT, STOP PIPS, PAIR\n"
        "Example: $5000, 15 pips, EURUSD\n"
        "I'll calculate your exact lot size!"
    )

async def ifthen(update, context):
    mode = get_mode(update.effective_user.id)
    if mode == "session":
        await update.message.reply_text(
            "💡 SESSION IF/THEN SCENARIOS\n\n"
            "DXY:\n"
            "• DXY bullish + supply zone → SHORT max confluence\n"
            "• DXY bearish + demand zone → LONG max confluence\n\n"
            "ASIA SWEEP:\n"
            "• Asia Low swept → LONG at demand\n"
            "• Asia High swept → SHORT at supply\n\n"
            "ZONE FAILS:\n"
            "• Supply fails (breaks high) → flip LONG\n"
            "• Demand fails (breaks low) → flip SHORT\n\n"
            "SESSION:\n"
            "• LTF structure break + HTF agree → EXECUTE\n"
            "• NY open + LTF reversal break → reversal trade\n"
            "• Red news imminent → NO TRADE\n\n"
            "ZONE STRENGTH:\n"
            "• Only correction produced → reduce size\n"
            "• Multiple retests → skip zone"
        )
    else:
        await update.message.reply_text(
            "⚡ SCALP IF/THEN SCENARIOS\n\n"
            "ASIA SWEEP:\n"
            "• Asia Low swept + 5M reversal\n"
            "  → LONG | Stop: below sweep | Target: Asia High\n\n"
            "• Asia High swept + 5M reversal\n"
            "  → SHORT | Stop: above sweep | Target: Asia Low\n\n"
            "SESSION OPEN:\n"
            "• London breaks Asia High on 1M\n"
            "  → LONG | Stop: below Asia High\n\n"
            "• London breaks Asia Low on 1M\n"
            "  → SHORT | Stop: above Asia Low\n\n"
            "ZONE SCALPS:\n"
            "• 5M bearish rejection at supply\n"
            "  → SHORT | Stop: above zone | Target: imbalance\n\n"
            "• 5M bullish rejection at demand\n"
            "  → LONG | Stop: below zone | Target: imbalance\n\n"
            "DXY:\n"
            "• DXY spikes UP → short EU/Gold, long UJ\n"
            "• DXY drops DOWN → long EU/Gold, short UJ\n\n"
            "SAFETY:\n"
            "• 3 losses → STOP SESSION NOW\n"
            "• Spread widens → DO NOT ENTER"
        )

async def news_reminder(update, context):
    await update.message.reply_text(
        "📰 NEWS RULES (Forex Factory)\n\n"
        "🔴 RED = HIGH IMPACT:\n"
        "• No trades 30 min before\n"
        "• No trades 30 min after\n"
        "• FOMC/Fed = skip entire session\n\n"
        "🟠 ORANGE = MEDIUM:\n"
        "• Caution + reduced size\n\n"
        "🟡 YELLOW = LOW:\n"
        "• Proceed normally\n\n"
        "KEY MOVERS:\n"
        "• USD events → all your pairs\n"
        "• EUR events → EUR/USD\n"
        "• JPY events → USD/JPY\n"
        "• Gold → most sensitive to USD\n\n"
        "⚠️ FOMC is the biggest event.\n"
        "It moved Gold $160 and EUR/USD\n"
        "110 pips in one candle!\n\n"
        "forexfactory.com → Filter: Red only\n"
        "Set timezone to CDT"
    )

async def dxy_guide(update, context):
    await update.message.reply_text(
        "💵 DXY CONFLUENCE GUIDE\n\n"
        "Check 4H chart BEFORE any pair.\n\n"
        "DXY BULLISH:\n"
        "• Short EUR/USD ↓\n"
        "• Short Gold ↓\n"
        "• Long USD/JPY ↑\n"
        "• Short GBP/USD ↓\n\n"
        "DXY BEARISH:\n"
        "• Long EUR/USD ↑\n"
        "• Long Gold ↑\n"
        "• Short USD/JPY ↓\n"
        "• Long GBP/USD ↑\n\n"
        "DXY CONSOLIDATION:\n"
        "• No clear bias\n"
        "• Zone setups only\n"
        "• Reduce all sizes\n\n"
        "MAX CONFLUENCE:\n"
        "• DXY at demand + pair at supply\n"
        "  = maximum SHORT confidence\n"
        "• DXY at supply + pair at demand\n"
        "  = maximum LONG confidence\n\n"
        "FOR SCALPING:\n"
        "• Check DXY 1M at session open\n"
        "• Spike UP = dollar strength now\n"
        "• Drop DOWN = dollar weakness now\n\n"
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
            {"type": "text", "text": f"{mode_instruction}\n\nAnalyze this trading chart using my full trading plan rules. {caption}"}
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
        await update.message.reply_text("⚠️ Something went wrong. Try again or send a clearer screenshot.")

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
