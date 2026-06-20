# Dre's Trading Bot — Complete Setup Guide
# Includes: Telegram Bot + TradingView Webhook Alerts

═══════════════════════════════════════
STEP 1 — GET YOUR API KEYS
═══════════════════════════════════════

A) TELEGRAM BOT TOKEN:
1. Open Telegram → search @BotFather
2. Type /newbot
3. Name it: Dre Trading Assistant
4. Username: dreTradingBot (or any available name)
5. Copy the token BotFather gives you
   Example: 7234567890:AAHdqTcvCH1vGBn...

B) ANTHROPIC API KEY:
1. Go to console.anthropic.com
2. Sign in → API Keys → Create New Key
3. Copy it. Starts with: sk-ant-...
4. Make sure you have $20 credit added

C) YOUR TELEGRAM CHAT ID:
1. Open Telegram → search @userinfobot
2. Type /start
3. It shows your ID — looks like: 123456789
4. Copy this number

═══════════════════════════════════════
STEP 2 — UPLOAD TO GITHUB
═══════════════════════════════════════

1. Go to github.com → New Repository
2. Name it: dre-trading-bot
3. Upload all 5 files:
   - bot.py
   - webhook.py
   - requirements.txt
   - Procfile
   - README.md

═══════════════════════════════════════
STEP 3 — DEPLOY TO RAILWAY
═══════════════════════════════════════

1. Go to railway.app
2. Sign in with GitHub
3. Click New Project → Deploy from GitHub
4. Select your dre-trading-bot repo
5. Add Environment Variables:
   - TELEGRAM_TOKEN = (your bot token)
   - ANTHROPIC_API_KEY = (your API key)
   - TELEGRAM_CHAT_ID = (your chat ID number)
6. Click Deploy
7. Railway gives you a public URL like:
   https://dre-trading-bot.up.railway.app

═══════════════════════════════════════
STEP 4 — SET UP TRADINGVIEW ALERTS
═══════════════════════════════════════

1. Open TradingView
2. Right-click on your chart at a supply/demand zone
3. Click "Add Alert"
4. Set the condition (price crosses, touches, etc.)
5. Under NOTIFICATIONS → check "Webhook URL"
6. Enter your Railway URL + /alert
   Example: https://dre-trading-bot.up.railway.app/alert
7. Set the Alert Message to:
   XAUUSD supply London {{close}}
   (format: PAIR ZONE SESSION PRICE)
8. Click Create

Repeat for every zone on every pair:
- Gold supply: XAUUSD supply London {{close}}
- Gold demand: XAUUSD demand London {{close}}
- EU supply: EURUSD supply London {{close}}
- UJ demand: USDJPY demand NY {{close}}

═══════════════════════════════════════
STEP 5 — TEST EVERYTHING
═══════════════════════════════════════

1. Open Telegram → find your bot → type /start
   You should see the welcome message

2. Test health check — open browser and go to:
   https://your-railway-url.up.railway.app/health
   Should show: "Dre's Trading Bot webhook is live!"

3. Send a chart screenshot to your bot
   Should get back full analysis

4. When TradingView price alert fires
   → Instant Telegram notification with analysis

═══════════════════════════════════════
BOT COMMANDS
═══════════════════════════════════════

/start       — Welcome message
/session     — Switch to day trading mode
/scalp       — Switch to scalping mode
/mode        — Check current mode
/presession  — Pre-session briefing
/checklist   — Daily routine checklist
/risk        — Position size calculator
/ifthen      — If/Then scenarios
/news        — News rules reminder
/dxy         — DXY confluence guide

Send any chart screenshot → instant analysis!

═══════════════════════════════════════
TRADINGVIEW ALERT ZONES TO SET UP
═══════════════════════════════════════

GOLD (XAU/USD):
- Supply zone top: ~$4,380
- Supply zone bottom: ~$4,350
- Demand zone top: ~$4,250
- Demand zone bottom: ~$4,218
- Major swing low: $4,218

EUR/USD:
- Supply zone: 1.1620 - 1.1660
- Demand zone: 1.1480 - 1.1500
- Next target: 1.1300

USD/JPY:
- Demand zone: 159.00 - 159.50
- Breakout level: 160.60
- Major support: 158.80

═══════════════════════════════════════
MONTHLY COST ESTIMATE
═══════════════════════════════════════

- Telegram: FREE
- Railway hosting: FREE tier (enough for personal use)
- Anthropic API: ~$5-15/month depending on usage
- TradingView: your existing plan (alerts are free)

TOTAL: ~$5-15/month
