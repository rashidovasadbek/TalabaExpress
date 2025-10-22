from aiogram import Dispatcher, types, F
from aiogram.types import  FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram import Router
from inline import get_channel_keyboard
from aiogram import Bot, types
from database import Database
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from ai_service import GeminiService
from constants import HELP_MESSAGE, ADMIN_CARD_NUMBER, PRICING, PAYMENT_CHANNEL_ID
from word_generator import generate_word_file, PAGE_TITLES 
from pptx_generate import generate_pptx_file as generate_pptx
from ai_service import GeminiService
from datetime import datetime
from inline import get_admin_receipt_action_keyboard
import os
from aiogram.types import BotCommand
from aiogram.types import Message, CallbackQuery
from aiogram.utils.deep_linking import create_start_link
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import urllib.parse
from aiogram.filters import StateFilter
import base64
from aiogram.types import Message

class UserGeneration(StatesGroup):
    choosing_language = State() 
    waiting_for_topic = State()
    waiting_for_uni_faculty = State()
    waiting_for_student_info = State()
    choosing_for_group = State()
    choosing_page_count = State()
    waiting_for_confirmation = State()

class Payment(StatesGroup):
    
    waiting_for_receipt = State() 

router = Router()

WELCOME_TEXT = (
    "TalabaExpress\n\n"
    "📚 Talabalarga yordamchi bot\n\n"
    "TalabaExpress bilan siz:\n"
    "• Referat va mustaqil ishlarni (DOCX) tez va qulay yarata olasiz.\n"
    "• Prezentatsiyalar (PPTX) keyinchalik qo‘llanadi.\n"
    "• PDF (tez kunda) va boshqa formatlar keladi.\n\n"
    "⏳ Ayniqsa deadline yaqinlashganda juda qulay — bir necha daqiqada hujjat tayyorlanadi.\n\n"
    "Unutmang: Agar siz yangi foydalanuvchi bo'lsangiz, sizga 10000 so'm boshlang'ich balans berildi!\n\n"
    "Pastdagi tugmalardan birini tanlang:"
)

def build_main_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 Referat (DOCX)"),
             KeyboardButton(text="📄 Mustaqil ish (DOCX) ")],
            [KeyboardButton(text="💰 Balans"),
             KeyboardButton(text="📘 Yo'riqnoma")]
        ],
        resize_keyboard=True
    )
    return kb

def build_language_keyboard() -> types.InlineKeyboardMarkup:
    """Generatsiya tilini tanlash klaviaturasi."""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🇺🇿 O'zbek tili", callback_data="lang_uz"),
            types.InlineKeyboardButton(text="🇷🇺 Rus tili", callback_data="lang_ru"),
        ],
        [
            types.InlineKeyboardButton(text="🇬🇧 Ingliz tili", callback_data="lang_en"),
            types.InlineKeyboardButton(text="🇺🇿 Кирилча", callback_data="lang_kr"),
        ],
    ])
    
def build_page_count_keyboard() -> types.InlineKeyboardMarkup:
    """Sahifalar sonini oralig'ini tanlash klaviaturasi."""
    return types.InlineKeyboardMarkup(inline_keyboard=[

        [types.InlineKeyboardButton(text="10 dan 15 gacha", callback_data="pages_10_15")],
        [types.InlineKeyboardButton(text="15 dan 20 gacha", callback_data="pages_15_20")],
        [types.InlineKeyboardButton(text="20 dan 30 gacha", callback_data="pages_21_30")],
    ])

def build_slide_count_keyboard() -> types.InlineKeyboardMarkup:
    """PPTX uchun slaydlar sonini tanlash tugmalarini yaratadi."""
    return types.InlineKeyboardMarkup(inline_keyboard=[

        [types.InlineKeyboardButton(text="10 - 15 slayd", callback_data="slides_10_15")],
        [types.InlineKeyboardButton(text="15 - 20 slayd", callback_data="slides_15_20")],
        [types.InlineKeyboardButton(text="20+ slayd", callback_data="slides_20_25")],
    ])

def build_confirmation_keyboard() -> types.InlineKeyboardMarkup:
    """Ma'lumotlarni tasdiqlash, o'zgartirish yoki bekor qilish tugmalari."""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Tayyorlash", callback_data="confirm_data"),
        ],
        [
            types.InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="edit_data"), # Qayta boshlash
            types.InlineKeyboardButton(text="🚫 Rad etish", callback_data="cancel_generation")
        ]
    ])

async def  check_user_subs(bot: Bot, user_id: int, db:Database) -> list[str]:
    not_joined = []
    channels = await db.get_channels()
    for ch_name in channels:
        if not ch_name.startswith(('-', '@')):
            channel_id = '@' + ch_name
        else:
            channel_id = ch_name
            
        try:
            member = await bot.get_chat_member(channel_id, user_id) 
            
            if member.status not in["creator", "administrator", "member"]:
                not_joined.append(ch_name)
                
        except Exception:
            not_joined.append(ch_name)
            
    return not_joined

@router.message(F.text == "📄 Referat (DOCX)")
async def handle_start_doc_referat(message: types.Message, state: FSMContext, bot: Bot, db: Database):
    
    # Qayta Obuna Tekshiruvi
    not_joined = await check_user_subs(bot, message.from_user.id, db)
    if not_joined:
        text = "📌 Siz quyidagi kanallarga a'zo bo'lishingiz kerak:\n\n"
        text += "\n".join([f"👉 {ch}" for ch in not_joined])
        await message.answer(text, reply_markup=get_channel_keyboard(not_joined))
        return
    
    await state.update_data(work_type='refarat')
    
    await state.set_state(UserGeneration.choosing_language)
    
    await message.answer(
        "Iltimos, hujjat **qaysi tilda** yaratilishi kerakligini tanlang:",
        reply_markup=build_language_keyboard(),
        parse_mode="Markdown"
    )
    
@router.message(F.text == "📄 Mustaqil ish (DOCX)")
async def handle_start_doc_mustaqil_ish(message: types.Message, state: FSMContext, bot: Bot, db: Database):
    

    not_joined = await check_user_subs(bot, message.from_user.id, db)
    if not_joined:
        text = "📌 Siz quyidagi kanallarga a'zo bo'lishingiz kerak:\n\n"
        text += "\n".join([f"👉 {ch}" for ch in not_joined])
        await message.answer(text, reply_markup=get_channel_keyboard(not_joined))
        return
    
    await state.update_data(work_type='mustaqil_ish')
    
    await state.set_state(UserGeneration.choosing_language)
    
    await message.answer(
        "Iltimos, hujjat **qaysi tilda** yaratilishi kerakligini tanlang:",
        reply_markup=build_language_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "💰 Balans", StateFilter(None, "*"))
async def handle_balance_button(message: types.Message, db: Database):
     
    balance = await db.get_user_balance(message.from_user.id) 
 
    if balance is None:
        balance = 0.00
        
    balance_display = f"{balance:,.0f} so'm"
    
    balance_text = f"""
        💰 **Sizning Hisobingiz Holati**

        **Joriy Balans:** **{balance_display}**

        ---
        ⚡️ **Tezkor Toʻldirish:**
        Balansingizni toʻldirish uchun ** /buy ** buyrugʻini bosing.
        Buyurtmangizni toʻxtatib qoʻymang!
        """
    await message.answer(balance_text, parse_mode="Markdown")

@router.message(F.text == "📊 Prezentatsiya (PPTX)")
async def handle_start_pptx(message: types.Message, state: FSMContext, bot: Bot, db:Database):
    
    not_joined = await check_user_subs(bot, message.from_user.id, db)
    if not_joined:
            text = "📌 Siz quyidagi kanallarga a'zo bo'lishingiz kerak:\n\n"
            text += "\n".join([f"👉 {ch}" for ch in not_joined])
            await message.answer(text, reply_markup=get_channel_keyboard(not_joined))
            return
        
    await state.update_data(work_type = 'prezentatsiya')
    
    await state.set_state(UserGeneration.choosing_language)
    
    await message.answer(
        "Iltimos, prezentatsiya **qaysi tilda** yaratilishi kerakligini tanlang:",
        reply_markup=build_language_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "📘 Yo'riqnoma", StateFilter(None, "*"))
async def handle_help_button_redirect(message: types.Message):
    # Bu funkisiya asosiy menyudagi 'ℹ️ Yordam' tugmasi bosilganda ishlaydi

    # Foydalanuvchiga yordam matni va admin lichkasiga o'tish tugmasi (Inline) yuboriladi
    await message.answer(
        HELP_MESSAGE, # O'zingiz kiritgan yordam matni
        reply_markup=get_help_contact_keyboard(), # Admin lichkasiga yo'naltiruvchi Inline tugma
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("lang_"), UserGeneration.choosing_language)
async def language_selected(callback: types.CallbackQuery, state: FSMContext):
    lang_code = callback.data.split("_")[1] 
    
    await state.update_data(lang=lang_code)
    
    await state.set_state(UserGeneration.waiting_for_topic)
    
    await callback.message.edit_text(
        "✅ Sizdan so'ralgan ma'lumotlarni **aniq va bexato** kiritishingiz ta'lab qilinadi!\n\n"
        "🆕 **Yangi mavzuni to'liq, bexato va tushunarli xolatda** yuboring:",
        parse_mode="Markdown"
    )

    await callback.answer()

@router.message(UserGeneration.waiting_for_topic)
async def process_topic(message: types.Message, state: FSMContext):
    await state.update_data(topic=message.text)
    
    await state.set_state(UserGeneration.waiting_for_uni_faculty)
    
    await message.answer(
        "**Institut va Kafedrangizni (majburiy emas)** to'liq kiriting.\n\n"
        "📋**Namuna:** `FARG‘ONA DAVLAT UNIVERSITETI IQTISODIYOT KAFEDRASI`\n",
        parse_mode="Markdown"
    )

@router.message(UserGeneration.waiting_for_uni_faculty)
async def process_uni_faculty(message: types.Message, state: FSMContext):
    
    await state.update_data(uni_faculty=message.text)
    
    await state.set_state(UserGeneration.waiting_for_student_info)
    
    await message.answer(
        "**(F.I.O)** to'liq kiriting.\n\n"
        "📋**Namuna:**`AZIZBEK ABDURAHMONOV`\n",
        parse_mode="Markdown"
    )

@router.message(UserGeneration.waiting_for_student_info) 
async def process_student_fio(message: types.Message, state: FSMContext): 
    
    await state.update_data(student_fio=message.text.strip()) 
    
    await state.set_state(UserGeneration.choosing_for_group) 
    
    await message.answer("**Guruhingizni** to'liq kiriting.\n\n"
                            "📋**Namuna:**`721-21`\n",
        parse_mode="Markdown")
    
@router.message(UserGeneration.choosing_for_group)
async def process_group_and_finish(message: types.Message, state: FSMContext):
        
    await state.update_data(student_group = message.text.strip())
    
    # --- TUZATILGAN LOGIKA: Oxirgi bosqich - Sahifalar/Slaydlar sonini so'rash ---
    
    await state.set_state(UserGeneration.choosing_page_count)
    
    user_data = await state.get_data()
    work_type = user_data.get('work_type', 'refarat')
    
    if work_type == 'prezentatsiya':
        prompt_text = "Nechta **slayd**dan iborat prezentatsiya yaratish kerak?"
        keyboard_builder = build_slide_count_keyboard() # Slayd soni uchun alohida klaviatura
    else:
        prompt_text = "Sahifalar sonini oraliq ko'rinishida tanlang:"
        keyboard_builder = build_page_count_keyboard() # Sahifalar soni uchun alohida klaviatura
        
    
    await message.answer(
        prompt_text,
        reply_markup=keyboard_builder,
        parse_mode="Markdown"
    )
    
@router.callback_query(F.data.startswith(("pages_", "slides_")), UserGeneration.choosing_page_count)
async def show_data_for_confirmation(callback: types.CallbackQuery, state: FSMContext):
    
    full_page_data = callback.data
    page_range = callback.data.split("_")
    min_pages = page_range[1]
    max_pages = page_range[2]
    
    await state.update_data(
        min_pages=min_pages, 
        max_pages=max_pages,
        page_count=full_page_data 
    )
        
    user_data = await state.get_data()
    
    escaped_topic = escape_markdown(user_data.get('topic'))
    escaped_uni = escape_markdown(user_data.get('uni_faculty'))
    escaped_student = escape_markdown(user_data.get('student_fio'))
    escaped_group = escape_markdown(user_data.get('student_group'))
    
    work_type_raw = user_data.get('work_type', 'Refarat')
    work_type_display = work_type_raw.replace('_', ' ').capitalize() 
    
    count_label = "Slaydlar soni" if work_type_raw == 'prezentatsiya' else "Sahifalar soni"
    
    response_text = "🎉 **Buyurtma Tayyor! Maʼlumotlaringizni Tekshiring.** 🎉\n\n"
    response_text += "Quyidagi maʼlumotlar asosida loyiha tayyorlanadi. Xatolik yoʻqligiga ishonch hosil qiling:\n\n"
    # --------------------------------------------------------------------------------------------------
    response_text += "📚 **Loyiha Tafsilotlari**\n"
    response_text += f"   • **Ish Turi:** {work_type_display}\n"
    response_text += f"   • **Mavzu:** *{escaped_topic}*\n"
    response_text += f"   • **Til:** {user_data.get('lang', 'uz').upper()}\n"
    response_text += f"   • **Sahifalar Son: ({count_label}):** {min_pages} dan – {max_pages} gacha\n\n"

    response_text += "👤 **Muallif Maʼlumotlari**\n"
    response_text += f"   • **Institut/Kafedra:** {escaped_uni or '— *Kiritilmagan*'}\n"
    response_text += f"   • **F.I.O. (Talaba):** {escaped_student or '— *Kiritilmagan*'}\n"
    response_text += f"   • **Guruhi:** {escaped_group or '— *Kiritilmagan*'}\n\n"
    # --------------------------------------------------------------------------------------------------
    response_text += "✅ **Agar maʼlumotlar toʻgʻri boʻlsa, TASDIQLANG.**" 
    
    await state.set_state(UserGeneration.waiting_for_confirmation)

    await callback.message.edit_text(
        response_text,
        reply_markup=build_confirmation_keyboard(), # build_confirmation_keyboard() ni chaqiramiz
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_generation") 
async def cancel_generation(callback: types.CallbackQuery, state: FSMContext):
    """
    Generatsiya jarayonini butunlay bekor qiladi va boshlang'ich holatga qaytaradi.
    Callback message tahrirlashdagi xatolikni (TelegramBadRequest) e'tiborsiz qoldirish uchun try/except ishlatildi.
    """
    
    # 1. FSM holatini tozalash
    await state.clear()
    
    try:
        # 2. Xabarni tahrirlash (Agar Telegram ruxsat bersa)
        await callback.message.edit_text(
            "❌ **Jarayon bekor qilindi.**\n\nBoshidan boshlash uchun asosiy tugmalardan birini tanlang:",
            reply_markup=build_main_reply_keyboard(), 
            parse_mode="Markdown"
        )
    except Exception:
        # 2.1 Agar xabarni tahrirlash imkonsiz bo'lsa (vaqti o'tgan bo'lsa), yangi xabar yuborish
        await callback.message.answer(
            "❌ **Jarayon bekor qilindi.**\n\nBoshidan boshlash uchun asosiy tugmalardan birini tanlang:",
            reply_markup=build_main_reply_keyboard(), 
            parse_mode="Markdown"
        )

    # 3. Callback so'roviga javob berish (Oxirida chaqirish shart)
    await callback.answer(text="Jarayon bekor qilindi.", show_alert=False)

@router.callback_query(F.data == "edit_data", UserGeneration.waiting_for_confirmation)
async def edit_data(callback: types.CallbackQuery, state: FSMContext):
    """
    Generatsiya ma'lumotlarini o'zgartirish (qayta kiritish) uchun mavzu kiritish bosqichiga qaytaradi.
    """
    
    # FSM holatini to'g'ridan-to'g'ri Mavzu kiritish bosqichiga qaytarish
    await state.set_state(UserGeneration.waiting_for_topic)
    
    # Foydalanuvchiga mavzuni qayta kiritishni so'rash
    await callback.message.edit_text(
        "✏️ **Ma'lumotlarni o'zgartirish**\n\n"
        "Iltimos, **yangi mavzuni to'liq, bexato va tushunarli xolatda** yuboring (yoki eski mavzuni qayta kiriting):",
        parse_mode="Markdown",
        reply_markup=None # Inline tugmalarni o'chirish
    )
    
    await callback.answer(text="Ma'lumotlarni qayta kiritish boshlandi.", show_alert=False)

def escape_markdown(text):
    """Matndagi Telegram Markdown belgilarni zararsizlantiradi."""
    if not text:
        return 'Kiritilmagan'
    
    # Textni majburiy ravishda stringga aylantirish
    text = str(text) 
    
    # Telegramdagi barcha maxsus belgilarni tozalash (V2 usuli)
    # _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., !
    
    # Faqat biz foydalanadigan ** ni hisobga olib (Caption uchun)
    
    text = text.replace('_', r'\_')
    text = text.replace('*', r'\*')
    text = text.replace('`', r'\`')
    text = text.replace('[', r'\[').replace(']', r'\]')
    text = text.replace('(', r'\(').replace(')', r'\)')
    text = text.replace('#', r'\#')
    text = text.replace('+', r'\+')
    text = text.replace('-', r'\-') # <<-- Bu belgi ko'pincha xato beradi!
    text = text.replace('=', r'\=')
    text = text.replace('|', r'\|')
    text = text.replace('{', r'\{').replace('}', r'\}')
    text = text.replace('.', r'\.')
    text = text.replace('!', r'\!')
    text = text.replace('~', r'\~')
    text = text.replace('>', r'\>')
    text = text.replace('\\', r'')
    text = text.replace('/', r'')

    return text

def get_cost_from_range(range_key_raw: str) -> float:
    """
    Sahifa diapazoniga qarab narxni qaytaradi. 
    range_key_raw 'pages_15_20' yoki '15-20' formatida kelishi mumkin.
    """
    
    # 1. Narxni qidirish uchun kalitni tayyorlash
    page_range_key = range_key_raw # Default holat: '15-20' kabi
    
    try:
        if range_key_raw.startswith("pages_"):
            # Callback data formatini ('pages_15_20') '15-20' formatiga o'tkazish
            parts = range_key_raw.split('_')
            
            # Agar format to'g'ri bo'lsa (pages, 15, 20)
            if len(parts) >= 3:
                page_range_key = f"{parts[1]}-{parts[2]}" 
            else:
                # Agar callback formati buzilgan bo'lsa
                page_range_key = '15-20' 
        
        # 2. PRICING lug'atidan narxni olish
        # Agar kalit topilmasa, 0.0 qaytaramiz (yoki o'rnatilgan default narx)
        cost = PRICING.get(page_range_key)
        
        if cost is not None:
            return float(cost)
            
    except Exception as e:
        # Kodni tahlil qilishda yoki konvertatsiyada xato ketsa
        print(f"ERROR in get_cost_from_range: {e}. Raw key: {range_key_raw}")
        # xato yuz berganda ham, hech bo'lmaganda default narxni qaytarishga harakat qilish
        pass

    # Kalit topilmasa yoki xato yuz bersa, 0.0 qaytarish
    return 0.0

@router.callback_query(F.data == "confirm_data", UserGeneration.waiting_for_confirmation)
async def final_generation_start(callback:types.CallbackQuery, state: FSMContext, db:Database):
    user_data = await state.get_data()
    file_path = None
    user_id = callback.from_user.id
    work_id = None # ai_works jadvali uchun ID
    
    page_count_raw = user_data.get("page_count", "pages_15_20") 
    
    cost = get_cost_from_range(page_count_raw)
    tr_type = "generation"
    
    user_balance = await db.get_user_balance(user_id) 
    
    if user_balance is None:
        user_balance = 0.00
    
    if  user_balance < cost:
        # user_balance None bo'lsa, uni 0 ga o'rnatish kerak, aks holda xato beradi:
        
        display_balance = user_balance
        
        await callback.message.edit_text(
            # display_balance dan foydalaning, chunki user_balance None bo'lishi mumkin
            f"❌ **Mablag' Yetarli Emas!** Balansingiz: **{display_balance:,.2f} so'm**."
            f" Bu ish uchun **{cost:,.0f} so'm** kerak. Iltimos, /buy buyrug'i orqali to'ldiring."
        )
        await state.clear()
        await callback.message.answer(
            "Bot bilan ishlashni davom ettirish uchun quyidagi tugmalardan birini tanlang:",
            reply_markup = build_main_reply_keyboard()
        )
        return
    

    debit_success = await db.debit_balance(user_id, cost, tr_type)
    if not debit_success:
        await callback.message.edit_text("❌ Uzr, pul yechishda texnik xatolik yuz berdi. Balansingizni tekshiring va qayta urinib ko'ring.")
        await state.clear()
        return
    
    try:
        gemini_service = GeminiService()
    except ValueError as e:
        if cost > 0:
                 await db.credit_balance(user_id, cost, "rollback")
        await callback.message.edit_text(str(e))
        return
    
    final_reja_data = []
    intro_text = ""      
    conclusion_text = ""  
    references_text = ""  
    final_title_data = {} 
    
    try:
        await callback.message.edit_text(
            "🔥 **Loyihangizga Start Berildi!** 🔥\n\n"
            "Hozirda yuqori quvvatli tizimlarimiz so'rovingizni qayta ishlamoqda.\n"
            "✍️ Kerakli sahifalar soni bo'yicha matn shakllantirilmoqda...\n\n"
            "⏳ **Bir necha daqiqa sabr qiling.** Tayyor **DOCX fayl** tez orada shu yerda bo'ladi!",
            parse_mode='Markdown' 
        )
        work_type = user_data.get('work_type', 'refarat')
        
        if work_type == 'mustaqil_ish':
            work_type_display = "Mustaqil ish"
        elif work_type == 'prezentatsiya':
            work_type_display = "Prezentatsiya"
        else:
            work_type_display = "Refarat"
        
        topic = user_data.get('topic', 'Mavzu aniqlanmagan')
        selected_lang_code = user_data.get('lang', 'uz')
        page_count_raw = user_data.get("page_count", "pages_15_20") 

        page_count = 20 
        min_page_count  = 10
        
        if isinstance(page_count_raw, str) and page_count_raw.startswith("pages_"):
            try:
                parts = page_count_raw.split('_')
                page_count = int(parts[-1]) 
                min_page_count = int(parts[-2])               
            except (ValueError, IndexError):
                page_count = 20
                min_page_count = 10 
        elif isinstance(page_count_raw, int):
            page_count = page_count_raw

        if page_count > 20: 
            main_sections = 3
        else: 
            main_sections = 2           
        await state.update_data(page_count=page_count)
        
        title_page_data = await gemini_service.generate_title_page_content(
            work_type=work_type, 
            lang=selected_lang_code
        )

        uni_name_uz = user_data.get('uni_name', "FARG'ONA DAVLAT UNIVERSITETI")
        uni_kafedra_uz = user_data.get('uni_faculty', "IQTISODIYOT KAFEDRASI")
        
        uni_name_translated = await gemini_service.translate_text(uni_name_uz, selected_lang_code)
        uni_kafedra_translated = await gemini_service.translate_text(uni_kafedra_uz, selected_lang_code)
        topic_translated = await gemini_service.translate_text(topic, selected_lang_code)
        
        
        doc_data = {
            'student_fio': user_data.get('student_fio', 'Talaba F.I.O.si kiritilmagan'), 
            'student_group': user_data.get('student_group', 'Guruh raqami kiritilmagan'),
            'supervisor_fio': (''), 
            'uni_kafedra': user_data.get('uni_faculty', title_page_data['uni_placeholder']), 
            'raw_work_type': work_type,
            'university_name': title_page_data['uni_placeholder'],
            'university_name': uni_name_translated,
            'uni_kafedra': uni_kafedra_translated,
            'topic': topic_translated,
            'year': datetime.now().year,
        }
        current_date = datetime.now()
        current_year = current_date.year
        academic_year_start = current_year
        academic_year_end = current_year + 1           
        academic_year_str = f"{academic_year_start}-{academic_year_end}"
        
        if work_type == 'prezentatsiya':
           
            try:
                min_c, max_c = map(int, user_data.get("page_count", "15_20").split('_'))
                num_slides = int((min_c + max_c) / 2) 
            except:
                num_slides = 15
                
            slide_titles_list = await gemini_service.generate_slide_titles(
            topic=topic,
            num_slides=num_slides,
            lang=selected_lang_code
            )
            if not slide_titles_list:
                await callback.message.edit_text(
                    "❌ **Generatsiya xatosi:** AI modelidan slayd rejasini olishning imkoni bo'lmadi. Keyinroq urinib ko'ring."
                )
                return
            
            await state.update_data(slide_titles=slide_titles_list)
            
            presentation_content = []

            await callback.message.edit_text(
                f"🚀 **{len(slide_titles_list)}ta slayd uchun kontent generatsiyasi boshlandi!**\n\n"
                f"⌛ Bu jarayon har bir slayd uchun alohida so'rov yuborishni talab qiladi va biroz vaqt olishi mumkin.",
                parse_mode='Markdown'
            )
            
            for i, title in enumerate(slide_titles_list):
            
                # Progress xabarini yangilash
                await callback.message.edit_text(
                    f"📝 **Kontent Olinmoqda** ({i+1}/{len(slide_titles_list)}):\n\n"
                    f"Sarlavha: **{title}**",
                    parse_mode='Markdown'
                )

                # Slayd kontentini generatsiya qilish
                content_text = await gemini_service.generate_slide_content(
                    topic=topic,
                    slide_title=title,
                    lang=selected_lang_code
                )
                
                # Sarlavha va kontentni umumiy ro'yxatga saqlash
                presentation_content.append({
                    "title": title,
                    "content": content_text
                })
                
            await callback.message.edit_text("✅ **Kontent to'liq generatsiya qilindi.** Hujjat tayyorlanmoqda...")
            
            BASE_DIR = os.getcwd() 
            TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')
            DEFAULT_THEME_PATH = os.path.join(TEMPLATE_FOLDER, 'minimal_clean.pptx') 
            print(DEFAULT_THEME_PATH)
            
            file_path = await generate_pptx(
                doc_data, 
                presentation_content,
                temp_dir='temp_files',
                theme_path = DEFAULT_THEME_PATH) 
            
            await callback.message.answer_document(
                document=FSInputFile(file_path),
                caption=f"✅ **'{topic_translated}'** mavzusidagi {work_type_display} tayyor!",
                parse_mode='Markdown' 
            )
           
        elif  work_type in ['refarat', 'mustaqil_ish']:
        
            main_titles_list = await gemini_service.generate_reja_titles(
            topic=topic,
            work_type=work_type_display,
            num_sections=main_sections,
            lang = selected_lang_code
            )
        
            for main_title in main_titles_list:
                sub_titles_list = await gemini_service.generate_sub_titles(
                    topic=topic,
                    main_title=main_title,
                    work_type=work_type_display,
                    num_sub_sections=3,
                    lang = selected_lang_code
                )
                
                section_content = await gemini_service.generate_section_content(
                    topic=topic,
                    main_title=main_title,
                    sub_titles_list=sub_titles_list,
                    main_sections_count=main_sections,
                    work_type=work_type_display,
                    page_count=page_count,
                    min_page_count=min_page_count,
                    lang = selected_lang_code,
                )
                
                final_reja_data.append({
                    "main_title": main_title,
                    "sub_titles": sub_titles_list,
                    "content": section_content
                })
            
            intro_text = await gemini_service.generate_introduction_text(
                topic=topic,
                work_type=work_type_display,
               
                main_titles_list=[data["main_title"] for data in final_reja_data],
                lang = selected_lang_code
            )
            
            conclusion_text = await gemini_service.generate_conclusion_text(
                topic=topic,
                work_type=work_type_display,
                final_reja_data=final_reja_data,
                lang = selected_lang_code
            )
            
            references_text = await gemini_service.generate_references_list(
                topic=topic,
                num_references=5,
                lang = selected_lang_code
            )
                        
            lang_titles = PAGE_TITLES.get(selected_lang_code, PAGE_TITLES['uz'])
            
            if work_type =='mustaqil_ish':
                work_title_key  = 'title_mustaqil_ish'
            else:
                work_title_key  = 'title_referat'
            
            main_sections_count = user_data.get('main_sections', 3)
            
            xulosa_raqami = main_sections_count + 1
            adabiyot_raqami = main_sections_count + 2

            final_title_data = {
                'reja_sarlavha': lang_titles['reja_sarlavha'],
                'title_intro': lang_titles['kirish'],
                'title_conclusion': lang_titles['xulosa'].replace('4.', f'{xulosa_raqami}.'),
                'title_references': lang_titles['adabiyotlar_title'], 
                'work_title_display': lang_titles[work_title_key],
                'kirish': lang_titles['kirish'],
                'xulosa': lang_titles['xulosa'].replace('4.', f'{xulosa_raqami}.'),
                'adabiyotlar': lang_titles['adabiyotlar'].replace('5.', f'{adabiyot_raqami}.'),
                'city_year': academic_year_str,              
                'vazirlik_title': lang_titles['vazirlik_title'] ,
                'label_topic': lang_titles['label_topic'],           
                'label_bajaruvchi': lang_titles['label_bajaruvchi'], 
                'label_group': lang_titles['label_group'],           
                'label_rahbar': lang_titles['label_rahbar'],        
                'label_study_year': lang_titles['label_study_year'], 
            }
             
            file_path = generate_word_file(
                    
                    work_type_display, 
                    final_reja_data,
                    doc_data = doc_data,
                    title_data = final_title_data,
                    intro_text = intro_text,
                    conclusion_text = conclusion_text,
                    references_text = references_text)
        else:
             await callback.message.edit_text("Hujjat turi noto'g'ri tanlangan.")
        
        if file_path:
            await callback.message.answer_document(
                document=FSInputFile(file_path),
                caption=f"{user_data.get('topic', 'Hujjat')}",
                        parse_mode='Markdown' 
            ) 
        
        message_text = (
                f"✅ **'{user_data.get('topic', 'Hujjat')}'** mavzusidagi {work_type_display} tayyor!\n"
                f"Sarf: {cost:,.0f} so'm."
            )

        await callback.message.answer(
                message_text,
                parse_mode='Markdown'
            )
    except Exception as e:
      
        print(f"Generatsiya xatosi: {e}")
        
        if cost > 0 :
          
            await db.credit_balance(user_id, cost, "rollback")
            
            error_msg = f"❌ **Texnik Xatolik!** Hujjatni yaratishda xato yuz berdi: {e} \n"
            error_msg += "Yechilgan mablag' **hisobingizga to'liq qaytarildi**."
            await callback.message.edit_text(error_msg, parse_mode='Markdown')
        
    finally:
    
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            
       
        await state.clear()
        
        await callback.message.answer(
        "Bot bilan ishlashni davom ettirish uchun quyidagi tugmalardan birini tanlang:",
        reply_markup = build_main_reply_keyboard()
    )
    
@router.message(Command("buy"))
async def command_buy_handler(message: types.Message, db):
    
    price_list = ""
    for page_range, price in PRICING.items():
       
        price_list += f"\n🔹{page_range} sahifa uchun: **{price:,.0f} so'm**\n"
        
    buy_text = f"""
            💳 **Tezkor Balans Toʻldirish Boʻyicha Qoʻllanma!**

        Sizning loyihangizni tezroq yakunlash uchun atigi 3 ta qadam qoldi! 🚀

        ---
        **1. 💰 Narxlarni Koʻrib Chiqing:**
        Botimizdagi narxlar sahifa soniga qarab belgilangan:
        {price_list}

        **2. 🏦 Toʻlovni Amalga Oshiring:**
        Istalgan bank ilovasi orqali quyidagi kartaga pul oʻtkazing:
        - **Karta Raqami:** `{ADMIN_CARD_NUMBER}`
        - **Qabul qiluvchi:** RASHIDOV ASADBEK
        
        **3. 🧾 Chekni Yuboring:**
        Pul oʻtkazmasi muvaffaqiyatli yakunlangach, shu chatga **toʻlov chekining rasmini (skrinshotini) yoki faylini (hujjatini)** yuboring.

        **4. ✅ Tasdiqlashni Kuting:**
        Chekni yuborganingizdan soʻng, adminimiz darhol uni tekshiradi va balansingizni toʻldiradi. Jarayon tezkor amalga oshiriladi!

        **Esda tuting:** Sizning balans toʻldirishingiz faqatgina 1-5 daqiqa vaqt oladi! Ishingizni tezroq bitiring! 😉
        """
    await message.answer(
        buy_text, 
        parse_mode="Markdown", 
        # Inline keyboardni uzatayotganingizga ishonch hosil qiling
        reply_markup=get_payment_keyboard() 
    )

async def handle_check_prompt(context_obj: Message | CallbackQuery, state: FSMContext):
    
    # Message yoki CallbackQuery ob'ektidan xabar ob'ektini olish
    if isinstance(context_obj, CallbackQuery):
        message = context_obj.message
        
        await context_obj.answer() 
    else:
        message = context_obj

    await state.clear() 
    
    chek_prompt_text = f"""
    📸 **Mablag'ni Faollashtirishning Oxirgi Qadami!** 🚀

    Ajoyib! Endi to'lov chekingizni yuboring.

    **DIQQAT QILING:**
    1.  Iltimos, amalga oshirilgan to'lovning **FAAQATGINA BITTA** rasm (skrinshot) yoki hujjat (fayl, PDF) ko'rinishidagi chekini yuboring.
    2.  Boshqa xabarlar, matnlar yoki hujjatlar yubormang.

    Biz chekni darhol tekshiramiz va balansingizni to'ldiramiz! Tezkor ishingiz uchun rahmat! 😉
    """
    
    if isinstance(context_obj, CallbackQuery):
        await message.edit_text(chek_prompt_text, parse_mode="Markdown")
    else:
        await message.answer(chek_prompt_text, parse_mode="Markdown")
        
    await state.set_state(Payment.waiting_for_receipt)

@router.callback_query(F.data == "start_payment_upload")
async def start_payment_upload(callback: types.CallbackQuery, state: FSMContext):
    # Logikani yordamchi funksiyaga o'tkazamiz
    await handle_check_prompt(callback, state) 

@router.message(Command("chek"))
async def command_chek_handler(message: types.Message, state: FSMContext):
    # Logikani yordamchi funksiyaga o'tkazamiz
    await handle_check_prompt(message, state) 

def get_payment_keyboard() -> types.InlineKeyboardMarkup:
    """To'lov chekini yuborish uchun maxsus tugma."""
    keyboard = [
        [
            # ✅ InlineKeyboardMarkup emas, balki InlineKeyboardButton ishlatilishi kerak!
            types.InlineKeyboardButton(
                text="📤 Chekni Yuborishga O'tish", 
                callback_data="start_payment_upload"
            )
        ]
    ]
    # InlineKeyboardMarkup konteyneriga tugmalar ro'yxatini uzatamiz
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Payment.waiting_for_receipt, F.photo | F.document)
async def process_receipt_upload(message: types.Message, state: FSMContext, bot: Bot):
    
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else 'yo\'q'
    
    # Chek uchun caption yaratish
    caption_text = (
        "🚨 YANGI TO'LOV CHEKI! 🚨\n\n"
        f"🔹 Foydalanuvchi ID: `{user_id}`\n"
        f"🔹 Username: @{username}\n\n"
        "_Admin: Chekni tekshiring va pastdagi tugmalardan birini bosing._"
    )

    file_id = None
    send_method = None
    media_arg_name = None
    

    if message.photo:
        # Agar rasm bo'lsa
        file_id = message.photo[-1].file_id # Eng yuqori sifatli rasmni olish
        send_method = bot.send_photo
        media_arg_name = 'photo'
    elif message.document:
        # Agar hujjat bo'lsa (PDF, JPEG/PNG hujjat sifatida, va h.k.)
        file_id = message.document.file_id
        send_method = bot.send_document
        media_arg_name = 'document'
    
    if file_id and send_method and media_arg_name:
        media_args = {
            media_arg_name: file_id
        }
        try:
            # 2. Chekni admin guruhiga yuborish
            # send_photo yoki send_document ni dinamik chaqirish
            await send_method(
                chat_id=PAYMENT_CHANNEL_ID,
                **media_args,              
                caption=caption_text, 
                parse_mode='HTML',
                reply_markup=get_admin_receipt_action_keyboard(user_id) 
            )
        except Exception as e:
            print(f"ERROR: Admin kanaliga chek yuborishda xato: {e}")
            await message.answer("❌ Uzr, chekni admin kanaliga yuborishda texnik xato yuz berdi. Adminga murojat qiling")
            return
    else:
        # Agar F.photo yoki F.document filtrlari muvaffaqiyatsiz bo'lsa, bu yerga tushadi.
        await message.answer("❌ Iltimos, amalga oshirilgan to'lov chekining rasmi yoki hujjatini yuboring.")
        return


    # 3. Foydalanuvchiga tasdiqlash xabari
    await message.answer(
        "✅ Chekingiz adminlarga muvaffaqiyatli yuborildi.\n"
        "Adminlar chekni tekshirib, hisobingizni oshirishadi. Bu biroz vaqt olishi mumkin."
    )
    
    # 4. Holatni tozalash va menyuga qaytarish
    await state.clear()
    await message.answer(
        text="✅ Chek muvaffaqiyatli yuklandi. Tekshiruvdan so'ng hisobingiz to'ldiriladi.",
        reply_markup=build_main_reply_keyboard()
    )

@router.message(Payment.waiting_for_receipt)
async def process_receipt_invalid(message: types.Message):
    await message.answer("❌ Iltimos, faqat to'lov chekining **rasmini** (skrinshotini) yuboring.")

REFERRAL_BONUS = 2000 

@router.message(Command("start"))
async def cmd_start(message: types.Message, bot: Bot, db: Database):
    user_id = message.from_user.id
    username = message.from_user.username
    
    referrer_id = None

    if message.text and len(message.text.split()) > 1:
        payload = message.text.split()[1]
        try:
            # Payloadni baytlarga aylantiramiz va dekodlaymiz
            decoded_payload_bytes = base64.urlsafe_b64decode(payload + '==') 
            decoded_payload = decoded_payload_bytes.decode('utf-8')
            
            # Agar dekodlangan matn "ref_" bilan boshlansa, ishni davom ettiramiz
            if decoded_payload.startswith("ref_"):
                referrer_id = int(decoded_payload.replace("ref_", ""))
                if referrer_id == user_id:
                    referrer_id = None
            
        except Exception as e:
            # Agar dekodlashda xato bo'lsa (bu Base64 bo'lmasa yoki noto'g'ri bo'lsa)
            print(f"Referral payloadni dekodlashda xato: {e}")
            referrer_id = None
    

    not_joined = await check_user_subs(bot, user_id, db)

    if not_joined:
        text = "📌 Siz quyidagi kanallarga a'zo bo'lishingiz kerak:\n\n"
        text += "\n".join([f"👉 {ch}" for ch in not_joined])
        await message.answer(text, reply_markup=get_channel_keyboard(not_joined))
    else:
        db_result = await db.get_or_create_user(user_id, username, referrer_id=referrer_id)

      
        if db_result is None or db_result[0] is False:
             await message.answer(
                "❌ Uzr, ma'lumotlar bazasi bilan ulanishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
            )
             return
        
       
        is_new_user = db_result[1] 
        
        if is_new_user and referrer_id is not None:
            
           
            await db.add_balance(referrer_id, REFERRAL_BONUS)
            
            try:
                await bot.send_message(
                    referrer_id, 
                    f"🎉 **Tabriklaymiz!** Siz taklif qilgan yangi foydalanuvchi botga qo'shildi. Hisobingizga **{REFERRAL_BONUS} so'm** qo'shildi.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        
        # Xush kelibsiz xabarini yuborish
        await message.answer(
            WELCOME_TEXT, 
            reply_markup=build_main_reply_keyboard(), 
            parse_mode="Markdown"
        )

async def set_default_commands(bot: Bot):
    commands = [
            BotCommand(command="start", description="🚀 Botni ishga tushirish (Asosiy Menyu)"),
            BotCommand(command="new", description="✍️ Yangi Referat/Mustaqil ish tayyorlash"),
            BotCommand(command="buy", description="💸 Balansni tezkor to'ldirish (Narxlar)"),
            BotCommand(command="chek", description="🧾 To'lov chekini yuborish va mablag'ni faollashtirish"), 
            BotCommand(command="referral", description="🤝 Do'stlarni taklif qilish va pul ishlash"),
        ]
    await bot.set_my_commands(commands)
    
@router.message(Command("help"))
async def command_help_handler(message: types.Message):
    
    await message.answer(
        HELP_MESSAGE,
        parse_mode="Markdown"
    )

@router.message(Command("new"))
async def command_new_handler(message: types.Message,state: FSMContext, db: Database):
    await state.clear() 
    await cmd_start(message, state, db)

@router.message(Command("referral"))
async def command_referral_handler(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    bot_username = (await bot.get_me()).username # Botning username'ini olamiz
    
    # 1. Shaxsiy referal havolani yaratish
    personal_link = await create_start_link(bot, f"ref_{user_id}", encode=True) 
    
    # 2. Taklif qilinadigan JODIY REKLAMA MATNI
    share_message_text = f"""
    📚 <b>TALABALIKNI OSONLASHTIR!</b> 🚀
    
    Men ajoyib botni topdim! @{bot_username} — referat, mustaqil ish va taqdimotlarni (DOCX/PPTX) bir necha daqiqada tayyorlaydi.
    
    🎁 Sizga ham <b>+10000 so'm</b> boshlang'ich bonus beriladi!
    
    Qo'shilish uchun: <a href="{personal_link}"><b>BOTGA O'TISH</b></a>
    """
    
    encoded_text = urllib.parse.quote_plus(share_message_text) # Bu endi HTML ni kodlaydi
    share_url = f"https://t.me/share/url?url={encoded_text}&parse_mode=HTML"

    # 4. Asosiy xabar va statistika
    referral_text = f"""
    🤝 <b>Dostlaringizni taklif qiling va bonular oling!</b> 💰
    
    Sizning ulashgan havolangiz orqali do'stingiz botga qo'shilishi bilan, hisobingizga darhol:
    ✨ <b>+{REFERRAL_BONUS} so'm qo'shiladi!</b> ✨
    
    ---
    
    <b>📊 Statistikangiz:</b>
    * Taklif qilganlar: <b>0</b> kishi
    * Jami daromad: <b>0</b> so'm
    
    QO'SHILISH UCHUN HAVOLA: <a href="{personal_link}">BOTGA O'TISH</a>
    """
    
    # 5. Inline Klaviatura yaratish
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚀 Do'stga Xabarni Yuborish",
                url=share_url # Ulashish (Share) havolasi
            )
        ]
    ])
    
    # 6. Yagona xabarni yuborish
    await message.answer(
        referral_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

def get_help_contact_keyboard() -> types.InlineKeyboardMarkup:

    ADMIN_ID = 5052391328 
    admin_link = f"tg://user?id={ADMIN_ID}" 
    
    help_button = types.InlineKeyboardButton( 
        text="ℹ️ Yordam (Admin bilan bog'lanish)",
        url=admin_link
    )
    
    return types.InlineKeyboardMarkup(inline_keyboard=[[help_button]])

@router.callback_query(F.data == "check_subs")
async def check_subs(callback: types.CallbackQuery, bot: Bot, db: Database):
    not_joined = await check_user_subs(bot, callback.from_user.id, db)
    
    if not_joined:
        await callback.answer("❌ Siz hali hamma kanallarga a'zo bo‘lmadingiz!", show_alert=True)
    else:
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.message.answer(WELCOME_TEXT,reply_markup=build_main_reply_keyboard(), parse_mode="HTML")
        await callback.answer()