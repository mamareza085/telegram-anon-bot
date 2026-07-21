"""
تنظیمات و متغیرهای محیطی.

نکته مهم: برخلاف نسخه‌ی قبلی، اینجا در صورت نبودن یک متغیر محیطی، در لحظه‌ی
import هیچ SystemExit ای رخ نمی‌دهد. این کار عمداً به تابع validate() موکول شده
چون در حالت Webhook/Serverless این فایل صرفاً «import» می‌شود (مثلاً توسط Vercel
برای ساخت تابع) و نباید فقط به‌خاطر نبود env در لحظه‌ی import کرش کند؛ اعتبارسنجی
باید در زمان پردازش واقعی درخواست انجام شود تا خطای واضح و قابل‌فهم برگردد.
"""

import os

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
OWNER_ID = int(os.environ.get("OWNER_ID", "0") or "0")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# توکن مخفی برای اعتبارسنجی درخواست‌های Webhook تلگرام (اختیاری ولی به‌شدت توصیه می‌شود).
# همین مقدار باید هنگام ثبت وبهوک (scripts/set_webhook.py) هم به تلگرام داده شود.
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()

RATE_LIMIT_SECONDS = 1.5  # حداقل فاصله بین دو پیام کاربر
RATE_LIMIT_MAX = 5        # حداکثر پیام در بازه
RATE_LIMIT_WINDOW = 10    # بازه زمانی به ثانیه


def validate() -> None:
    """اعتبارسنجی متغیرهای ضروری. در زمان اجرای واقعی (نه در import) صدا زده می‌شود."""
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not OWNER_ID:
        missing.append("OWNER_ID")
    if not DATABASE_URL:
        missing.append("DATABASE_URL")
    if missing:
        raise RuntimeError(
            "❌ متغیرهای محیطی زیر تنظیم نشده‌اند: " + ", ".join(missing) +
            " (در .env یا Environment Variables پلتفرم میزبانی تنظیم کنید)"
        )
