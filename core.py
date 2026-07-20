"""
ساخت نمونه‌ی Bot و Dispatcher به‌صورت Singleton/Cache-شده.

چرا این‌طور؟ در Serverless (Vercel) وقتی یک Instance «گرم» چند درخواست پشت‌سرهم
می‌گیرد، اگر هر بار Bot جدید بسازیم یک aiohttp session جدید هم باز می‌شود که هم
کند است و هم منابع را هدر می‌دهد. با کش‌کردن در سطح ماژول، در Invocationهای گرم
همان نمونه‌ی قبلی استفاده می‌شود.
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot import config
from bot.handlers import router

_bot: Bot | None = None
_dp: Dispatcher | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        _dp = Dispatcher()
        _dp.include_router(router)
    return _dp
