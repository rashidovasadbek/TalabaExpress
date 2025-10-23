import asyncpg
from config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER
from typing import Optional
from typing import Dict
from typing import Optional
import logging
import traceback

class Database:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None
        
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        print("✅ Database pool yaratildi")
        
    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            print("database yopildi")
    
    async def get_channels(self) -> list[str]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT username FROM public.channels ORDER BY id')
            return[r["username"]for r in rows]
        
    async def add_channel(self, username: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO channels(username) VALUES($1) ON CONFLICT DO NOTHING", username
            )
            
    async def remove_channel(self, username: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE  FROM channels WHERE username=$1", username
            )
    
    async def get_all_settings(self) -> list[dict]:
        """Barcha mavjud promptlar (kalit, qiymat, tavsif) ro'yxatini oladi."""
        async with self.pool.acquire() as conn:
        # SELECT qismida ustun nomlari aniq berilgan
            rows = await conn.fetch("SELECT key, value, description FROM settings ORDER BY key")
        
        # Xatoga sabab bo'lgan qatorni o'chirib tashlaymiz va xavfsiz lug'at yaratish usulidan foydalanamiz:
        return [
            {
                'key': r['key'], 
                'value': r['value'], 
                # 'description' ustuni ba'zan NULL bo'lishi mumkin, shuning uchun xavfsiz olinadi.
                'description': r['description']
            } 
            for r in rows
        ]
        
    async def update_setting(self, key: str, new_value: str, description: str = None):
        """Sozlama (prompt) qiymatini yangilaydi/yaratadi."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3) "
                "ON CONFLICT (key) DO UPDATE SET value = $2, description = COALESCE($3, settings.description)", 
                key, new_value, description
            )

    async def get_user(self, user_id: int):
        """
        Telegram ID bo'yicha foydalanuvchi ma'lumotlarini bazadan oladi.
        :return: Foydalanuvchi obyekti (Masalan, dict/Record), yoki None.
        """

        sql = """
        SELECT * FROM users WHERE telegram_id = $1
        """
        # pool.fetchrow faqat bir qatorni qaytaradi
        user = await self.pool.fetchrow(sql, user_id)
        return user
    
    async def get_or_create_user(self, user_id: int, username: str | None, referrer_id: int | None = None) -> tuple[bool, bool]:
        """
        Foydalanuvchini bazadan oladi. Agar mavjud bo'lmasa, uni yaratadi.
        Referral tizimi uchun maxsus mo'ljallangan.
        
        :return: (Muvaffaqiyatli bo'lsa True/False, Yangi foydalanuvchi bo'lsa True/False)
        """
    
        # Avval mavjudligini tekshirish
        user = await self.get_user(user_id)
        is_new_user = user is None
        
        # 10000 so'm starter balansni faqat yangi foydalanuvchiga beramiz
        INITIAL_BALANCE = 10000.00 if is_new_user else 0.00
        
        safe_username = username if username else ''
        
        # Eslatma: SQL da telegram_id PRIMARY KEY yoki UNIQUE deb belgilangan
        sql = """
        INSERT INTO users (telegram_id, username, balance, referrer_id) 
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (telegram_id) DO NOTHING;
        """
        
        try:
            if is_new_user:
            
                await self.pool.execute(sql, user_id, safe_username, INITIAL_BALANCE, referrer_id)
                
            return (True, is_new_user)
            
        except Exception as e:
            print(f"!!! CRITICAL DB ERROR: Failed to insert user {user_id}: {e}")
            # ✅ Xato bo'lganda ham kutilgan formatda qaytarish
            return (False, False)
    
    async def get_user_balance(self, user_id: int) -> float | None:
        """
        Foydalanuvchining joriy balansini float sifatida oladi.
        Agar foydalanuvchi topilmasa, None qaytaradi.
        """
        sql = "SELECT balance FROM \"users\" WHERE telegram_id = $1"
        
        try:
            # self.pool.fetchval faqat birinchi ustun qiymatini qaytaradi
            balance = await self.pool.fetchval(sql, user_id)
            
            # Agar baza None qaytarsa (foydalanuvchi yo'q), None uzatamiz.
            # Agar Decimal qaytarsa, uni float ga o'tkazamiz.
            if balance is not None:
                return float(balance)
            return None
            
        except Exception as e:
            print(f"Error getting user balance for {user_id}: {e}")
            return None
    
    async def update_balance_and_log_transaction(self, user_id: int, amount: float, tr_type: str) -> bool:
        """
        Balansni yangilash va tranzaksiya yozuvini yozish (Atomar amaliyot).
        
        :param amount: Balansga qo'shish uchun musbat, ayirish uchun manfiy bo'lishi kerak.
        :param tr_type: 'generation', 'rollback', 'admin_refund', 'payment'
        :return: Muvaffaqiyatli bo'lsa True, aks holda False.
        """
        try:
            async with self.pool.acquire() as conn:
                # ASOSIY TRANZAKSIYA BLOKI - Atomarlikni ta'minlash
                async with conn.transaction():
                    try:
                        # 1. Balansni yangilash
                        # Amaliyotni soddalashtirish uchun amount shu yerda qo'shiladi/ayriladi
                        update_sql = "UPDATE users SET balance = balance + $1 WHERE telegram_id = $2 RETURNING balance"
                        new_balance = await conn.fetchval(update_sql, amount, user_id)
                        
                        if new_balance is None:
                            logging.error(f"DB ERROR: User {user_id} not found during balance update.")
                            # Foydalanuvchi topilmasa
                            return False

                        # 2. Tranzaksiya yozuvini kiritish (Audit uchun)
                        log_sql = """
                        INSERT INTO transactions (user_id, amount, type) 
                        VALUES ($1, $2, $3)
                        """
                        await conn.execute(log_sql, user_id, amount, tr_type)
                        
                        return True
                    except Exception as e:
                        # TUZATISH 2: Xatolik yuz berganda to'liq loglama
                        logging.error("--------------------- DB TRANZAKSIYA XATOSI ---------------------")
                        logging.error(f"User ID: {user_id}, Turi: {tr_type}, Summa: {amount}")
                        logging.error(f"Xato matni: {e}")
                        logging.error(traceback.format_exc()) # <--- Eng muhimi!
                        logging.error("---------------------------------------------------------------")
                        return False
        except Exception as e:
            # Ulanish, Pool yoki Tranzaksiyaning istalgan joyida yuz bergan xato
            logging.error("--------------------- GLOBAL DB XATOSI (TO'LIQ) ---------------------")
            logging.error(f"User ID: {user_id}, Turi: {tr_type}, Summa: {amount}")
            logging.error(f"Xato turi: {type(e).__name__}")
            logging.error(f"Xato matni: {e}")
            logging.error(traceback.format_exc())
            logging.error("--------------------------------------------------------------------")
            return False
    
    async def debit_balance(self, user_id: int, amount: float, tr_type: str) -> bool:
        """Balansdan pul ayiradi (Debit). amount musbatda kiritilishi kerak."""
        
        if amount <= 0:
            return False # Manfiy yoki nol qiymatda ayirish mumkin emas
            
        # Pul yechish uchun miqdor manfiy qilinadi.
        try:
        # update_balance_and_log_transaction endi xato bo'lsa False emas, Exception otadi
            return await self.update_balance_and_log_transaction(user_id, -amount, tr_type)
        
        except Exception as e:
            # XATO BU YERDA USHLANADI VA LOGLANADI!
            logging.error("--------------------- DEBIT BILAN ALOQALI XATO ---------------------")
            logging.error(f"User ID: {user_id}, Summa: {amount}")
            logging.error(f"Xato turi: {type(e).__name__}")
            logging.error(f"Xato matni: {e}")
            logging.error(traceback.format_exc()) # <--- Traceback to'liq yozilishi shart
            logging.error("----------------------------------------------------------------------")
            return False

    async def credit_balance(self, user_id: int, amount: float, reason: str) -> bool:
        """Foydalanuvchi balansini oshiradi. Yangi update_balance_and_log_transaction orqali"""
        
        if amount <= 0:
            return False 
            
        # Pul qo'shish uchun: amount musbatda
        return await self.update_balance_and_log_transaction(user_id, amount, reason)
    
    async def create_ai_work_record(self,user_id: int, work_data: Dict, cost: float) -> Optional[int]:
    
        topic = work_data.get('topic', 'Noma\'lum mavzu')
        work_type = work_data.get('raw_work_type', 'refarat')
        page_range = work_data.get('page_count_raw', '15-20') 

        sql = """
        INSERT INTO ai_works (user_id, topic, work_type, page_range, cost, is_completed)
        VALUES ($1, $2, $3, $4, $5, FALSE) 
        RETURNING id;
        """
        try:
            # self.pool ishlatildi va 5 ta parametr uzatildi
            work_id = await self.pool.fetchval(
                sql, user_id, topic, work_type, page_range, cost 
            )
            return work_id
        except Exception as e:
            print(f"Error creating AI work record: {e}")
            return None
        
    async def update_ai_work_status(self,work_id: int, is_completed: bool, debit_transaction_id: Optional[int] = None) -> bool:
        sql = """
        UPDATE ai_works SET is_completed = $1, debit_transaction_id = $2
        WHERE id = $3;
        """
        try:
            # ✅ self.pool dan ulanish olib, unda execute qilamiz
            async with self.pool.acquire() as conn:
                result = await conn.execute(sql, is_completed, debit_transaction_id, work_id)
                return result == 'UPDATE 1' # Yangilanish muvaffaqiyatli bo'lganini tekshirish
        except Exception as e:
            print(f"Error updating AI work status: {e}")
            return False

    async def add_balance(self, user_id: int, amount: float) -> bool:
        """
        Foydalanuvchi balansiga summa qo'shadi (refund yoki to'ldirish).
        """
        sql = """
        UPDATE users SET balance = balance + $1 WHERE telegram_id = $2
        """
        try:
            await self.pool.execute(sql, amount, user_id)
            return True
        except Exception as e:
            print(f"Balansga pul qo'shishda xato: {e}")
            return False