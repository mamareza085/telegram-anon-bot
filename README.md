# 🤖 ربات ناشناس حرفه‌ای تلگرام (Aiogram 3 + PostgreSQL/Supabase)

پیام‌های کاربران (متن، عکس، ویدیو، فایل، ویس، آدیو، گیف، استیکر، لوکیشن، مخاطب) به‌صورت ناشناس برای **مالک** ارسال می‌شود. مالک می‌تواند پاسخ / ریپلای / پروفایل / بلاک / حذف کند.

این پروژه اکنون هم به‌صورت **Polling** (روی VPS/سرور معمولی) و هم به‌صورت **Webhook/Serverless** (روی Vercel) قابل اجراست، بدون این‌که منطق ربات تکراری نوشته شود.

## 🗂 ساختار پروژه

```
tgbot/
├── bot/
│   ├── config.py     تنظیمات/متغیرهای محیطی
│   ├── db.py         لایه‌ی PostgreSQL (asyncpg, Pool کش‌شده)
│   ├── keyboards.py  کیبوردهای اینلاین
│   ├── handlers.py   تمام هندلرهای aiogram (منطق ربات)
│   └── core.py       ساخت Bot/Dispatcher به‌صورت singleton
├── api/
│   └── webhook.py    اپ FastAPI که Vercel اجرا می‌کند (POST /api/webhook)
├── scripts/
│   ├── set_webhook.py     ثبت آدرس Webhook در تلگرام
│   └── delete_webhook.py  حذف Webhook (برگشت به Polling)
├── polling.py         اجرای سنتی با Polling (برای VPS)
├── requirements.txt
├── vercel.json
└── .env.example
```

## 🛠 مشکلات و باگ‌هایی که در این نسخه رفع شد

| مشکل | توضیح |
|---|---|
| کرش در import | نسخه‌ی قبلی با `raise SystemExit` در سطح ماژول، به‌محض import (نه فقط اجرا) کرش می‌کرد؛ در Serverless که فایل فقط import می‌شود این یعنی دیپلوی از کار می‌افتد. الان اعتبارسنجی به `config.validate()` منتقل شده و فقط لحظه‌ی پردازش واقعی درخواست اجرا می‌شود. |
| ناسازگاری asyncpg با PgBouncer | Supabase برای Serverless پیشنهاد Connection Pooler (پورت 6543) می‌دهد، ولی asyncpg به‌صورت پیش‌فرض Prepared Statement کش می‌کند که با حالت Transaction این Pooler تداخل دارد و خطای `prepared statement ... does not exist` می‌دهد. با `statement_cache_size=0` حل شد. |
| ساخت Pool به‌ازای هر اجرا | Pool دیتابیس حالا Lazy و Cache‌شده است (`db.get_pool()`) تا در Invocationهای گرم Vercel دوباره ساخته نشود و به سقف اتصالات Supabase نخوریم. |
| ساخت Bot/session تکراری | نمونه‌ی `Bot` و `Dispatcher` هم در `bot/core.py` کش شده‌اند تا هر درخواست یک aiohttp session جدید باز نکند. |
| عدم پشتیبانی Serverless | معماری Polling (`start_polling`) روی Vercel اصلاً کار نمی‌کرد چون پروسه‌ی دائمی نیست؛ حالا `api/webhook.py` مسیر Webhook را با FastAPI پیاده می‌کند. |
| بدون اعتبارسنجی امنیتی Webhook | مسیر Webhook حالا هدر `X-Telegram-Bot-Api-Secret-Token` را با `WEBHOOK_SECRET` چک می‌کند تا کسی غیر از تلگرام نتواند Update جعلی بفرستد. |
| تکرار کد بین اجرای لوکال و Webhook | منطق ربات از `bot.py` به ماژول‌های مجزا (`bot/*.py`) منتقل شد تا هم `polling.py` و هم `api/webhook.py` از همان کد استفاده کنند و آینده نگه‌داری راحت‌تر باشد. |

> ⚠️ محدودیت شناخته‌شده: Rate Limit در حافظه‌ی پروسه نگه‌داری می‌شود. روی VPS با Polling همیشه دقیق است؛ روی Vercel اگر Instance سرد شود، شمارنده موقتاً ریست می‌شود. برای دقت کامل روی Serverless باید آن را به یک جدول Postgres یا Redis منتقل کنید — در صورت نیاز بگویید تا اضافه‌اش کنم.

## 🚀 راه‌اندازی مشترک (هر دو حالت)

### ۱) ساخت پروژه Supabase
1. در [supabase.com](https://supabase.com) یک پروژه جدید بسازید.
2. از مسیر **Project Settings → Database → Connection string** آدرس را کپی کنید.
3. **برای Webhook/Serverless حتماً از حالت Connection Pooling (Transaction mode, پورت 6543)** استفاده کنید.

جداول به‌صورت خودکار توسط خود ربات هنگام اولین اجرا ساخته می‌شوند.

### ۲) نصب پکیج‌ها
```bash
pip install -r requirements.txt
```

### ۳) گرفتن توکن و آی‌دی
توکن از [@BotFather](https://t.me/BotFather) و آی‌دی عددی از [@userinfobot](https://t.me/userinfobot).

### ۴) تنظیم متغیرها
```bash
cp .env.example .env
```
و مقادیر `BOT_TOKEN` / `OWNER_ID` / `DATABASE_URL` را پر کنید.

---

## 🖥 حالت اول: Polling (VPS / سرور معمولی)

```bash
python polling.py
```

برای اجرای دائم روی یک VPS با systemd:
```ini
[Unit]
Description=Anonymous Telegram Bot
After=network.target

[Service]
WorkingDirectory=/opt/tgbot
EnvironmentFile=/opt/tgbot/.env
ExecStart=/usr/bin/python3 /opt/tgbot/polling.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## ☁️ حالت دوم: Webhook / Serverless روی Vercel

### ۱) دیپلوی
```bash
npm i -g vercel   # اگر نصب نیست
vercel
```
سپس در پنل Vercel، در بخش **Settings → Environment Variables**، سه مقدار `BOT_TOKEN`, `OWNER_ID`, `DATABASE_URL` (با پورت 6543) و اختیاراً `WEBHOOK_SECRET` را تنظیم کنید و دوباره Deploy بزنید (`vercel --prod`).

### ۲) ثبت آدرس Webhook در تلگرام
بعد از هر دیپلوی موفق، یک‌بار این را (از لوکال، نه روی Vercel) اجرا کنید:
```bash
export BOT_TOKEN="توکن_ربات"
export WEBHOOK_URL="https://YOUR-APP.vercel.app/api/webhook"
export WEBHOOK_SECRET="یک-رشته-تصادفی-طولانی"   # همان مقدار روی Vercel
python scripts/set_webhook.py
```

### ۳) تست
```
GET https://YOUR-APP.vercel.app/api/webhook   → {"ok": true, ...}
```
و بعد در تلگرام به ربات پیام بدهید — باید بلافاصله برای مالک فوروارد شود.

### برگشت به Polling
اگر خواستید موقتاً به Polling برگردید، اول Webhook را حذف کنید:
```bash
python scripts/delete_webhook.py
```
در غیر این‌صورت تلگرام همزمان هم Webhook فعال می‌بیند هم Polling، که خطا می‌دهد.

## 🔐 امنیت
- فقط `OWNER_ID` به پنل ادمین دسترسی دارد؛ سایرین پیام `⛔ Access Denied` می‌گیرند.
- توکن، کانکشن‌استرینگ دیتابیس و Secret فقط از Environment Variable خوانده می‌شوند.
- درخواست‌های Webhook با `WEBHOOK_SECRET` اعتبارسنجی می‌شوند.
- پیام‌ها با `copy_message` ناشناس ارسال می‌شوند؛ هیچ اطلاعاتی از فرستنده به دیگران نمایش داده نمی‌شود.
- Rate Limit: حداقل ۱.۵ ثانیه بین دو پیام و حداکثر ۵ پیام در ۱۰ ثانیه (نگاه کنید به محدودیت بالا).
- بلاک دائمی در دیتابیس ذخیره می‌شود.

## 🗂 ساختار دیتابیس (PostgreSQL)
- `users(id BIGINT, username, firstname, lastname, language, joined_at TIMESTAMPTZ, blocked BOOLEAN)`
- `messages(id BIGSERIAL, user_id, message_id, owner_msg_id, type, text, created_at TIMESTAMPTZ)`
- `states(owner_id BIGINT, reply_to_user, reply_to_msg)`

## 📋 دستورات مالک
- `/stats` — آمار کاربران/پیام‌ها
- `/unblock <user_id>` — رفع بلاک
- `/cancel` — لغو حالت پاسخ فعال
