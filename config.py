import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY = os.getenv("PROXY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PAYMENT_CHANNEL_ID = int(os.getenv("PAYMENT_CHANNEL_ID"))

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN .env faylda topilmadi!")