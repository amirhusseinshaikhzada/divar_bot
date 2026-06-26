# import os
# import re
# import logging
# import threading
# import asyncio
# import numpy as np
# import httpx
# import asyncpg
# import matplotlib.pyplot as plt
# from flask import Flask , jsonify
# from datetime import datetime
# from bs4 import BeautifulSoup
# from dotenv import load_dotenv
# import telebot
# from telebot import types
# from database import db



# load_dotenv()



# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)



# BOT_TOKEN = os.getenv("BOT_TOKEN")
# DB_URL = os.getenv("DATABASE_URL")

# app = Flask(__name__)
# bot = telebot.TeleBot(BOT_TOKEN)




# # --- CONFIGURATION ---


# CITIES_DICT = {
#     "تهران": "tehran",
#     "کرج": "karaj",
#     "مشهد": "mashhad",
#     "اصفهان": "isfahan",
#     "تبریز": "tabriz",
#     "شیراز": "shiraz",
#     "قزوین": "qazvin",
#     "همدان": "hamadan",
#     "رشت": "rasht",
#     "همه شهرها": "all"
# }



# user_settings = {}

# # -----------------------
# # DATABASE LAYER
# # -----------------------
# class Database:
#     def __init__(self, url):
#         self.url = url
#         self.loop = asyncio.new_event_loop()
#         self.pool = None

#     def start_connection(self):
#         asyncio.set_event_loop(self.loop)
#         self.loop.run_until_complete(self._connect())

#     async def _connect(self):
#         try:
#             self.pool = await asyncpg.create_pool(self.url)
#             async with self.pool.acquire() as conn:
#                 await conn.execute('''
#                     CREATE TABLE IF NOT EXISTS price_history (
#                         id SERIAL PRIMARY KEY,
#                         query TEXT NOT NULL,
#                         avg_price BIGINT,
#                         city TEXT,
#                         timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                     );
#                 ''')
#             logger.info("✅ Database Connected and Ready.")
#         except Exception as e:
#             logger.error(f"❌ Database Connection Error: {e}")

#     def save_result(self, query, avg_price, city):
#         asyncio.run_coroutine_threadsafe(
#             self._save(query, avg_price, city), self.loop
#         )

#     async def _save(self, query, avg_price, city):
#         async with self.pool.acquire() as conn:
#             await conn.execute(
#                 'INSERT INTO price_history(query, avg_price, city) VALUES($1, $2, $3)',
#                 query.lower(), avg_price, city
#             )

#     def get_history(self, query):
#         return asyncio.run_coroutine_threadsafe(
#             self._get_history(query), self.loop
#         ).result()

#     async def _get_history(self, query):
#         async with self.pool.acquire() as conn:
#             # دریافت ۱۰ رکورد آخر برای رسم نمودار بهتر
#             rows = await conn.fetch(
#                 'SELECT avg_price, timestamp FROM price_history WHERE query = $1 ORDER BY timestamp ASC LIMIT 10',
#                 query.lower()
#             )
#             return [{"price": r['avg_price'], "time": r['timestamp']} for r in rows]

# db = Database(DB_URL)

# # -----------------------
# # CHART GENERATOR
# # -----------------------
# def generate_price_chart(query, history_data):
#     """ساخت نمودار قیمت با matplotlib"""
#     if len(history_data) < 2:
#         return None

#     prices = [item['price'] for item in history_data]
#     # تبدیل زمان‌ها به فرمت خوانا برای محور X
#     times = [item['time'].strftime('%m-%d %H:%M') for item in history_data]

#     plt.figure(figsize=(10, 5))
#     plt.plot(times, prices, marker='o', linestyle='-', color='#1e88e5', linewidth=2, markersize=8)
#     plt.fill_between(times, prices, color='#1e88e5', alpha=0.1)
    
#     plt.title(f"Price Trend for: {query}", fontsize=14, fontweight='bold', pad=15)
#     plt.xlabel("Time (Month-Day Hour:Min)", fontsize=10)
#     plt.ylabel("Price (Toman)", fontsize=10)
#     plt.grid(True, linestyle='--', alpha=0.6)
#     plt.xticks(rotation=45)
#     plt.tight_layout()

#     file_path = f"chart_{query.replace(' ', '_')}.png"
#     plt.savefig(file_path)
#     plt.close()
#     return file_path

# # -----------------------
# # SCRAPER ENGINE
# # -----------------------
# def extract_price(text):
#     nums = re.findall(r"\d+", text.replace(",", ""))
#     return int("".join(nums)) if nums else None

# async def scrape_divar_async(query, city_slug):
#     all_ads = []
#     target_cities = CITIES_DICT.values() if city_slug == "all" else [city_slug]
    
#     async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
#         for city in target_cities:
#             url = f"https://divar.ir/s/{city}?q={query}"
#             headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36","Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7"}
#             try:
#                 res = await client.get(url, headers=headers)
#                 soup = BeautifulSoup(res.text, "html.parser")
#                 posts = soup.select("div.kt-post-card")
                
#                 for p in posts:
#                     title_tag = p.select_one(".kt-post-card__title")
#                     price_tag = p.select_one(".kt-post-card__description")
#                     link_tag = p.find("a")
                    
#                     if title_tag and price_tag and link_tag:
#                         price = extract_price(price_tag.text)
#                         if price:
#                             all_ads.append({
#                                 "title": title_tag.text,
#                                 "price": price,
#                                 "url": "https://divar.ir" + link_tag["href"],
#                                 "city": city
#                             })
#             except Exception as e:
#                 logger.error(f"Scrape Error: {e}")
#     return all_ads

# # -----------------------
# # BOT HANDLERS
# # -----------------------



# @bot.message_handler(commands=['start'])
# def start(message):
#     markup = types.InlineKeyboardMarkup(row_width=2)
    
#     # ساخت لیست دکمه‌ها
#     buttons = [types.InlineKeyboardButton(name, callback_data=f"city_{slug}") for name, slug in CITIES_DICT.items()]
    
#     # اصلاح اصلی: اضافه کردن علامت * قبل از buttons
#     markup.add(*buttons) 
    
#     bot.send_message(
#         message.chat.id, 
#         "👋 سلام! به ربات هوشمند قیمت دیوار خوش آمدید.\n\n"
#         "اول **شهر مورد نظر** خود را انتخاب کنید، سپس نام کالا را بفرستید.",
#         reply_markup=markup,
#         parse_mode="Markdown"
#     )

# @bot.callback_query_handler(func=lambda call: call.data.startswith("city_"))
# def city_selection(call):
#     city_slug = call.data.split("_")[1]
#     city_name = next((k for k, v in CITIES_DICT.items() if v == city_slug), "نامشخص")
#     user_settings[call.message.chat.id] = city_slug
    
#     bot.answer_callback_query(call.id, f"✅ شهر انتخاب شد: {city_name}")
#     bot.edit_message_text(
#         f"✅ شهر روی **{city_name}** تنظیم شد.\n\n"
#         "حالا نام کالایی که می‌خواهید قیمت آن را بدانید بفرستید.",
#         call.message.chat.id,
#         call.message.message_id,
#         parse_mode="Markdown"
#     )

# @bot.message_handler(func=lambda message: True)
# def handle_text(message):
#     chat_id = message.chat.id
#     query = message.text.strip()
    
#     if chat_id not in user_settings:
#         bot.reply_to(message, "⚠️ لطفاً ابتدا از منوی پایین، یک شهر را انتخاب کنید.")
#         return

#     city_slug = user_settings[chat_id]
#     # ارسال پیام وضعیت اولیه
#     status_msg = bot.reply_to(message, "🔍 در حال جستجو، تحلیل و رسم نمودار... لطفاً صبر کنید.")

#     def run_search():
#         """
#         این تابع در یک ترد (Thread) جداگانه اجرا می‌شود تا باعث بلاک شدن ربات نشود.
#         """
#         try:
#             # ۱. اسکرپ کردن (استفاده از asyncio.run برای اجرای تابع async در ترد معمولی)
#             # این روش امن‌ترین راه برای اجرای یک تابع async در یک Thread معمولی است.
#             ads = asyncio.run(scrape_divar_async(query, city_slug))
            
#             if not ads:
#                 bot.edit_message_text("❌ هیچ آگهی مرتبطی پیدا نشد.", chat_id, status_msg.message_id)
#                 return

#             # ۲. محاسبات آماری (پاکسازی داده‌های پرت با IQR)
#             prices = [a['price'] for a in ads]
#             arr = np.array(prices)
#             q1, q3 = np.percentile(arr, [25, 75])
#             iqr = q3 - q1
            
#             # حذف داده‌های پرت
#             lower_bound = q1 - 1.5 * iqr
#             upper_bound = q3 + 1.5 * iqr
#             clean_prices = [p for p in prices if lower_bound <= p <= upper_bound]
            
#             # اگر به هر دلیلی بعد از حذف داده‌ها لیست خالی شد، از همان قیمت‌های اصلی استفاده کن
#             if not clean_prices: 
#                 clean_prices = prices
            
#             avg_price = int(np.mean(clean_prices))
            
#             # ۳. ذخیره در دیتابیس
#             db.save_result(query, avg_price, city_slug)

#             # ۴. دریافت تاریخچه برای نمودار و روند
#             history = db.get_history(query)
            
#             # ۵. رسم نمودار
#             chart_path = generate_price_chart(query, history)

#             # ۶. تشخیص روند
#             trend_text = ""
#             if len(history) >= 2:
#                 if history[-1]['price'] > history[-2]['price']:
#                     trend_text = "📈 روند قیمت: **افزایشی**"
#                 elif history[-1]['price'] < history[-2]['price']:
#                     trend_text = "📉 روند قیمت: **کاهشی**"
#                 else:
#                     trend_text = "↔️ روند قیمت: **ثابت**"

#             # ۷. ساخت متن گزارش
#             response = (
#                 f"📦 **گزارش تحلیل: {query}**\n"
#                 f"━━━━━━━━━━━━━━━━━━\n"
#                 f"💰 **میانگین قیمت:** `{avg_price:,}` تومان\n"
#                 f"📊 **تعداد آگهی:** `{len(ads)}` عدد\n"
#                 f"{trend_text}\n"
#                 f"━━━━━━━━━━━━━━━━━━\n"
#             )

#             # بررسی فرصت طلایی (اگر ارزان‌ترین آگهی کمتر از ۸۵٪ میانگین باشد)
#             cheapest_ad = min(ads, key=lambda x: x['price'])
#             if cheapest_ad['price'] < (avg_price * 0.85):
#                 response += "🔥 **فرصت طلایی خرید!**\nارزان‌ترین آگهی بسیار زیر میانگین است.\n\n"

#             response += "✨ **ارزان‌ترین‌ها:**\n"
#             sorted_ads = sorted(ads, key=lambda x: x['price'])[:3]
#             for ad in sorted_ads:
#                 response += f"• {ad['title']}\n  `{ad['price']:,}`\n  [لینک آگهی]({ad['url']})\n\n"

#             # ۸. ارسال نهایی
#             # ابتدا پیام "در حال جستجو" را پاک می‌کنیم تا پیام جدید جایگزین شود
#             bot.delete_message(chat_id, status_msg.message_id)

#             if chart_path and os.path.exists(chart_path):
#                 with open(chart_path, 'rb') as photo:
#                     bot.send_photo(
#                         chat_id, 
#                         photo, 
#                         caption=response, 
#                         parse_mode="Markdown", 
#                         disable_web_page_preview=True
#                     )
#                 # پاکسازی فایل نمودار پس از ارسال موفق
#                 try:
#                     os.remove(chart_path)
#                 except Exception as e:
#                     logger.error(f"Error deleting chart: {e}")
#             else:
#                 # اگر نموداری ساخته نشد، فقط متن را بفرست
#                 bot.send_message(chat_id, response, parse_mode="Markdown", disable_web_page_preview=True)

#         except Exception as e:
#             logger.exception(f"Error in run_search: {e}")
#             # در صورت بروز خطا، به کاربر اطلاع داده شود
#             try:
#                 bot.send_message(chat_id, "⚠️ متأسفانه خطایی در فرآیند تحلیل رخ داد. لطفاً دوباره تلاش کنید.")
#             except:
#                 pass

#     # اجرای تابع در یک ترد جداگانه برای جلوگیری از قفل شدن ربات
#     threading.Thread(target=run_search, daemon=True).start()

# # -----------------------
# # MAIN
# # -----------------------
# def main():
#     db_thread = threading.Thread(target=db.start_connection)
#     db_thread.start()
#     print("🚀 Bot is running with Chart & DB Support...")
#     bot.infinity_polling()

# # -----------------------
# # CORE FUNCTIONS
# # -----------------------

# def run_bot():
#     """تابع برای اجرای ربات در یک ترد جداگانه با مدیریت خطا و حذف وب‌هوک"""
#     try:
#         # ۱. حذف وب‌هوک قدیمی برای جلوگیری از خطای 409 Conflict
#         logger.info("🧹 Cleaning up any existing webhooks...")
#         bot.remove_webhook()
        
#         # ۲. اطمینان از اتصال دیتابیس در همان ترد ربات
#         logger.info("🔌 Establishing database connection in bot thread...")
#         # db.start_connection() # این خط را بر اساس کد اصلی خودتان فعال کنید
        
#         # ۳. شروع عملیات Polling
#         logger.info("🤖 Starting Telegram Bot polling...")
#         bot.infinity_polling()
#     except Exception as e:
#         logger.error(f"❌ Bot polling error: {e}")

# def start_all_services():
#     """این تابع برای اجرای محلی (Local) استفاده می‌شود"""
#     # ۱. اتصال به دیتابیس در ترد اصلی
#     try:
#         # db.start_connection() 
#         logger.info("✅ Database connection established.")
#     except Exception as e:
#         logger.error(f"❌ Failed to connect to DB: {e}")
#         return 

#     # ۲. استارت زدن ربات در یک ترد جداگانه
#     bot_thread = threading.Thread(target=run_bot, daemon=True)
#     bot_thread.start()
    
#     # ۳. اجرای Flask در ترد اصلی
#     port = int(os.environ.get("PORT", 5000))
#     logger.info(f"🌐 Starting Flask server on port {port}...")
#     app.run(host='0.0.0.0', port=port)

# # -----------------------
# # WEB ROUTES
# # -----------------------

# @app.route('/')
# def index():
#     return "<h1>Bot is Running!</h1><p>The Telegram Bot is active in the background.</p>"

# @app.route('/health')
# def health_check():
#     return jsonify({"status": "healthy", "bot": "active"}), 200

# # -----------------------
# # MAIN ENTRY POINT
# # -----------------------

# if __name__ == "__main__":
#     # حالت LOCAL: وقتی با دستور python bot.py اجرا می‌کنی
#     start_all_services()

# else:
#     # حالت PRODUCTION: وقتی با دستور gunicorn فایل را اجرا می‌کنی
#     # در این حالت Gunicorn مسئول اجرای Flask است.
    
#     # ۱. تلاش برای اتصال به دیتابیس در ترد اصلی (اگر لازم است)
#     try:
#         # db.start_connection()
#         logger.info("✅ Database connection established (via Gunicorn).")
#     except Exception as e:
#         logger.error(f"❌ Database error during Gunicorn startup: {e}")

#     # ۲. اجرای ربات در پس‌زمینه (با اصلاح خط اصلی)
#     bot_thread = threading.Thread(target=run_bot, daemon=True)
#     bot_thread.start() # <--- این خط اصلاح شد تا ربات واقعاً اجرا شود
#     logger.info("🚀 Bot thread has been dispatched in background.")







































import os
import re
import logging
import asyncio
import threading
import datetime
import dotenv
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import httpx
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from telebot import telebot, types
from sqlalchemy import create_engine # استفاده از SQLAlchemy برای مدیریت بهتر PostgreSQL

# بارگذاری متغیرهای محیطی
dotenv.load_dotenv()

# --- تنظیمات و پیکربندی ---
TOKEN = os.getenv("BOT_TOKEN")
# DB_URL باید شامل مشخصات PostgreSQL باشد، مثلا:
# postgresql://username:password@localhost:5432/dbname
DB_URL = os.getenv("DATABASE_URL") 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# تنظیمات Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- کلاس مدیریت دیتابیس (اصلاح شده برای PostgreSQL) ---
class DatabaseManager:
    def __init__(self, db_url):
        self.db_url = db_url
        self.lock = threading.Lock()
        self._create_table()

    def _get_engine(self):
        # استفاده از SQLAlchemy برای مدیریت اتصالات PostgreSQL
        return create_engine(self.db_url)

    def _create_table(self):
        with self.lock:
            engine = self._get_engine()
            # در PostgreSQL از SERIAL برای ID و BIGINT برای قیمت‌های بزرگ استفاده می‌کنیم
            query = '''CREATE TABLE IF NOT EXISTS ads (
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMP,
                            city TEXT,
                            category TEXT,
                            title TEXT,
                            price BIGINT,
                            url TEXT
                        )'''
            with engine.connect() as conn:
                conn.execute(query)
                # در SQLAlchemy برای اعمال تغییرات در برخی نسخه‌ها نیاز به commit است
                # اما برای دستورات DDL مثل CREATE TABLE معمولاً خودکار اعمال می‌شود

    def save_ad(self, city, category, title, price, url):
        with self.lock:
            engine = self._get_engine()
            query = "INSERT INTO ads (timestamp, city, category, title, price, url) VALUES (%s, %s, %s, %s, %s, %s)"
            values = (datetime.datetime.now(), city, category, title, price, url)
            with engine.connect() as conn:
                conn.execute(query, values)
                # برای PostgreSQL در SQLAlchemy حتما باید commit شود
                from sqlalchemy import text
                conn.execute(text("COMMIT"))

    def get_history(self, city, category):
        with self.lock:
            engine = self._get_engine()
            query = "SELECT timestamp, price FROM ads WHERE city=%s AND category=%s"
            # استفاده از pandas برای خواندن مستقیم از SQL
            df = pd.read_sql(query, engine, params=(city, category))
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
            return df

# مقداردهی دیتابیس
db = DatabaseManager(DB_URL)

# --- کلاس اسکرپر پیشرفته ---
class DivarScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    async def scrape_divar_async(self, city, category, query):
        url = f"https://divar.ir/s/{city}/{category}?q={query}"
        async with httpx.AsyncClient(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.error(f"❌ Divar Error: {response.status_code}")
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                posts = soup.select("article, div.kt-post-card, div[class*='post-card']")
                
                ads = []
                for post in posts:
                    try:
                        title_el = post.select_one("div.kt-post-card__title, div[class*='title'], h2")
                        title = title_el.get_text(strip=True) if title_el else "بدون عنوان"

                        price_el = post.select_one("div.kt-post-card__description, div[class*='price'], span[class*='price']")
                        price_text = price_el.get_text(strip=True) if price_el else ""
                        price = self.extract_price(price_text)
                        
                        link_el = post.find('a', href=True)
                        link = "https://divar.ir" + link_el['href'] if link_el else ""

                        if price and title:
                            ads.append({'title': title, 'price': price, 'url': link})
                    except:
                        continue
                return ads
            except Exception as e:
                logger.error(f"❌ Scraper Exception: {e}")
                return []

    def extract_price(self, text):
        clean_text = text.replace(",", "").replace("تومان", "").replace("ریال", "").replace(" ", "")
        nums = re.findall(r"\d+", clean_text)
        return int("".join(nums)) if nums else None

scraper = DivarScraper()
user_settings = {}

# --- منطق تحلیل آماری و نمودار ---
def generate_analysis_report(city, category, current_ads):
    df_history = db.get_history(city, category)
    
    # ذخیره آگهی‌های جدید در دیتابیس برای تحلیل آینده
    for ad in current_ads:
        db.save_ad(city, category, ad['title'], ad['price'], ad['url'])
    
    # بازخوانی دوباره برای شامل شدن داده‌های جدید
    df = db.get_history(city, category)
    
    if len(df) < 3:
        return "📊 داده‌های کافی برای تحلیل روند قیمت در دیتابیس وجود ندارد. جستجوهای بیشتری انجام دهید.", None

    # حذف داده‌های پرت با IQR
    Q1 = df['price'].quantile(0.25)
    Q3 = df['price'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    df_clean = df[(df['price'] >= lower_bound) & (df['price'] <= upper_bound)].copy()

    if df_clean.empty:
        return "⚠️ خطای آماری در پردازش قیمت‌ها.", None

    avg_price = df_clean['price'].mean()
    last_price = current_ads[0]['price']
    trend = "📈 صعودی" if last_price > avg_price else "📉 نزولی"
    
    # رسم نمودار
    plt.figure(figsize=(10, 5))
    plt.plot(df_clean['timestamp'], df_clean['price'], marker='o', linestyle='-', color='blue')
    plt.axhline(y=avg_price, color='r', linestyle='--', label=f'Average: {int(avg_price):,}')
    plt.title(f"Price Trend for {category} in {city}")
    plt.xlabel("Date")
    plt.ylabel("Price (Toman)")
    plt.legend()
    plt.grid(True)
    
    plot_filename = f"chart_{city}_{category}.png"
    plt.savefig(plot_filename)
    plt.close()
    
    report = (f"📊 **تحلیل بازار:**\n\n"
              f"💰 میانگین قیمت: {int(avg_price):,} تومان\n"
              f"🔎 آخرین قیمت یافت شده: {last_price:,} تومان\n"
              f"📈 وضعیت بازار: {trend}\n"
              f"ℹ️ تحلیل بر اساس {len(df_clean)} داده‌ی ثبت شده.")
    
    return report, plot_filename

# --- هندلرهای تلگرام ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    cities = ["تهران", "مشهد", "اصفهان", "کرج", "تبریز", "شیراز", "کرمان", "لاهیجان"]
    markup.add(*cities)
    bot.send_message(message.chat.id, "👋 خوش آمدید! لطفاً شهر خود را انتخاب کنید:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["تهران", "مشهد", "اصفهان", "کرج", "تبریز", "شیراز", "کرمان", "لاهیجان"])
def set_city(message):
    user_settings[message.chat.id] = {'city': message.text}
    bot.send_message(message.chat.id, f"✅ شهر {message.text} انتخاب شد. حالا کالا مورد نظر را بنویسید (مثلاً: دوچرخه):")

@bot.message_handler(func=lambda message: True)
def handle_search(message):
    chat_id = message.chat.id
    query = message.text

    if chat_id not in user_settings:
        bot.send_message(chat_id, "⚠️ ابتدا شهر خود را انتخاب کنید.")
        return

    status_msg = bot.send_message(chat_id, "🔍 در حال جستجو و تحلیل بازار... لطفاً صبر کنید.")

    def task():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        city = user_settings[chat_id]['city']
        category = "all"
        
        ads = loop.run_until_complete(scraper.scrape_divar_async(city, category, query))
        
        if not ads:
            bot.edit_message_text("❌ هیچ آگهی مرتبطی پیدا نشد. کلمه دیگری امتحان کنید.", chat_id, status_msg.message_id)
            return

        report_text, plot_file = generate_analysis_report(city, category, ads)
        
        response = f"✅ {len(ads)} آگهی جدید پیدا شد:\n\n"
        for i, ad in enumerate(ads[:5]):
            response += f"🔹 {ad['title']} | {ad['price']:,} تومان\n"
        
        response += f"\n{report_text}"
        
        try:
            if plot_file and os.path.exists(plot_file):
                with open(plot_file, 'rb') as photo:
                    bot.send_photo(chat_id, photo, caption=None)
                os.remove(plot_file)
            
            bot.edit_message_text(response, chat_id, status_msg.message_id, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error sending results: {e}")
            bot.send_message(chat_id, "❌ خطایی در ارسال نتایج رخ داد.")

    threading.Thread(target=task).start()

# --- مدیریت اجرا ---

def run_bot_service():
    try:
        bot.remove_webhook()
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"❌ Bot Error: {e}")

@app.route('/')
def index():
    return jsonify({"status": "online"}), 200

if __name__ == "__main__":
    logger.info("🚀 Starting Bot Service...")
    threading.Thread(target=run_bot_service, daemon=True).start()
    # پورت از محیط سیستم یا پیش‌فرض ۵۰۰۰ خوانده می‌شود (نه از .env)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
