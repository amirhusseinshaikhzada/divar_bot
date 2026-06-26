import os
from sqlalchemy import create_engine, Column, Integer, String, Float, BigInteger, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

# 1. تعریف پایه برای مدل‌ها (Base)
# تمام کلاس‌هایی که در آینده می‌سازی باید از این Base ارث‌بری کنند
Base = declarative_base()

# ---------------------------------------------------------
# 2. تعریف جداول (Models)
# من بر اساس نیاز ربات تحلیل قیمت تو، جداول اصلی را اینجا ساختم.
# اگر نام ستون‌ها یا جداول متفاوت است، آن‌ها را اینجا اصلاح کن.
# ---------------------------------------------------------

class User(Base):
    """جدول کاربران برای ذخیره اطلاعات تلگرام"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class PriceSearch(Base):
    """جدول برای ذخیره جستجوها و قیمت‌های استخراج شده از دیوار"""
    __tablename__ = 'price_searches'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(String, nullable=False)  # مثلا: "ایفون 13"
    extracted_price = Column(Float, nullable=True) # قیمتی که پیدا شد
    city = Column(String, nullable=True)        # شهر مورد نظر
    timestamp = Column(DateTime, server_default=func.now())

class Statistics(Base):
    """جدول برای ذخیره تحلیل‌های آماری (اگر بخواهی نمودارها را ذخیره کنی)"""
    __tablename__ = 'statistics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_name = Column(String, nullable=False)
    avg_price = Column(Float, nullable=False)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    recorded_at = Column(DateTime, server_default=func.now())

# ---------------------------------------------------------

class DatabaseManager:
    """مدیریت اتصال به دیتابیس و ساخت جداول"""
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        # خواندن URL دیتابیس از متغیرهای محیطی هاست (بسیار مهم برای امنیت)
        self.db_url = os.environ.get("DATABASE_URL")
        
        # اگر در حالت لوکال هستی و متغیر محیطی تعریف نشده، از این استفاده کن:
        if not self.db_url:
            # جایگزین کن با مشخصات دیتابیس محلی خودت
            self.db_url = "postgresql://postgres:TLxSGgtoFedqwUgdfIGUYvctHRhPfUzo@postgres-dv9t.railway.internal:5432/railway"

    def start_connection(self):
        """اتصال به دیتابیس و ساخت جداول در صورت عدم وجود"""
        try:
            print(f"🔄 Connecting to database...")
            self.engine = create_engine(self.db_url)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # --- بخش اصلی: ساخت جداول ---
            # این دستور چک می‌کند اگر جدولی وجود ندارد، آن را می‌سازد.
            print("🛠 Checking/Creating database tables...")
            Base.metadata.create_all(bind=self.engine)
            print("✅ Database tables are ready and synced!")
            
        except Exception as e:
            print(f"❌ Error: Could not connect to database or create tables: {e}")
            raise e

    def get_session(self):
        """ایجاد یک نشست (Session) برای انجام عملیات دیتابیس"""
        if self.SessionLocal:
            return self.SessionLocal()
        else:
            raise Exception("❌ Database is not connected! Call start_connection() first.")

# ایجاد یک نمونه واحد (Singleton) از کلاس برای استفاده در کل پروژه
db = DatabaseManager()
