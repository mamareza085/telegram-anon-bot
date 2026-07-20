"""
لایه‌ی دیتابیس (PostgreSQL / Supabase).

تغییرات مهم نسبت به نسخه‌ی قبلی برای سازگاری با Serverless:

۱) Pool دیگر در main() ساخته نمی‌شود، بلکه با get_pool() به‌صورت Lazy و
   Cache-شده ساخته می‌شود. در محیط Serverless (Vercel) هر «کانتینر گرم»
   ممکن است چند درخواست را پشت‌سرهم پردازش کند؛ با کش‌کردن pool در سطح
   ماژول، از باز کردن Pool جدید به‌ازای هر درخواست جلوگیری می‌شود.

۲) statement_cache_size=0 ست شده است. این یک باگ واقعی و رایج است: وقتی از
   Connection Pooler سوپابیس در حالت Transaction (پورت 6543 / PgBouncer)
   استفاده می‌کنید، asyncpg به‌صورت پیش‌فرض prepared statement کش می‌کند که
   با حالت Transaction pgbouncer ناسازگار است و خطای
   "prepared statement ... does not exist" می‌دهد. غیرفعال کردن کش آن را
   حل می‌کند و دقیقاً همان چیزی است که برای اجرای Serverless لازم داریم.

۳) min_size=0 و max_size کوچک، چون در هر Function Invocation معمولاً فقط
   یک درخواست هم‌زمان پردازش می‌شود و نباید به سقف اتصالات Supabase بخوریم.
"""

import asyncio
from datetime import datetime, timezone

import asyncpg

from bot import config

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    """Pool را می‌سازد (در صورت نبود) و برمی‌گرداند. ایمن در برابر فراخوانی هم‌زمان."""
    global _pool
    if _pool is not None and not _pool._closed:
        return _pool

    async with _pool_lock:
        if _pool is not None and not _pool._closed:
            return _pool
        _pool = await asyncpg.create_pool(
            dsn=config.DATABASE_URL,
            min_size=0,
            max_size=3,
            statement_cache_size=0,  # سازگاری با Supabase Pooler (PgBouncer / Transaction mode)
            command_timeout=15,
        )
        await _init_tables(_pool)
    return _pool


async def close_pool() -> None:
    """فقط برای حالت Polling/VPS لازم است (خروج تمیز). در Webhook صدا زده نمی‌شود."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def _init_tables(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            username TEXT,
            firstname TEXT,
            lastname TEXT,
            language TEXT,
            joined_at TIMESTAMPTZ,
            blocked BOOLEAN DEFAULT FALSE
        );
        """)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT,
            message_id BIGINT,
            owner_msg_id BIGINT,
            type TEXT,
            text TEXT,
            created_at TIMESTAMPTZ
        );
        """)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS states (
            owner_id BIGINT PRIMARY KEY,
            reply_to_user BIGINT,
            reply_to_msg BIGINT
        );
        """)


async def upsert_user(u) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id FROM users WHERE id=$1", u.id)
        if row is None:
            await conn.execute(
                "INSERT INTO users(id, username, firstname, lastname, language, joined_at) "
                "VALUES($1,$2,$3,$4,$5,$6)",
                u.id, u.username or "", u.first_name or "", u.last_name or "",
                u.language_code or "", datetime.now(timezone.utc),
            )
            return True
        await conn.execute(
            "UPDATE users SET username=$1, firstname=$2, lastname=$3, language=$4 WHERE id=$5",
            u.username or "", u.first_name or "", u.last_name or "", u.language_code or "", u.id,
        )
        return False


async def is_blocked(user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT blocked FROM users WHERE id=$1", user_id)
        return bool(r and r["blocked"])


async def set_blocked(user_id: int, val: bool) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET blocked=$1 WHERE id=$2", val, user_id)


async def get_user(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE id=$1", user_id)


async def save_message(user_id, message_id, owner_msg_id, mtype, text) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO messages(user_id, message_id, owner_msg_id, type, text, created_at) "
            "VALUES($1,$2,$3,$4,$5,$6)",
            user_id, message_id, owner_msg_id, mtype, text or "", datetime.now(timezone.utc),
        )


async def find_msg_by_owner(owner_msg_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM messages WHERE owner_msg_id=$1", owner_msg_id)


async def set_state(owner_id, reply_to_user, reply_to_msg=None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO states(owner_id, reply_to_user, reply_to_msg) VALUES($1,$2,$3) "
            "ON CONFLICT(owner_id) DO UPDATE SET reply_to_user=EXCLUDED.reply_to_user, "
            "reply_to_msg=EXCLUDED.reply_to_msg",
            owner_id, reply_to_user, reply_to_msg,
        )


async def get_state(owner_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM states WHERE owner_id=$1", owner_id)


async def clear_state(owner_id) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM states WHERE owner_id=$1", owner_id)


async def delete_user_data(user_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM messages WHERE user_id=$1", user_id)
        await conn.execute("DELETE FROM users WHERE id=$1", user_id)


async def count_stats():
    pool = await get_pool()
    async with pool.acquire() as conn:
        users = await conn.fetchval("SELECT COUNT(*) FROM users")
        blocked = await conn.fetchval("SELECT COUNT(*) FROM users WHERE blocked=TRUE")
        msgs = await conn.fetchval("SELECT COUNT(*) FROM messages")
        return users, blocked, msgs
