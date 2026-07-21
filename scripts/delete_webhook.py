"""
حذف Webhook (مثلاً وقتی می‌خواهید موقتاً به حالت Polling برگردید).

اجرا:
    export BOT_TOKEN="..."
    python scripts/delete_webhook.py
"""

import asyncio
import os
import sys

from aiogram import Bot

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()


async def main():
    if not BOT_TOKEN:
        print("❌ لطفاً BOT_TOKEN را تنظیم کنید.")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook حذف شد.")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
