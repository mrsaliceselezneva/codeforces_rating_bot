import asyncio
import os
from dotenv import load_dotenv
import httpx
from datetime import datetime, timedelta, timezone
from app.db.database import get_db
from aiogram import Bot
from app.utils.send_large_message import send_large_message
import asyncio

load_dotenv()

API_URL = os.getenv("API_URL_CODEFORCES")
API_URL_CONTESTS = os.getenv("API_URL_CODEFORCES_CONTESTS")

# Ограничение 1 запрос в 10 секунд
ADMINS = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()]
last_call = 0


async def get_user_info(handle: str):
    global last_call
    now = asyncio.get_event_loop().time()
    wait = 10 - (now - last_call)
    if wait > 0:
        await asyncio.sleep(wait)
    last_call = asyncio.get_event_loop().time()

    async with httpx.AsyncClient() as client:
        response = await client.get(API_URL, params={"handles": handle})
        try:
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise Exception(f"Ошибка при получении данных от Codeforces: {e}")

        if data.get("status") != "OK":
            raise Exception(f"Ошибка API для {handle}: {data.get('comment')}")

        result = data.get("result")
        if not result:
            raise Exception(f"Пользователь {handle} не найден.")

        return result[0]


def is_target_division(name: str) -> bool:
    return any(div in name for div in ["Div. 2", "Div. 3", "Div. 4"])


async def get_upcoming_div_contests():
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.get(API_URL_CONTESTS, params={"gym": "false"})
        data = r.json()
        if data["status"] != "OK":
            raise Exception(f"Codeforces API error: {data.get('comment')}")

        contests = data["result"]
        now = datetime.now(timezone.utc)

        upcoming = []
        for contest in contests:
            if contest["phase"] != "BEFORE":
                continue

            name = contest["name"]
            if not is_target_division(name):
                continue

            start_time = datetime.fromtimestamp(contest["startTimeSeconds"], tz=timezone.utc)
            url = f"https://codeforces.com/contests/{contest['id']}"

            upcoming.append({
                "name": name,
                "start": start_time,
                "url": url
            })

        # Отсортируем по времени
        upcoming.sort(key=lambda c: c["start"])
        return upcoming


def format_time(dt: datetime, fmt="%d.%m %H:%M") -> str:
    offset = int(os.getenv("DEFAULT_TIMEZONE_OFFSET", "0"))
    local_time = dt + timedelta(hours=offset)
    sign = "+" if offset >= 0 else "-"
    return f"{local_time.strftime(fmt)} UTC{sign}{abs(offset)}"


async def collect_daily_history(bot: Bot):
    errors = []

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT handle FROM users WHERE handle IS NOT NULL")
        users = cursor.fetchall()

    for (handle,) in users:
        try:
            info = await get_user_info(handle)
            rank = info.get("rank", "unrated")
            rating = info.get("rating", 0)
            timestamp = datetime.utcnow().isoformat()

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO history (handle, rank, rating, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (handle, rank, rating, timestamp))
                conn.commit()
        except Exception as e:
            errors.append(f"{handle}: {e}")
        await asyncio.sleep(5)  # не чаще 1 запроса в 10 секунд, подстраховка

    if errors:
        text = "❌ Ошибки при обновлении истории:\n" + "\n".join(errors)
    else:
        text = "✅ История рейтингов успешно обновлена."

    for admin_id in ADMINS:
        await send_large_message(bot, int(admin_id), text, parse_mode="HTML")
