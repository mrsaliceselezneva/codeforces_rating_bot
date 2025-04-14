from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone, timedelta
from pytz import timezone as pytz_timezone
import os
from aiogram import Bot
import asyncio

from db.database import get_db
from services.codeforces import get_upcoming_div_contests, format_time

local_timezone = pytz_timezone("Asia/Dubai")
scheduler = AsyncIOScheduler(timezone=local_timezone)


async def send_weekly_contests(bot: Bot):
    upcoming = await get_upcoming_div_contests()
    if not upcoming:
        return

    lines = ["📅 Предстоящие раунды на этой неделе:"]
    for c in upcoming:
        start = format_time(c["start"])
        lines.append(f"\n🔸 <b>{c['name']}</b>\n🕒 {start}\n🔗 <a href='{c['url']}'>Перейти</a>")
    text = "\n".join(lines)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id FROM users")
        users = [row[0] for row in cursor.fetchall()]

    for uid in users:
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            await asyncio.sleep(0.3)
        except Exception:
            pass


async def send_today_contests(bot: Bot):
    upcoming = await get_upcoming_div_contests()
    if not upcoming:
        return

    offset = int(os.getenv("DEFAULT_TIMEZONE_OFFSET", "0"))
    now = datetime.now(timezone.utc) + timedelta(hours=offset)
    today = now.date()
    today_contests = [c for c in upcoming if c["start"].date() == today]
    if not today_contests:
        return

    lines = ["📢 Сегодня пройдёт раунд:"]
    for c in today_contests:
        start = format_time(c["start"])
        lines.append(f"\n<b>{c['name']}</b>\n🕒 {start}\n🔗 <a href='{c['url']}'>Перейти</a>")
    text = "\n".join(lines)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id FROM users")
        users = [row[0] for row in cursor.fetchall()]

    for uid in users:
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            await asyncio.sleep(0.3)
        except Exception:
            pass
