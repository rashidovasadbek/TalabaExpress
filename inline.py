from aiogram.utils.keyboard import InlineKeyboardBuilder 
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import types

def get_admin_receipt_action_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Admin chekni tasdiqlash yoki rad etish uchun tugmalar."""
    
    keyboard = [
        [
            # QABUL QILISH: callback_data ichida user_id saqlanadi
            types.InlineKeyboardButton(
                text="✅ Qabul Qilish", 
                callback_data=f"admin_accept:{user_id}"
            ),
        ],
        [
            # RAD ETISH: callback_data ichida user_id saqlanadi
            types.InlineKeyboardButton(
                text="❌ Rad Etish", 
                callback_data=f"admin_reject:{user_id}"
            )
        ]
    ]
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_channel_keyboard(not_joined: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    
    # Har bir kanal uchun tugma qo'shamiz
    for ch in not_joined:
        kb.row(
            InlineKeyboardButton(
                text=ch.replace("@", ""), 
                url=f"https://t.me/{ch.lstrip('@')}"
            )
        )
    
    # Oxiriga "A'zo bo'ldim" tugmasi
    kb.row(InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="check_subs"))
    
    return kb.as_markup()