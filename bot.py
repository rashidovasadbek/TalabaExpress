import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
import admin, start, prompt
from database import Database
from dotenv import load_dotenv 
from ai_service import GeminiService 
from start import set_default_commands
import logging

load_dotenv() 

db = Database()

async def on_startup(bot: Bot):

    await set_default_commands(bot) 
    

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
async def main():
    

    bot = Bot(token = BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage = storage)
    
    dp.startup.register(on_startup) 
    
    try:
        ai_service = GeminiService()
    except ValueError as e:
        print(f"❌ Xizmatni ishga tushirishda xato: {e}")
        return # Kalit topilmasa, botni ishga tushirmaymiz
    
    await db.connect()
    
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(prompt.router)
    
    dp.workflow_data['dp'] = dp
    
    print("🚀 Bot ishga tushdi...")
    try:
        await dp.start_polling(bot, db=db, ai_service=ai_service, drop_pending_updates=True)
    finally:
        await bot.session.close()
    
if __name__ == "__main__":
    asyncio.run(main())
