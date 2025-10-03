# Daily Assistant Bot - Push via Telegram
# Features: Weather, Outfit Advice, News Summary, Exchange Rates

import requests
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import feedparser
from time import mktime
import yfinance as yf


# ==== OpenAI v1+ 新用法 ==== 额度用完了，换一个
# from openai import OpenAI

# 可根据需要增删来源；也支持用环境变量 NEWS_FEEDS 覆盖（用逗号分隔）
DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",           # BBC Top Stories
    "https://feeds.reuters.com/reuters/topNews",       # Reuters Top
    "http://rss.cnn.com/rss/edition.rss",              # CNN World
]

# === Load config from .env ===
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID')
WEATHER_API_KEY    = os.getenv('WEATHER_API_KEY')
CITY               = os.getenv('CITY', 'Dublin')
OPENAI_API_KEY     = os.getenv('OPENAI_API_KEY')

# OpenAI 客户端（v1+）
# client = OpenAI(api_key=OPENAI_API_KEY)

# === Weather Info ===
def get_weather():
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={CITY}"
    res = requests.get(url, timeout=15)
    res.raise_for_status()
    data = res.json()
    temp_c      = data['current']['temp_c']
    feelslike_c = data['current']['feelslike_c']
    condition   = data['current']['condition']['text']
    wind_kph    = data['current']['wind_kph']
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
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        data = res.json()
        rates = data.get('rates', {})
        return rates.get('USD', 0.0), rates.get('CNY', 0.0), rates.get('SGD', 0.0)
    except Exception:
        return 0.0, 0.0, 0.0

# === Gold price ===
def get_gold_price():
    try:
        ticker = yf.Ticker("XAUUSD=X")   # 黄金现货（美元）
        data = ticker.history(period="1d")
        if not data.empty:
            return float(data["Close"][-1])
        else:
            return 0.0
    except Exception as e:
        return 0.0

# === News Summary using OpenAI (v1+ SDK) ===
def get_news_summary(max_items=10, per_feed=3):
    """
    聚合多个 RSS：
      - 每个源取 per_feed 条
      - 合并去重（按标题）
      - 按发布时间降序
      - 截断为 max_items 条
      - 返回用于 Telegram 的多行字符串
    """
    feed_list = os.getenv("NEWS_FEEDS", "")
    feeds = [u.strip() for u in feed_list.split(",") if u.strip()] or DEFAULT_FEEDS

    items = []
    for url in feeds:
        d = feedparser.parse(url)
        for entry in d.entries[:per_feed]:
            title = getattr(entry, "title", "").strip()
            if not title:
                continue
            # 发布时间（可能没有，做兼容）
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                dt = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                dt = datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)
            else:
                dt = datetime.now(timezone.utc)
            link = getattr(entry, "link", "").strip()
            items.append({"title": title, "link": link, "dt": dt})

    # 去重（按小写标题）
    seen = set()
    deduped = []
    for it in items:
        k = it["title"].lower()
        if k in seen:
            continue
        seen.add(k)
        deduped.append(it)

    # 按时间最新在前
    deduped.sort(key=lambda x: x["dt"], reverse=True)
    top = deduped[:max_items]

    if not top:
        return "⚠️ No headlines fetched."

    # 组合成简洁的多行文本（Markdown 兼容：不放链接时更稳；要带链接请确保标题不含方括号）
    lines = [f"- {it['title']}" for it in top]
    return "\n".join(lines)

# === Telegram Push ===
def push_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, data=payload, timeout=15)
    except Exception:
        pass

# === Daily Job ===
def job():
    temp, feelslike, condition, wind = get_weather()
    outfit = get_outfit_suggestion(feelslike, condition)
    usd, cny, sgd = get_exchange_rates()
    gold = get_gold_price()
    news = get_news_summary()

    now = datetime.now().strftime("%Y-%m-%d")
    message = (
        f"*Good morning!* \n\n*📅 {now}*\n\n"
        f"*🌤 Weather in {CITY}*: {temp}°C（体感 {feelslike}°C）, {condition}, 风速{wind}km/h\n"
        f"*👕 Outfit Tip*: {outfit}\n\n"
        f"*💱 Exchange Rates (EUR)*:\nUSD: {usd:.4f}, CNY: {cny:.4f}, SGD: {sgd:.4f}\n\n"
        f"\n*🥇 Gold Price*: ${gold:.2f} / oz \n\n"
        f"*📰 News Summary:*\n{news}\n\n"
        
    )
    push_to_telegram(message)

if __name__ == "__main__":
    job()
