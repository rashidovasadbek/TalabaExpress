from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup , State
from database import Database
from config import ADMIN_ID
from typing import Dict

router = Router()
class AdminSettings(StatesGroup):
    choosing_prompt_key = State()
    waiting_for_new_prompt = State()
    
PROMPT_KEYS: Dict[str, str] = {
    "refarat_uz": "O'zb. Referat (essay)",
    "mustaqil_ish_uz": "O'zb. Mustaqil ish (thesis)",
    "title_page_uz": "O'zb. Titul varaqa"
} 

def build_prompt_key_keyboard() -> types.InlineKeyboardMarkup:
    buttons = []
    
    for key, text in PROMPT_KEYS.items():
        buttons.append([types.InlineKeyboardButton(text=text, callback_data=f"set_prompt_{key}")])
    
    buttons.append([types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_admin_op")])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def build_admin_prompt_menu() -> types.InlineKeyboardMarkup:
    """/prompt buyrug'i uchun asosiy admin menu klaviaturasi."""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📝 Promptni O'zgartirish", callback_data="admin_change_prompt")
        ],
        [
            types.InlineKeyboardButton(text="👁 Promptlarni Ko'rish", callback_data="admin_view_prompts")
        ]
    ])
    
@router.message(Command("prompt"))
async def cmd_prompt_menu(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return 
        
    await message.answer(
        "🛠 **AI Prompt Boshqaruvi Paneli**",
        reply_markup=build_admin_prompt_menu()
    )

@router.callback_query(F.data == "admin_change_prompt")
async def start_prompt_setup(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
        
    await state.set_state(AdminSettings.choosing_prompt_key)
    
    await callback.message.edit_text(
        "Iltimos, o'zgartirmoqchi bo'lgan **Prompt turini** tanlang:",
        reply_markup=build_prompt_key_keyboard()
    )
    await callback.answer()
    
@router.callback_query(F.data.startswith("set_prompt_"), AdminSettings.choosing_prompt_key)
async def prompt_key_selected(callback: types.CallbackQuery, state: FSMContext, db: Database):
    prompt_key = callback.data.split("_")[2]
    
    # Bazadan hozirgi qiymatni olish
    current_prompt = await db.get_setting(prompt_key)
    
    # Keyinchalik foydalanish uchun FSM ga saqlash
    await state.update_data(current_prompt_key=prompt_key)
    await state.set_state(AdminSettings.waiting_for_new_prompt)
    
    # Foydalanuvchiga matnni tushunarli qilib ko'rsatish
    await callback.message.edit_text(
        f"✅ Tanlandi: **`{prompt_key}`**\n\n"
        f"**Hozirgi matn:**\n"
        f"```\n{current_prompt or 'Hali prompt kiritilmagan.'}\n```\n\n"
        "Iltimos, **yangi prompt matnini** yuboring. Matnda mavzu joyiga **`{topic}`** kalit so'zini qo'shishni unutmang!",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminSettings.waiting_for_new_prompt)
async def process_new_prompt_value(message: types.Message, state: FSMContext, db: Database):
    new_prompt_value = message.text
    user_data = await state.get_data()
    prompt_key = user_data.get("current_prompt_key")
    
    if not prompt_key:
        await message.answer("Xatolik: Prompt kaliti topilmadi. Qayta boshlang.")
        await state.clear()
        return

    # Bazada yangilash
    await db.update_setting(prompt_key, new_prompt_value)
    
    await message.answer(
        f"✅ Prompt muvaffaqiyatli yangilandi!\n"
        f"**Kalit:** `{prompt_key}`",
        parse_mode="Markdown",
        reply_markup=build_admin_prompt_menu() # Asosiy admin menyuga qaytish
    )
    
    # Holatni tiklash
    await state.clear()
    
@router.callback_query(F.data == "admin_view_prompts")
async def view_all_prompts(callback: types.CallbackQuery, db: Database):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo'q!") 
        return

    # >>> Bu yerda yangi metod chaqiriladi <<<
    all_settings = await db.get_all_settings()
    
    response_text = "📑 **Bazadagi Barcha Promptlar:**\n\n"
    
    if not all_settings:
        response_text += "Bazada hech qanday prompt saqlanmagan."
    else:
        for setting in all_settings:
            # Sozlamalar lug'at (dict) ko'rinishida keladi: {'key': '...', 'value': '...', 'description': '...'}
            
            # 1. Prompt tavsifini va kalitini ko'rsatish
            description = setting.get('description') or 'Tavsif yo\'q'
            response_text += f"**🔑 Kalit:** `{setting['key']}`\n"
            response_text += f"**📝 Tavsif:** _{description}_ \n"
            
            # 2. Matn qiymatini qisqartirib ko'rsatish
            prompt_value = setting['value']
            if len(prompt_value) > 300:
                # Yangi qatorlar (newline) joyiga bo'sh joy qo'yamiz
                short_value = prompt_value[:300].replace('\n', ' ') + "..."
            else:
                short_value = prompt_value.replace('\n', ' ')

            response_text += f"**Matn Qiymati (qisqa):** `{short_value}`\n"
            response_text += "--------------------------------------\n"
            
    await callback.message.edit_text(
        response_text,
        parse_mode="Markdown",
        reply_markup=build_admin_prompt_menu()
    )
    await callback.answer()
    
@router.callback_query(F.data == "cancel_admin_op")
async def cancel_admin_op(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Sozlash bekor qilindi.", reply_markup=build_admin_prompt_menu())
    await callback.answer()
    