from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def user_start_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👤 مشاهده پروفایل", callback_data=f"profile:{user_id}"),
        InlineKeyboardButton(text="🚫 بلاک", callback_data=f"block:{user_id}"),
    ]])


def message_kb(user_id: int, user_msg_id: int, owner_msg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 پاسخ", callback_data=f"reply:{user_id}:0"),
            InlineKeyboardButton(text="↩ ریپلای", callback_data=f"reply:{user_id}:{user_msg_id}"),
        ],
        [
            InlineKeyboardButton(text="👤 پروفایل", callback_data=f"profile:{user_id}"),
            InlineKeyboardButton(text="🚫 بلاک", callback_data=f"block:{user_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑 حذف پیام", callback_data=f"delm:{owner_msg_id}"),
            InlineKeyboardButton(text="❌ حذف پروفایل", callback_data=f"delu:{user_id}"),
        ],
    ])


def profile_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💬 پاسخ", callback_data=f"reply:{user_id}:0"),
        InlineKeyboardButton(text="🚫 بلاک", callback_data=f"block:{user_id}"),
        InlineKeyboardButton(text="❌ حذف پروفایل", callback_data=f"delu:{user_id}"),
    ]])
