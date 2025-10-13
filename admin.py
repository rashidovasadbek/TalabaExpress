from aiogram import Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_ID
from aiogram import Router, Bot
from aiogram.filters import Command
from database import Database
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message 
from aiogram.fsm.storage.base import StorageKey


class AdminAction(StatesGroup):
    
    waiting_for_amount = State() 
    waiting_for_refund_amount = State()
    waiting_for_refund_user_id = State()

router =  Router()

admin_action = {}

def build_admin_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👤 Foydalanuvchilar")],
            [KeyboardButton(text="💳 To‘lovlar"), KeyboardButton(text="📢 Xabar yuborish")],
            [KeyboardButton(text="🔄 Pul qaytarish (Refund)"), KeyboardButton(text="➕ Kanal qo'shish")], 
            [KeyboardButton(text="➖ Kanal o‘chirish"), KeyboardButton(text="📋 Kanallar ro‘yxati")]
        ],
        resize_keyboard=True
    )
    return kb

@router.message(F.text == "🔄 Pul qaytarish (Refund)")
async def start_refund(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return # Admin bo'lmasa ishlamasin
    
    await message.answer("➡️ **Pul qaytariladigan foydalanuvchining Telegram ID'sini kiriting:**", parse_mode= "Markdown")
    await state.set_state(AdminAction.waiting_for_refund_user_id)


@router.message(AdminAction.waiting_for_refund_user_id)
async def receive_refund_user_id(message: Message, state: FSMContext):
    user_id_str = message.text.strip()
    
    try:
        refund_user_id = int(user_id_str)
    except ValueError:
        await message.answer("❌ **Noto'g'ri format!** Iltimos, faqat raqamlardan iborat Telegram ID'sini kiriting.")
        return

    # ID ni FSM xotirasiga saqlash
    await state.update_data(target_user_id=refund_user_id)
    
    await message.answer(
        f"✅ ID: `{refund_user_id}` qabul qilindi.\n\n"
        "💰 **Endi qaytariladigan summani so'mda kiriting (Masalan: 5000):**",
        parse_mode="Markdown"
    )
    await state.set_state(AdminAction.waiting_for_refund_amount)

@router.message(AdminAction.waiting_for_refund_amount)
async def process_refund_amount(message: Message, state: FSMContext, bot: Bot, db: Database):
    amount_str = message.text.strip()
    
    try:
        refund_amount = float(amount_str)
        if refund_amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ **Noto'g'ri summa!** Iltimos, musbat raqam kiriting (Masalan: 5000.00).")
        return

    # FSM xotirasidan ID ni olish
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    
    # ❌ Refund (balansga qo'shish)
    success = await db.add_balance(target_user_id, refund_amount)
    
    await state.clear() # FSM holatini tozalash

    if success:
        # 4. Foydalanuvchini xabardor qilish
        try:
            await bot.send_message(
                target_user_id, 
                f"💸 **Hisobingizga mablag' qaytarildi!**\n\n"
                f"Sizning hisobingizga **{refund_amount} so'm** qaytarildi. Bu ehtimol, tayyorlangan hujjatdagi texnik xatolik bilan bog'liq.\n"
                f"Uzr so'raymiz! 😊",
                parse_mode="Markdown"
            )
            confirmation_text = "✅ **Pul muvaffaqiyatli qaytarildi!** Foydalanuvchi xabardor qilindi."
        except Exception:
            confirmation_text = "⚠️ **Pul qaytarildi**, ammo foydalanuvchiga xabar yuborilmadi (Bot bloklagan bo'lishi mumkin)."
            
        await message.answer(confirmation_text, parse_mode="Markdown")
        
    else:
        await message.answer("❌ **Xatolik!** Pulni qaytarishda yoki foydalanuvchi bazada topishda xatolik yuz berdi.")

@router.callback_query(F.data.startswith(("admin_accept", "admin_reject")))
async def process_receipt_action(callback: CallbackQuery, state: FSMContext, db: Database):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Bu harakatni faqat adminlar amalga oshirishi mumkin!", show_alert=True)
        return

    action, user_id_str = callback.data.split(':')
    target_user_id = int(user_id_str)

    if action == "admin_accept":
        
        admin_user_id = callback.from_user.id
        
        admin_pm_key = StorageKey(
            bot_id=callback.bot.id, 
            chat_id=admin_user_id,   # ✅ CHAT ID = ADMIN ID
            user_id=admin_user_id    # ✅ USER ID = ADMIN ID
        )
        
        admin_pm_state = FSMContext(state.storage, admin_pm_key)
        
        # 1. Adminning shaxsiy chatiga FSM holatini o'rnatish
        await admin_pm_state.set_state(AdminAction.waiting_for_amount)
        
        # 2. Balansni olish
        user_balance = await db.get_user_balance(target_user_id)
        current_balance = user_balance if user_balance is not None else 0.00
        
        # 3. Ma'lumotlarni Adminning PM FSM xotirasiga saqlash
        await admin_pm_state.update_data(
            target_user_id=target_user_id,
            receipt_message_id=callback.message.message_id,
            receipt_chat_id=callback.message.chat.id, # Asl chek turgan guruh ID
            current_balance=current_balance
    
        )
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=f"💰 **Balansga qo'shiladigan summani kiriting** (ID: `{target_user_id}`).\nMasalan: 4000",
            parse_mode='Markdown'
        )
        await callback.answer("Summani kiritishni boshlang.", show_alert=False)
        
        try:
            await callback.message.edit_caption(
                caption=callback.message.caption + "\n\n**🟡 KUTMOQDA:** Admin summa kiritmoqda...",
                parse_mode='Markdown',
                reply_markup=None 
            )
        except Exception as e:
            print(f"Ogohlantirish: Original chek xabarini tahrirlashda xato: {e}")
            pass
            
    elif action == "admin_reject":
   
        new_caption = callback.message.caption + "\n\n**❌ RAD ETILDI:** Chek qabul qilinmadi."
        
        await callback.message.edit_caption(
            caption=new_caption,
            parse_mode='Markdown',
            reply_markup=None
        )
        await callback.bot.send_message(
            target_user_id,
            "❌ **Chek Qabul Qilinmadi.** Iltimos, qayta tekshirib yuboring.",
            parse_mode="Markdown"
        )
        await callback.answer("Chek rad etildi.", show_alert=True)

@router.message(AdminAction.waiting_for_amount, F.text)
async def process_admin_topup_amount(message: Message, state: FSMContext, db: Database, bot: Bot):
   
    
    user_data = await state.get_data()
    target_user_id = user_data.get('target_user_id')
    receipt_chat_id = user_data.get('receipt_chat_id') # Chek turgan guruh ID
    receipt_message_id = user_data.get('receipt_message_id') # Chek ID

    # 1. Summani tahlil qilish
    try:
        amount = float(message.text.replace(' ', ''))
        if amount <= 0:
            await message.answer("❌ Noto'g'ri summa formati. Iltimos, faqat musbat son kiriting.")
            return 
    except ValueError:
        await message.answer("❌ Noto'g'ri summa formati. Iltimos, faqat musbat son kiriting.")
        return 

    # 2. Balansni oshirish
    refund_success = await db.credit_balance(target_user_id, amount, "admin_topup") 
    
    # 3. Yakunlash va xabarnomalar
    if refund_success:
        new_balance = await db.get_user_balance(target_user_id)
        new_balance_text = f"{new_balance:,.0f} so'm" if new_balance is not None else "Noma'lum"
        
        # Admin uchun tasdiqlash xabari (PM da)
        await message.answer(
            f"✅ Balans muvaffaqiyatli oshirildi.\n"
            f"Foydalanuvchi ID: {target_user_id}\n"
            f"Miqdor: {amount:,.0f} so'm.\n"
            f"Yangi balans: {new_balance_text}."
        )
        
        # Foydalanuvchiga xabar yuborish
        try:
            await bot.send_message(
                target_user_id,
                f"💰 Balansingiz To'ldirildi!\n\n"
                f"Sizning hisobingizga administrator tomonidan {amount:,.0f} so'm qo'shildi.\n"
                f"Joriy Balansingiz: {new_balance_text}."
            )
        except Exception:
            await message.answer(f"⚠️ Ogohlantirish: Foydalanuvchi {target_user_id} ga xabar yuborilmadi (bloklagan bo'lishi mumkin).")
            
        # Original chek xabarini (Guruhdagi) yangilash
        try:
            original_caption = user_data.get('caption', f"Foydalanuvchi ID: {target_user_id}")
            await bot.edit_message_caption(
                chat_id=receipt_chat_id,
                message_id=receipt_message_id,
                caption=f"{original_caption}\n\n✅ TO'LDIRILDI: {amount:,.0f} so'm. Admin: {message.from_user.full_name}",
                reply_markup=None
            )
        except Exception as e:
            # Tahrirlash xato berishi mumkin (chek o'chirilgan bo'lsa)
            print(f"Original chekni tahrirlashda xato: {e}")
            pass

    else:
        await message.answer("❌ DB Xatosi: Balansni oshirish amalga oshmadi. Loglarni tekshiring.")
        
    # 4. FSM holatini tozalash
    await state.clear()

@router.message(Command("admin"))
async def  cmd_admin(message: types.Message):
    if message.from_user.id  != ADMIN_ID:
        await message.answer("⛔ Sizda admin huquqi yo‘q!")
        return
    
    await message.answer("🔐 Admin paneliga xush kelibsiz!", reply_markup = build_admin_reply_keyboard())

@router.message(lambda m: m.text == "➕ Kanal qo'shish")
async def add_channel(message: types.Message):
     if message.from_user.id != ADMIN_ID:
        return
    
     admin_action[message.from_user.id] = "add"
     await message.answer("➕ Qo‘shmoqchi bo‘lgan kanal username ni yuboring (@kanal_nomi).")

@router.message(lambda m: m.text == "➖ Kanal o‘chirish")
async def remove_channel_request(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    admin_action[message.from_user.id] = "remove"
    await message.answer("❌ O‘chirmoqchi bo‘lgan kanal username ni yuboring (@kanal_nomi).")
    
@router.message(lambda m: m.text and m.text.startswith("@"))
async def handle_channel(message: types.Message, db: Database):
    if message.from_user.id != ADMIN_ID:
        return
    
    username = message.text.strip()
    action = admin_action.get(message.from_user.id)

    if action == "add":
        await db.add_channel(username)
        await message.answer(f"✅ Kanal qo‘shildi: {username}")
    elif action == "remove":
        await db.remove_channel(username)
        await message.answer(f"🗑 Kanal o‘chirildi: {username}")
    else:
        await message.answer("ℹ️ Avval menyudan amalni tanlang (➕ qo‘shish yoki ➖ o‘chirish).")   
        
@router.message(lambda m: m.text == "📋 Kanallar ro‘yxati")
async def list_channels(message: types.Message, db:Database):
    if message.from_user.id != ADMIN_ID:
        return
    
    channels = await db.get_channels()
    if channels:
        text = "📋 Hozirgi kanallar:\n\n" + "\n".join([f"👉 {ch}" for ch in channels])
    else:
        text = "❌ Kanallar mavjud emas."
    await message.answer(text)   
    
@router.message(Command("refund"))
async def admin_refund_handler(message: types.Message, db):
    # 1. Admin Huquqini Tekshirish
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu buyruqni bajarishga ruxsat yo'q.")
        return
        
    # 2. Buyruqni Ajratish
    try:
        # Format: /refund <user_id> <amount> [reason]
        args = message.text.split()
        target_user_id = int(args[1])
        amount = float(args[2])
        reason = "Admin refund"
        if len(args) > 3:
            reason = " ".join(args[3:])
            
        if amount <= 0:
            await message.answer("Qaytariladigan summa musbat bo'lishi kerak.")
            return

    except (IndexError, ValueError):
        await message.answer("Noto'g'ri format. Foydalanish: /refund <user_id> <summa> [izoh]")
        return
        
    # 3. Pulni Qaytarish (Credit)
    refund_success = await db.credit_balance(target_user_id, amount, "admin_refund") 
    
    # 4. Xabar Yuborish
    if refund_success:
        # Adminni xabardor qilish
        await message.answer(
            f"✅ **{amount:,.2f} so'm** (ID: {target_user_id}) foydalanuvchi hisobiga muvaffaqiyatli qaytarildi. Sabab: {reason}"
        )
        
        # Foydalanuvchini xabardor qilish (Agar bu imkoniyat bo'lsa, Bot orqali)
        try:
            await message.bot.send_message(
                target_user_id,
                f"💰 **Balansingiz Oshirildi!**\nSizga **{amount:,.2f} so'm** qaytarildi (Refund).\n"
                f"Sabab: {reason}. Tizim bilan bog'liq xatolik tufayli."
            )
        except Exception:
            print(f"Foydalanuvchiga ({target_user_id}) xabar yuborishda xato.")
            
    else:
        await message.answer(f"❌ Qaytarish (refund) amalga oshmadi. Foydalanuvchi ID si noto'g'ri yoki DB xatosi.")