import asyncio
import logging
from aiogram import Bot, Dispatcher 
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv 

from config import BOT_TOKEN
from database import Database
from ai_service import GeminiService
import admin, start, prompt
from start import set_default_commands

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def on_startup(bot: Bot):
    await set_default_commands(bot)
    logger.info("🚀 Bot default komandalari o'rnatildi.")

async def main():
    load_dotenv() 
    
    
    db = Database()
    bot = Bot(token = BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage = storage)
        
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(prompt.router)
    
    dp.startup.register(on_startup)
    
    try:
        ai_service = GeminiService()
        
        await db.connect()
        logger.info("✅ Ma'lumotlar bazasiga ulanish o'rnatildi.")
        
        
        logger.info("🤖 Bot polling rejimida ish boshlamoqda...")
        await dp.start_polling(bot, db=db, ai_service=ai_service)
        
    except ValueError as e:
        logger.error(f"❌ Xatolik yuz berdi: {e}")
    
    finally:
        # 4. Tozalash (Cleanup)
        # Baza ulanishini yopishni unutmang (agar database.py da close metodi bo'lsa)
        # await db.close() 
        await bot.session.close()
        logger.info("💤 Bot to'xtatildi.")
        
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot manually stopped")
