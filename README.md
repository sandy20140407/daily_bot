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

## 配置 Secrets & Variables（安全注入）

到仓库 Settings → Secrets and variables → Actions：

### Repository Secrets（敏感信息）

新增这些条目：

```
TELEGRAM_BOT_TOKEN

TELEGRAM_CHAT_ID

WEATHER_API_KEY

（可选）OPENAI_API_KEY — 如你已弃用，可不配
```

### Repository Variables（非敏感配置）

新增这些条目（可按需）：

```
NEWS_FEEDS（逗号分隔的 RSS 列表）

https://feeds.bbci.co.uk/news/rss.xml, https://feeds.reuters.com/reuters/topNews, http://rss.cnn.com/rss/edition.rss


NEWS_MAX_ITEMS（默认 5）

NEWS_PER_FEED（默认 3）

CITY（默认 Dublin）
```

### 新建 GitHub Actions 工作流

在仓库中新建文件：.github/workflows/daily-bot.yml

```
name: daily-bot

on:
  schedule:
    # ⚠️ GitHub 使用 UTC 时间！
    # 每天 06:30 UTC（= 伦敦夏令时 07:30；冬令时 06:30）
    - cron: "30 6 * * *"
    # 如需全年“伦敦本地固定 07:30”，可加第二条（冬季生效）：
    # - cron: "30 7 * * *"
  workflow_dispatch: {}   # 支持手动触发测试

jobs:
  run:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    concurrency:
      group: ${{ github.workflow }}-${{ github.ref }}
      cancel-in-progress: true

    # 全局环境（非敏感，或改用 repo variables）
    env:
      CITY: ${{ vars.CITY }}
      NEWS_MAX_ITEMS: ${{ vars.NEWS_MAX_ITEMS }}
      NEWS_PER_FEED: ${{ vars.NEWS_PER_FEED }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run bot
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID:   ${{ secrets.TELEGRAM_CHAT_ID }}
          WEATHER_API_KEY:    ${{ secrets.WEATHER_API_KEY }}
          OPENAI_API_KEY:     ${{ secrets.OPENAI_API_KEY }}   # 若不用可删除
          NEWS_FEEDS:         ${{ vars.NEWS_FEEDS }}          # 也可不配，走默认
          CITY:               ${{ vars.CITY }}
        run: |
          python daily_bot.py

```

为什么要 concurrency？ 防止上一次任务还在跑，下一次又开始，造成重叠。

### （可选）本地快速验证

```
pip install -r requirements.txt
python daily_bot.py
```

确认 Telegram 能收到推送后再提交到仓库。

### 触发与查看日志

首次创建/修改工作流后：进入仓库 Actions 页面，选择 daily-bot，点 Run workflow 手动触发一次，观察日志是否成功。

之后会按照你设定的 cron（UTC）自动触发；GitHub 定时器可能有几分钟正常延迟。

###  常用 Cron 配方（UTC）

```
每天 06:30：30 6 * * *

每天 07:30 和 19:00：

schedule:
  - cron: "30 7 * * *"
  - cron: "0 19 * * *"


每周一 08:00（适合周报）：0 8 * * 1

每月 1 号 09:00（月报）：0 9 1 * *

每季度第 1 个月的 1 号 10:00（季报）：0 10 1 1,4,7,10 *

想严格跟随“伦敦本地 07:30”：

夏令时（BST=UTC+1）→ 用 06:30 UTC

冬令时（GMT=UTC+0）→ 用 07:30 UTC

做法：在 schedule 同时写两条（上面模板已注释）。
```

###  自定义新闻源（RSS）

```
直接在 Variables 里设置 NEWS_FEEDS，不改代码：

https://www.rte.ie/news/rss/news-headlines.xml, https://feeds.bbci.co.uk/news/world/rss.xml, https://feeds.reuters.com/reuters/businessNews


数量限制：

NEWS_PER_FEED：每个源取几条（默认 3）

NEWS_MAX_ITEMS：最终保留几条（默认 5）
```

###  故障排查（FAQ）

- 定时没触发？

记得 GitHub 使用 UTC；确认 cron 写法无误。

新建/修改工作流后，通常先手动运行一遍，再等下一次定时。

公共仓库负载高峰可能有几分钟延迟，属正常。

报错 ModuleNotFoundError: feedparser？

确认 requirements.txt 已包含 feedparser，并被安装。

- Telegram 收不到消息？

确认 TELEGRAM_BOT_TOKEN、TELEGRAM_CHAT_ID 正确无误；

检查日志里 sendMessage 步骤返回是否 200（别打印敏感信息）。

- OpenAI 配额不足/不用 OpenAI

你已经替换为 RSS 聚合方案，无需配 OPENAI_API_KEY；可把相关环境变量与依赖删除。

- 如何分离日/周/月/季/年任务？

建立多个工作流文件（如 daily.yml / weekly.yml / monthly.yml / …），分别写各自的 cron 与 run 命令。

### 安全与最佳实践

Secrets 永远不要写在代码/日志中；Actions 会对 ${{ secrets.* }} 打码，但你自己 print() 出来仍会暴露。

给 Job 最小权限（已在模板里设置 contents: read）。

PR 来自 fork 的代码默认拿不到 secrets（安全设计）。

配置可读参数尽量放 Variables，敏感的放 Secrets。

私有依赖或私有 PyPI：把凭证放 Secrets，用环境变量注入 PIP_INDEX_URL 安装。

### 目录结构示例

```
your-repo/
├─ daily_bot.py
├─ requirements.txt
└─ .github/
   └─ workflows/
      └─ daily-bot.yml
```


###  一次检查清单 ✅

- requirements.txt 包含 requests, python-dotenv, feedparser
- 仓库 Settings 里配置好 Secrets（Telegram/Weather 等）
- 仓库 Settings 里配置好 Variables（NEWS_FEEDS 等，或使用默认）
- .github/workflows/daily-bot.yml 已创建，cron 时间（UTC）正确
- 在 Actions 页面手动 Run workflow 一次，确认日志成功
- 等到下一个定时点，确认任务自动触发

## ❤️ Credits
This tool was built by me, with the help of ChatGPT ✨ in 1 hour.

Enjoy your custom morning Telegram briefing! ☕
"""
