# Daily Assistant Bot - Push via Telegram
# Features: Weather, Outfit Advice, News Summary, Exchange Rates, Gold Price

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from time import mktime

import feedparser
import requests
import yfinance as yf
from dotenv import load_dotenv

# === Logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# 可根据需要增删来源；也支持用环境变量 NEWS_FEEDS 覆盖（用逗号分隔）
DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",       # BBC Top Stories
    "https://feeds.reuters.com/reuters/topNews",    # Reuters Top
    "http://rss.cnn.com/rss/edition.rss",           # CNN World
]

# === Load config from .env ===
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID')
WEATHER_API_KEY    = os.getenv('WEATHER_API_KEY')
CITY               = os.getenv('CITY', 'Singapore')

# 雨/雪相关的天气关键词，用于穿衣建议追加提醒
_RAIN_KEYWORDS = re.compile(r"rain|drizzle|shower|thunderstorm|sleet", re.I)
_SNOW_KEYWORDS = re.compile(r"snow|blizzard|ice", re.I)


# === Weather Info ===
def get_weather():
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={CITY}"
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        data = res.json()
        cur = data['current']
        return cur['temp_c'], cur['feelslike_c'], cur['condition']['text'], cur['wind_kph']
    except Exception as exc:
        log.error("Failed to fetch weather: %s", exc)
        return None, None, None, None


# === Outfit Suggestion ===
def get_outfit_suggestion(feelslike, condition):
    if feelslike is None:
        return "天气数据暂不可用，请自行查看天气穿衣哦 🤷"

    if feelslike < 0:
        tip = "冻成狗了宝！穿羽绒服、围巾、帽子、手套全套安排上！🧤🧣🧥"
    elif feelslike < 5:
        tip = "非常冷，羽绒服+厚裤子+帽子别忘了，风吹脸会痛！🥶"
    elif feelslike < 10:
        tip = "冷飕飕，建议穿保暖外套 + 长裤，搭配围巾抗风。🧥"
    elif feelslike < 15:
        tip = "早晚凉，薄外套 + 卫衣刚刚好，风大的话建议带帽子。🌬️"
    elif feelslike < 20:
        tip = "天气舒适，长袖 or 外套 + 牛仔裤，轻松出门不费劲。😎"
    elif feelslike < 25:
        tip = "有点热，T恤 + 裙子或短裤，记得防晒霜！☀️"
    elif feelslike < 32:
        tip = "有点闷热，轻薄透气最重要！短袖短裤+防晒一定要有 ☀️"
    elif feelslike < 35:
        tip = "体感高温！尽量待在空调房，多喝水，别被热化了 😵‍💫💦"
    else:
        tip = "桑拿模式MAX！能不出门就别出门，出门记得防晒+遮阳伞！🔥🫠"

    # 根据天气状况追加雨雪提醒
    if condition:
        if _RAIN_KEYWORDS.search(condition):
            tip += "\n⚠️ 有雨，记得带伞！🌂"
        elif _SNOW_KEYWORDS.search(condition):
            tip += "\n⚠️ 有雪，穿防滑鞋，注意路面结冰！❄️"

    return tip


# === Exchange Rate ===
def get_exchange_rates():
    try:
        url = "https://open.er-api.com/v6/latest/EUR"
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        rates = res.json().get('rates', {})
        return rates.get('USD', 0.0), rates.get('CNY', 0.0), rates.get('SGD', 0.0)
    except Exception as exc:
        log.error("Failed to fetch exchange rates: %s", exc)
        return 0.0, 0.0, 0.0


# === Gold price ===
def get_gold_price():
    """
    依次尝试 Yahoo Finance 的黄金代码：
      1) XAUUSD=X  现货黄金（美元）
      2) XAU=X     现货黄金（美元，另一写法）
      3) GC=F      COMEX 黄金期货（作为兜底）
    返回: (price_usd_per_oz, symbol_used)
    """
    candidates = ["XAUUSD=X", "XAU=X", "GC=F"]
    for sym in candidates:
        try:
            data = yf.download(sym, period="5d", interval="1d", progress=False)
            close = data["Close"].dropna()
            if not close.empty:
                return float(close.iloc[-1]), sym
        except Exception as exc:
            log.warning("Gold price fetch failed for %s: %s", sym, exc)
            continue
    log.error("All gold price sources failed")
    return 0.0, None


# === News Summary ===
def _fetch_feed(url, per_feed):
    """获取单个 RSS 源的条目，带超时保护。"""
    try:
        # 用 requests 先下载 RSS XML，确保有超时
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        d = feedparser.parse(res.content)
    except Exception as exc:
        log.warning("RSS fetch failed for %s: %s", url, exc)
        return []

    items = []
    for entry in d.entries[:per_feed]:
        title = getattr(entry, "title", "").strip()
        if not title:
            continue
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            dt = datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        link = getattr(entry, "link", "").strip()
        items.append({"title": title, "link": link, "dt": dt})
    return items


def get_news_summary(max_items=10, per_feed=3):
    """
    聚合多个 RSS：
      - 每个源取 per_feed 条（并行获取）
      - 合并去重（按标题）
      - 按发布时间降序
      - 截断为 max_items 条
    """
    feed_list = os.getenv("NEWS_FEEDS", "")
    feeds = [u.strip() for u in feed_list.split(",") if u.strip()] or DEFAULT_FEEDS

    # 并行拉取各 RSS 源
    items = []
    with ThreadPoolExecutor(max_workers=len(feeds)) as pool:
        futures = {pool.submit(_fetch_feed, url, per_feed): url for url in feeds}
        for fut in as_completed(futures):
            items.extend(fut.result())

    # 去重（按小写标题）
    seen = set()
    deduped = []
    for it in items:
        k = it["title"].lower()
        if k not in seen:
            seen.add(k)
            deduped.append(it)

    deduped.sort(key=lambda x: x["dt"], reverse=True)
    top = deduped[:max_items]

    if not top:
        return "⚠️ No headlines fetched."

    lines = [f"- {_escape_markdown(it['title'])}" for it in top]
    return "\n".join(lines)


# === Telegram helpers ===
def _escape_markdown(text):
    """转义 Telegram Markdown V1 特殊字符，避免消息解析失败。"""
    # Telegram Markdown V1 的特殊字符：* _ ` [
    return re.sub(r"([*_`\[])", r"\\\1", text)


def push_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        resp = requests.post(url, data=payload, timeout=15)
        if not resp.ok:
            log.error("Telegram API error %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        log.error("Failed to push message to Telegram: %s", exc)


# === Daily Job ===
def job():
    log.info("Daily job started")

    # 并行获取天气、汇率、金价、新闻
    with ThreadPoolExecutor(max_workers=4) as pool:
        weather_fut = pool.submit(get_weather)
        rates_fut   = pool.submit(get_exchange_rates)
        gold_fut    = pool.submit(get_gold_price)
        news_fut    = pool.submit(get_news_summary)

        temp, feelslike, condition, wind = weather_fut.result()
        usd, cny, sgd = rates_fut.result()
        gold_usd, gold_sym = gold_fut.result()
        news = news_fut.result()

    outfit = get_outfit_suggestion(feelslike, condition)
    gold_eur = (gold_usd / usd) if (gold_usd and usd) else 0.0

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 天气部分：如果获取失败则显示占位信息
    if temp is not None:
        weather_line = f"*🌤 Weather in {CITY}*: {temp}°C（体感 {feelslike}°C）, {condition}, 风速{wind}km/h"
    else:
        weather_line = f"*🌤 Weather in {CITY}*: 数据获取失败，请稍后手动查看"

    message = (
        f"*Good morning!* \n\n*📅 {now}*\n\n"
        f"{weather_line}\n"
        f"*👕 Outfit Tip*: {outfit}\n\n"
        f"*💱 Exchange Rates (EUR)*:\nUSD: {usd:.4f}, CNY: {cny:.4f}, SGD: {sgd:.4f}\n\n"
        f"*🥇 Gold*: ${gold_usd:.2f}/oz (~€{gold_eur:.2f}/oz){'' if not gold_sym else f' \\[{gold_sym}\\]'}\n\n"
        f"*📰 News Summary:*\n{news}\n\n"
    )
    push_to_telegram(message)
    log.info("Daily job finished")


if __name__ == "__main__":
    job()
