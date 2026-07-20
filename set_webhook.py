"""
ثبت آدرس Webhook در تلگرام (فقط یک‌بار بعد از هر دیپلوی روی Vercel اجرا کنید).

اجرا:
    export BOT_TOKEN="..."
    export WEBHOOK_URL="https://your-app.vercel.app/api/webhook"
    export WEBHOOK_SECRET="یک-رشته-تصادفی-دلخواه"   # اختیاری ولی توصیه‌شده
    python scripts/set_webhook.py
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
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").strip()
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()


async def main():
    if not BOT_TOKEN or not WEBHOOK_URL:
        print("❌ لطفاً BOT_TOKEN و WEBHOOK_URL را تنظیم کنید.")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.set_webhook(
            url=WEBHOOK_URL,
            secret_token=WEBHOOK_SECRET or None,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        )
        info = await bot.get_webhook_info()
        print("✅ Webhook با موفقیت تنظیم شد:")
        print(info)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
