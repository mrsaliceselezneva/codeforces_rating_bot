import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from app.db.models import init_db
from app.handlers import admin, user, commands
from app.services.notifier import scheduler, send_weekly_contests, send_today_contests


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()]

# Настройка логов
logging.basicConfig(level=logging.INFO)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN не найден в .env")

    init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(commands.router)
    dp.include_router(user.router)
    dp.include_router(admin.router)

    scheduler.add_job(send_weekly_contests, "cron", day_of_week="mon", hour=9, minute=0, args=[bot])
    scheduler.add_job(send_today_contests, "cron", hour=10, minute=0, args=[bot])
    scheduler.start()

    logging.info("✅ Бот запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
