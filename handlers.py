"""
هندلرهای ربات. منطق دقیقاً همان نسخه‌ی قبلی است، فقط از bot.db و bot.keyboards
استفاده می‌کند تا این فایل هم برای Polling (VPS) و هم برای Webhook (Serverless)
قابل استفاده باشد.

⚠️ نکته درباره‌ی Rate Limit:
دیکشنری _rate در حافظه‌ی پروسه نگه‌داری می‌شود. روی یک سرور/VPS با Polling این
مشکلی ندارد چون پروسه همیشه یکی و زنده است. اما روی Serverless (Vercel) ممکن
است هر چند وقت یک‌بار یک Instance جدید و «سرد» بالا بیاید که این حافظه را ندارد؛
در آن لحظه محدودیت نرخ موقتاً ریست می‌شود. برای اکثر بات‌های شخصی/کوچک این
مشکلی ایجاد نمی‌کند، ولی اگر Rate Limit دقیق و تضمین‌شده لازم دارید باید آن را
به یک جدول در همان Postgres یا Redis منتقل کنید.
"""

import time
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message, CallbackQuery

from bot import config, db
from bot.keyboards import user_start_kb, message_kb, profile_kb

log = logging.getLogger("anon-bot")

router = Router()

# ---------- Rate Limit (در حافظه) ----------
_rate: dict[int, list[float]] = {}


def rate_ok(user_id: int) -> bool:
    now = time.time()
    arr = [t for t in _rate.get(user_id, []) if now - t < config.RATE_LIMIT_WINDOW]
    if arr and now - arr[-1] < config.RATE_LIMIT_SECONDS:
        _rate[user_id] = arr
        return False
    if len(arr) >= config.RATE_LIMIT_MAX:
        _rate[user_id] = arr
        return False
    arr.append(now)
    _rate[user_id] = arr
    return True


# ---------- /start ----------
@router.message(CommandStart())
async def cmd_start(message: Message):
    u = message.from_user
    if u.id == config.OWNER_ID:
        await message.answer(
            "👑 خوش آمدی مالک عزیز!\n\nربات فعال است.\nپیام‌های کاربران اینجا برایت ارسال می‌شود."
        )
        return

    new_user = await db.upsert_user(u)
    if await db.is_blocked(u.id):
        return  # سکوت کامل برای بلاک‌شده‌ها

    await message.answer(
        "👋 سلام!\nپیامت را بفرست، به صورت ناشناس به مالک ارسال می‌شود.\n\n"
        "می‌توانی متن، عکس، ویدیو، فایل، ویس، استیکر، لوکیشن یا مخاطب بفرستی."
    )

    if new_user:
        text = (
            "🔔 <b>کاربر جدید ربات را استارت کرد.</b>\n\n"
            f"👤 {u.first_name or ''} {u.last_name or ''}\n"
            f"🆔 <code>{u.id}</code>"
        )
        await message.bot.send_message(config.OWNER_ID, text, reply_markup=user_start_kb(u.id))


# ---------- تشخیص نوع پیام ----------
TYPE_MAP = [
    ("photo", "🖼 عکس"),
    ("video", "🎬 ویدیو"),
    ("document", "📎 فایل"),
    ("voice", "🎙 ویس"),
    ("audio", "🎵 آدیو"),
    ("animation", "🎞 گیف"),
    ("sticker", "💟 استیکر"),
    ("location", "📍 لوکیشن"),
    ("contact", "👤 مخاطب"),
    ("video_note", "🎥 ویدیو-نوت"),
]


def detect_type(msg: Message):
    for attr, label in TYPE_MAP:
        if getattr(msg, attr, None):
            return attr, label
    if msg.text:
        return "text", "📝 متن"
    return "unknown", "❓ ناشناخته"


# ---------- پیام مالک (حالت پاسخ) ----------
async def owner_message(message: Message):
    st = await db.get_state(config.OWNER_ID)
    if not st or not st["reply_to_user"]:
        return  # پیام آزاد مالک را نادیده بگیر
    target = st["reply_to_user"]
    reply_to = st["reply_to_msg"] or None
    try:
        await message.bot.copy_message(
            chat_id=target,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            reply_to_message_id=reply_to if reply_to else None,
        )
        await message.reply("✅ ارسال شد.")
    except Exception as e:
        await message.reply(f"❌ ارسال ناموفق: {e}")
    finally:
        await db.clear_state(config.OWNER_ID)


# ---------- دستورات مالک (باید قبل از هندلر عمومی پیام‌ها ثبت شوند) ----------
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != config.OWNER_ID:
        return await message.answer("⛔ Access Denied")
    users, blocked, msgs = await db.count_stats()
    await message.answer(
        f"📊 آمار\n\n👥 کاربران: {users}\n🚫 بلاک‌شده: {blocked}\n📩 پیام‌ها: {msgs}"
    )


@router.message(Command("unblock"))
async def cmd_unblock(message: Message, command: CommandObject):
    if message.from_user.id != config.OWNER_ID:
        return await message.answer("⛔ Access Denied")
    if not command.args:
        return await message.answer("Usage: /unblock <user_id>")
    try:
        uid = int(command.args.split()[0])
        await db.set_blocked(uid, False)
        await message.answer(f"✅ Unblocked {uid}")
    except ValueError:
        await message.answer("شناسه نامعتبر")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message):
    if message.from_user.id != config.OWNER_ID:
        return
    await db.clear_state(config.OWNER_ID)
    await message.answer("❌ حالت پاسخ لغو شد.")


# ---------- پیام‌های کاربر → مالک (هندلر عمومی؛ باید بعد از دستورات ثبت شود) ----------
@router.message(F.text | F.photo | F.video | F.document | F.voice | F.audio |
                 F.animation | F.sticker | F.location | F.contact | F.video_note)
async def user_message(message: Message):
    u = message.from_user
    if u.id == config.OWNER_ID:
        return await owner_message(message)  # پیام آزاد مالک → حالت پاسخ

    await db.upsert_user(u)
    if await db.is_blocked(u.id):
        return
    if not rate_ok(u.id):
        try:
            await message.reply("⏳ آرام‌تر! لطفاً کمی صبر کن.")
        except Exception:
            pass
        return

    mtype, label = detect_type(message)
    header = (
        f"📩 <b>پیام ناشناس</b>\n"
        f"از: {u.first_name or ''} {u.last_name or ''}\n"
        f"🆔 <code>{u.id}</code>\n"
        f"نوع: {label}"
    )

    try:
        await message.bot.send_message(config.OWNER_ID, header)
        copied = await message.bot.copy_message(
            chat_id=config.OWNER_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=message_kb(u.id, message.message_id, 0),
        )
        owner_msg_id = copied.message_id
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=config.OWNER_ID,
                message_id=owner_msg_id,
                reply_markup=message_kb(u.id, message.message_id, owner_msg_id),
            )
        except Exception:
            pass
        await db.save_message(u.id, message.message_id, owner_msg_id, mtype, message.text or message.caption or "")
        log.info("msg from %s (%s)", u.id, mtype)
    except Exception as e:
        log.exception("forward failed: %s", e)


# ---------- Callback ها ----------
@router.callback_query()
async def on_callback(callback: CallbackQuery):
    if callback.from_user.id != config.OWNER_ID:
        await callback.answer("⛔ Access Denied", show_alert=True)
        return
    await callback.answer()
    data = callback.data or ""
    message = callback.message

    if data.startswith("profile:"):
        uid = int(data.split(":")[1])
        r = await db.get_user(uid)
        if not r:
            return await message.reply("کاربر یافت نشد.")
        joined = r["joined_at"].strftime("%Y-%m-%d") if r["joined_at"] else "-"
        uname = f"@{r['username']}" if r["username"] else "-"
        txt = (
            f"👤 <b>نام:</b> {r['firstname']} {r['lastname'] or ''}\n"
            f"🆔 <b>شناسه:</b> <code>{r['id']}</code>\n"
            f"📛 <b>Username:</b> {uname}\n"
            f"🌍 <b>Language:</b> {r['language'] or '-'}\n"
            f"📅 <b>اولین ورود:</b> {joined}\n"
            f"🚫 <b>بلاک:</b> {'بله' if r['blocked'] else 'خیر'}"
        )
        await message.reply(txt, reply_markup=profile_kb(uid))

    elif data.startswith("unblock:"):
        uid = int(data.split(":")[1])
        await db.set_blocked(uid, False)
        await message.reply(f"✅ Unblocked\n🆔 <code>{uid}</code>")

    elif data.startswith("block:"):
        uid = int(data.split(":")[1])
        await db.set_blocked(uid, True)
        await message.reply(f"🚫 User Blocked\n🆔 <code>{uid}</code>")

    elif data.startswith("reply:"):
        _, uid, mid = data.split(":")
        await db.set_state(config.OWNER_ID, int(uid), int(mid) or None)
        note = "↩ ریپلای" if int(mid) else "💬 پاسخ"
        await message.reply(f"{note} فعال شد.\nحالا پیام خود را بفرست تا برای کاربر ارسال شود.")

    elif data.startswith("delm:"):
        owner_msg_id = int(data.split(":")[1])
        try:
            await callback.bot.delete_message(config.OWNER_ID, owner_msg_id)
        except Exception:
            pass
        try:
            await message.delete()
        except Exception:
            pass

    elif data.startswith("delu:"):
        uid = int(data.split(":")[1])
        await db.delete_user_data(uid)
        await message.reply(f"❌ پروفایل کاربر حذف شد.\n🆔 <code>{uid}</code>")
