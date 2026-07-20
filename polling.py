"""
اجرای ربات به‌صورت Polling — برای هاست‌هایی که پروسه‌ی دائمی پشتیبانی می‌کنند
(VPS، Fly.io، Render و مشابه). برای Vercel/Serverless از api/webhook.py استفاده کنید.

اجرا:
    python polling.py
"""

import asyncio
import logging

from bot import config
from bot.core import get_bot, get_dispatcher
from bot.db import get_pool, close_pool

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("anon-bot")


async def main():
    config.validate()

    await get_pool()  # اتصال به دیتابیس + ساخت جداول در صورت نبود
    bot = get_bot()
    dp = get_dispatcher()

    log.info("🤖 Bot started (polling). Owner=%s", config.OWNER_ID)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
