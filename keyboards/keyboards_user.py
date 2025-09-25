from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def keyboard_start_users():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Выставить машину", callback_data="car"), InlineKeyboardButton(text=f"📦 Перевезти груз", callback_data="cargo")],
    ])

def keyboard_sendorno_users():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="send"), InlineKeyboardButton(text=f"❌ Отмена", callback_data="back")],
    ])

def keyboard_ingroup_users(manager_id: int, username):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Откликнуться", callback_data="reply"), InlineKeyboardButton(text="💬 Чат с логистом", url=f"https://t.me/{username}")]
        ]
    )