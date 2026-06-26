import os
import re
import logging
import threading
import asyncio
import numpy as np
import httpx
import asyncpg
import matplotlib.pyplot as plt
from flask import Flask , jsonify
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import telebot
from telebot import types
from database import db



load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)




# --- CONFIGURATION ---


CITIES_DICT = {
    "تهران": "tehran",
    "کرج": "karaj",
    "مشهد": "mashhad",
    "اصفهان": "isfahan",
    "تبریز": "tabriz",
    "شیراز": "shiraz",
    "قزوین": "qazvin",
    "همدان": "hamadan",
    "رشت": "rasht",
    "همه شهرها": "all"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------
# DATABASE LAYER
# -----------------------
class Database:
    def __init__(self, url):
        self.url = url
        self.loop = asyncio.new_event_loop()
        self.pool = None

    def start_connection(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect())

    async def _connect(self):
        try:
            self.pool = await asyncpg.create_pool(self.url)
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS price_history (
                        id SERIAL PRIMARY KEY,
                        query TEXT NOT NULL,
                        avg_price BIGINT,
                        city TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                ''')
            logger.info("✅ Database Connected and Ready.")
        except Exception as e:
            logger.error(f"❌ Database Connection Error: {e}")

    def save_result(self, query, avg_price, city):
        asyncio.run_coroutine_threadsafe(
            self._save(query, avg_price, city), self.loop
        )

    async def _save(self, query, avg_price, city):
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO price_history(query, avg_price, city) VALUES($1, $2, $3)',
                query.lower(), avg_price, city
            )

    def get_history(self, query):
        return asyncio.run_coroutine_threadsafe(
            self._get_history(query), self.loop
        ).result()

    async def _get_history(self, query):
        async with self.pool.acquire() as conn:
            # دریافت ۱۰ رکورد آخر برای رسم نمودار بهتر
            rows = await conn.fetch(
                'SELECT avg_price, timestamp FROM price_history WHERE query = $1 ORDER BY timestamp ASC LIMIT 10',
                query.lower()
            )
            return [{"price": r['avg_price'], "time": r['timestamp']} for r in rows]

db = Database(DB_URL)

# -----------------------
# CHART GENERATOR
# -----------------------
def generate_price_chart(query, history_data):
    """ساخت نمودار قیمت با matplotlib"""
    if len(history_data) < 2:
        return None

    prices = [item['price'] for item in history_data]
    # تبدیل زمان‌ها به فرمت خوانا برای محور X
    times = [item['time'].strftime('%m-%d %H:%M') for item in history_data]

    plt.figure(figsize=(10, 5))
    plt.plot(times, prices, marker='o', linestyle='-', color='#1e88e5', linewidth=2, markersize=8)
    plt.fill_between(times, prices, color='#1e88e5', alpha=0.1)
    
    plt.title(f"Price Trend for: {query}", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Time (Month-Day Hour:Min)", fontsize=10)
    plt.ylabel("Price (Toman)", fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45)
    plt.tight_layout()

    file_path = f"chart_{query.replace(' ', '_')}.png"
    plt.savefig(file_path)
    plt.close()
    return file_path

# -----------------------
# SCRAPER ENGINE
# -----------------------
def extract_price(text):
    nums = re.findall(r"\d+", text.replace(",", ""))
    return int("".join(nums)) if nums else None

async def scrape_divar_async(query, city_slug):
    all_ads = []
    target_cities = CITIES_DICT.values() if city_slug == "all" else [city_slug]
    
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for city in target_cities:
            url = f"https://divar.ir/s/{city}?q={query}"
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                res = await client.get(url, headers=headers)
                soup = BeautifulSoup(res.text, "html.parser")
                posts = soup.select("div.kt-post-card")
                
                for p in posts:
                    title_tag = p.select_one(".kt-post-card__title")
                    price_tag = p.select_one(".kt-post-card__description")
                    link_tag = p.find("a")
                    
                    if title_tag and price_tag and link_tag:
                        price = extract_price(price_tag.text)
                        if price:
                            all_ads.append({
                                "title": title_tag.text,
                                "price": price,
                                "url": "https://divar.ir" + link_tag["href"],
                                "city": city
                            })
            except Exception as e:
                logger.error(f"Scrape Error: {e}")
    return all_ads

# -----------------------
# BOT HANDLERS
# -----------------------



user_settings = {}

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(name, callback_data=f"city_{slug}") for name, slug in CITIES_DICT.items()]
    markup.add(*buttons)
    
    bot.send_message(
        message.chat.id, 
        "👋 سلام! به ربات هوشمند قیمت دیوار خوش آمدید.\n\n"
        "اول **شهر مورد نظر** خود را انتخاب کنید، سپس نام کالا را بفرستید.",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("city_"))
def city_selection(call):
    city_slug = call.data.split("_")[1]
    city_name = next((k for k, v in CITIES_DICT.items() if v == city_slug), "نامشخص")
    user_settings[call.message.chat.id] = city_slug
    
    bot.answer_callback_query(call.id, f"✅ شهر انتخاب شد: {city_name}")
    bot.edit_message_text(
        f"✅ شهر روی **{city_name}** تنظیم شد.\n\n"
        "حالا نام کالایی که می‌خواهید قیمت آن را بدانید بفرستید.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    query = message.text.strip()
    
    if chat_id not in user_settings:
        bot.reply_to(message, "⚠️ لطفاً ابتدا از منوی پایین، یک شهر را انتخاب کنید.")
        return

    city_slug = user_settings[chat_id]
    status_msg = bot.reply_to(message, "🔍 در حال جستجو، تحلیل و رسم نمودار... لطفاً صبر کنید.")

    def run_search():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # ۱. اسکرپ کردن
            ads = loop.run_until_complete(scrape_divar_async(query, city_slug))
            
            if not ads:
                bot.edit_message_text("❌ هیچ آگهی مرتبطی پیدا نشد.", chat_id, status_msg.message_id)
                return

            # ۲. محاسبات آماری
            prices = [a['price'] for a in ads]
            arr = np.array(prices)
            q1, q3 = np.percentile(arr, [25, 75])
            iqr = q3 - q1
            clean_prices = [p for p in prices if (q1 - 1.5 * iqr) <= p <= (q3 + 1.5 * iqr)]
            if not clean_prices: clean_prices = prices
            
            avg_price = int(np.mean(clean_prices))
            
            # ۳. ذخیره در دیتابیس
            db.save_result(query, avg_price, city_slug)

            # ۴. دریافت تاریخچه برای نمودار و روند
            history = db.get_history(query)
            
            # ۵. رسم نمودار
            chart_path = generate_price_chart(query, history)

            # ۶. تشخیص روند
            trend_text = ""
            if len(history) >= 2:
                if history[-1]['price'] > history[-2]['price']:
                    trend_text = "📈 روند قیمت: **افزایشی**"
                elif history[-1]['price'] < history[-2]['price']:
                    trend_text = "📉 روند قیمت: **کاهشی**"
                else:
                    trend_text = "↔️ روند قیمت: **ثابت**"

            # ۷. ساخت متن گزارش
            response = (
                f"📦 **گزارش تحلیل: {query}**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 **میانگین قیمت:** `{avg_price:,}` تومان\n"
                f"📊 **تعداد آگهی:** `{len(ads)}` عدد\n"
                f"{trend_text}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
            )

            cheapest_ad = min(ads, key=lambda x: x['price'])
            if cheapest_ad['price'] < (avg_price * 0.85):
                response += "🔥 **فرصت طلایی خرید!**\nارزان‌ترین آگهی بسیار زیر میانگین است.\n\n"

            response += "✨ **ارزان‌ترین‌ها:**\n"
            sorted_ads = sorted(ads, key=lambda x: x['price'])[:3]
            for ad in sorted_ads:
                response += f"• {ad['title']}\n  `{ad['price']:,}`\n  [لینک آگهی]({ad['url']})\n\n"

            # ۸. ارسال نهایی (ابتدا نمودار، سپس متن)
            if chart_path and os.path.exists(chart_path):
                with open(chart_path, 'rb') as photo:
                    bot.send_photo(chat_id, photo, caption=response, parse_mode="Markdown", disable_web_page_preview=True)
                os.remove(chart_path) # پاکسازی فایل
            else:
                bot.edit_message_text(response, chat_id, status_msg.message_id, parse_mode="Markdown", disable_web_page_preview=True)

        except Exception as e:
            logger.exception(e)
            bot.edit_message_text("⚠️ خطایی در تحلیل رخ داد.", chat_id, status_msg.message_id)

    threading.Thread(target=run_search).start()

# -----------------------
# MAIN
# -----------------------
def main():
    db_thread = threading.Thread(target=db.start_connection)
    db_thread.start()
    print("🚀 Bot is running with Chart & DB Support...")
    bot.infinity_polling()

# -----------------------
# CORE FUNCTIONS
# -----------------------

def run_bot():
    """تابع برای اجرای ربات در یک ترد جداگانه"""
    try:
        logger.info("🤖 Starting Telegram Bot polling...")
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"❌ Bot polling error: {e}")

def start_all_services():
    """این تابع برای اجرای محلی (Local) استفاده می‌شود"""
    # ۱. اتصال به دیتابیس (در ترد اصلی برای اطمینان از صحت اتصال)
    try:
        db.start_connection()
        logger.info("✅ Database connection established.")
    except Exception as e:
        logger.error(f"❌ Failed to connect to DB: {e}")
        return 

    # ۲. استارت زدن ربات در یک ترد جداگانه
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # ۳. اجرای Flask در ترد اصلی
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Starting Flask server on port {port}...")
    app.run(host='0.0.0.0', port=port)

# -----------------------
# WEB ROUTES
# -----------------------

@app.route('/')
def index():
    return "<h1>Bot is Running!</h1><p>The Telegram Bot is active in the background.</p>"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "bot": "active"}), 200

# -----------------------
# MAIN ENTRY POINT
# -----------------------

if __name__ == "__main__":
    # حالت LOCAL: وقتی با دستور python bot.py اجرا می‌کنی
    start_all_services()

else:
    # حالت PRODUCTION: وقتی با دستور gunicorn فایل را اجرا می‌کنی
    # در این حالت Gunicorn مسئول اجرای Flask است. ما فقط دیتابیس و ربات را بالا می‌آوریم.
    try:
        db.start_connection()
        logger.info("✅ Database connection established (via Gunicorn).")
    except Exception as e:
        logger.error(f"❌ Database error during Gunicorn startup: {e}")

    # اجرای ربات در پس‌زمینه
    bot_thread = threading.Thread(target=run_bot, daemon=True)
