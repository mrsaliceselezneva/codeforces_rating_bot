import asyncio
import os
from dotenv import load_dotenv
import httpx
from datetime import datetime, timedelta, timezone

load_dotenv()

API_URL = os.getenv("API_URL_CODEFORCES")
API_URL_CONTESTS = os.getenv("API_URL_CODEFORCES_CONTESTS")

# Ограничение 1 запрос в 10 секунд
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
        data = response.json()
        if data["status"] != "OK":
            raise Exception(f"Ошибка API для {handle}: {data.get('comment')}")
        return data["result"][0]


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
