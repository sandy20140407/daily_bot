# Daily Assistant Bot - Push via Telegram
# Features: Weather, Outfit Advice, News Summary, Exchange Rates

import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import openai

# === Load config from .env ===
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
CITY = os.getenv('CITY', 'Dublin')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai.api_key = OPENAI_API_KEY

# === Weather Info ===
def get_weather():
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={CITY}"
    res = requests.get(url)
    data = res.json()
    temp_c = data['current']['temp_c']
    feelslike_c = data['current']['feelslike_c']
    condition = data['current']['condition']['text']
    wind_kph = data['current']['wind_kph']
    return temp_c, feelslike_c, condition, wind_kph

# === Outfit Suggestion ===
def get_outfit_suggestion(feelslike, condition):
    if feelslike < 0:
        return "冻成狗了宝！穿羽绒服、围巾、帽子、手套全套安排上！🧤🧣🧥"
    elif feelslike < 5:
        return "非常冷，羽绒服+厚裤子+帽子别忘了，风吹脸会痛！🥶"
    elif feelslike < 10:
        return "冷飕飕，建议穿保暖外套 + 长裤，搭配围巾抗风。🧥"
    elif feelslike < 15:
        return "早晚凉，薄外套 + 卫衣刚刚好，风大的话建议带帽子。🌬️"
    elif feelslike < 20:
        return "天气舒适，长袖 or 外套 + 牛仔裤，轻松出门不费劲。😎"
    elif feelslike < 25:
        return "有点热，T恤 + 裙子或短裤，记得防晒霜！☀️"
    else:
        return "炎热爆表，穿得越少越好！轻薄短袖+遮阳帽走起～🌡️🩳"

# === Exchange Rate ===
def get_exchange_rates():
    url = "https://open.er-api.com/v6/latest/EUR"
    try:
        res = requests.get(url)
        data = res.json()
        if 'rates' not in data:
            raise KeyError("'rates' not in fallback API response")
        return data['rates']['USD'], data['rates']['CNY'], data['rates']['SGD']
    except Exception as e:
        return 0.0, 0.0, 0.0

# === News Summary using OpenAI ===
def get_news_summary():
    headlines = [
        "ECB cuts rates by 25 bps amid economic slowdown.",
        "Trump announces new tariffs on EU goods.",
        "Global markets see tech rebound."
    ]
    prompt = """
Summarize the following news headlines into 3 short bullet points:
"""
    prompt += "\n".join(headlines)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes news."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )
        summary = response['choices'][0]['message']['content']
        return summary
    except openai.error.OpenAIError as e:
        return f"[OpenAI API error: {str(e)}]"

# === Telegram Push ===
def push_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    requests.post(url, data=payload)

# === Daily Job ===
def job():
    temp, feelslike, condition, wind = get_weather()
    outfit = get_outfit_suggestion(feelslike, condition)
    usd, cny, sgd = get_exchange_rates()
    news = get_news_summary()

    now = datetime.now().strftime("%Y-%m-%d")
    message = f"*Good morning!* \n\n*📅 {now}*\n\n"
    message += f"*🌤 Weather in {CITY}*: {temp}°C（体感 {feelslike}°C）, {condition}, 风速{wind}km/h\n"
    message += f"*👕 Outfit Tip*: {outfit}\n\n"
    message += f"*📰 News Summary:*\n{news}\n\n"
    message += f"*💱 Exchange Rates (EUR)*:\nUSD: {usd:.4f}, CNY: {cny:.4f}, SGD: {sgd:.4f}"

    push_to_telegram(message)

if __name__ == "__main__":
    job()
