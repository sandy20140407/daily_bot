# 📄 Deployment Guide

## 🧠 Project: Daily Assistant Bot
This bot sends you a personalized daily briefing including:
- 🌤 Weather & feels-like temperature
- 👕 Outfit suggestion
- 📰 Global news summary
- 💱 EUR exchange rates

## 🚀 Getting Started

### 1. Clone the project
```bash
git clone https://github.com/sandy20140407/daily-assistant-bot.git
cd daily-assistant-bot
```

### 2. Create a virtual environment (optional but recommended)
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create `.env` file
```ini
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
WEATHER_API_KEY=your_weather_api_key
OPENAI_API_KEY=your_openai_api_key
CITY=Dublin
```

## 🛠 How to Set Up Telegram Bot & Get Chat ID

### Step 1: Create a Telegram Bot
1. Open Telegram and search `@BotFather`
2. Send `/start` then `/newbot`
3. Give it a name (e.g., `DailyBot`)
4. Set a username (must end with `_bot`, e.g., `mydaily_bot`)
5. You'll get a `TELEGRAM_BOT_TOKEN` like `123456:ABCdefGhijkLMNOP`

### Step 2: Get Your Telegram Chat ID
1. Start a chat with your new bot (just say hi)
2. Open this URL in browser:
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```
3. You'll see something like:
```json
{"message":{"chat":{"id":123456789}}}
```
Copy that `id` — it's your `TELEGRAM_CHAT_ID`

### Step 3: Add Both to Your `.env`
```
TELEGRAM_BOT_TOKEN=123456:ABCdefGhijkLMNOP
TELEGRAM_CHAT_ID=123456789
```

## 🌤 How to Get Weather API Key
1. Visit [https://www.weatherapi.com/](https://www.weatherapi.com/)
2. Register a free account
3. Login and go to your dashboard
4. Copy your API key from "Your API Keys"
5. Paste it into your `.env` as `WEATHER_API_KEY`

### 5. Run the bot manually (test)
```bash
python bot.py
```

### 6. Setup crontab for daily automation (macOS/Linux)
```bash
crontab -e
```
Add this line to run daily at 8:00am:
```bash
0 8 * * * /usr/bin/python3 /absolute/path/to/bot.py
```

---

## 📦 requirements.txt
```
requests
python-dotenv
openai
```

## ❤️ Credits
This tool was built by me, with the help of ChatGPT ✨

Enjoy your custom morning Telegram briefing! ☕
"""
