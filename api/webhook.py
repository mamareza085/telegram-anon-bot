"""
Webhook برای اجرای Serverless (Vercel).

جریان کار:
    Telegram → POST /api/webhook → این فایل → aiogram Dispatcher → پاسخ

نکات امنیتی/فنی مهم:
- درخواست‌ها با هدر X-Telegram-Bot-Api-Secret-Token اعتبارسنجی می‌شوند تا کسی
  جز تلگرام نتواند به این آدرس Update جعلی بفرستد (اگر WEBHOOK_SECRET ست شده باشد).
- Bot/Dispatcher/DB Pool در سطح ماژول کش می‌شوند تا در Invocationهای گرم دوباره
  ساخته نشوند (نگاه کنید به bot/core.py و bot/db.py).
- Vercel به‌صورت خودکار اپ ASGI با نام "app" را در این فایل پیدا و اجرا می‌کند،
  پس نیازی به uvicorn.run() یا Mangum نیست؛ آن فقط برای اجرای لوکال لازم است.
"""

import logging

from fastapi import FastAPI, Request, Header, HTTPException
from aiogram.types import Update

from bot import config
from bot.core import get_bot, get_dispatcher
from bot.db import get_pool

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("webhook")

app = FastAPI()


@app.get("/api/webhook")
async def health():
    """صرفاً برای تست زنده بودن سرویس (Telegram هرگز GET نمی‌زند)."""
    return {"ok": True, "service": "telegram-anon-bot-webhook"}


@app.post("/api/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    try:
        config.validate()
    except RuntimeError as e:
        log.error(str(e))
        raise HTTPException(status_code=500, detail="server misconfigured")

    if config.WEBHOOK_SECRET and x_telegram_bot_api_secret_token != config.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="invalid secret token")

    # اطمینان از آماده بودن دیتابیس (Cache‌شده؛ در Invocationهای گرم سریع برمی‌گردد)
    await get_pool()

    bot = get_bot()
    dp = get_dispatcher()

    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})

    await dp.feed_update(bot=bot, update=update)
    return {"ok": True}
