from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.db.database import get_db
from dotenv import load_dotenv
import os

router = Router()
load_dotenv()

ADMINS = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()]


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (user_id,))
        user = cursor.fetchone()

        if user:
            await message.answer(
                "Привет! Вы уже зарегистрированы в боте.\n"
                "Вы будете получать уведомления о предстоящих раундах Codeforces Div2/3/4."
            )
        elif user_id in ADMINS:
            cursor.execute("""
                INSERT INTO users (telegram_id, first_name, last_name, is_admin)
                VALUES (?, ?, ?, 1)
            """, (
                user_id,
                message.from_user.first_name or "",
                message.from_user.last_name or ""
            ))
            conn.commit()

            await message.answer("Вы добавлены как администратор.")
        else:
            await message.answer(
                "Привет! Я бот для Codeforces.\n"
                "Если вы хотите получать уведомления о раундах, отправьте заявку:\n\n"
                "<code>/registration Имя Фамилия handle</code>"
            )


@router.message(Command("help"))
async def cmd_help(message: Message):
    user_id = message.from_user.id

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (user_id,))
        row = cursor.fetchone()

    if row:
        is_admin = row[0]
        if is_admin:
            text = (
                "🛠 <b>Команды администратора:</b>\n"
                "/add_user — добавить ученика. Введи /add_user и увидишь шаблон\n"
                "/remove_user &lt;handle&gt; — удалить ученика по хендлу\n"
                "/update_handle &lt;old&gt; &lt;new&gt; — обновить handle вручную. Укажи старый, потом новый\n"
                "/update_ratings_clear — обновить рейтинги всех учеников и удалить историю изменения рейтингов"
                "за время с последнего обновления\n"
                "/update_ratings — обновить рейтинги всех учеников\n"
                "/list_users — список зарегистрированных учеников\n"
                "/help — показать это сообщение"
            )
        else:
            text = (
                "ℹ️ <b>Команды пользователя:</b>\n"
                "/start — информация о боте\n"
                "/registration Имя Фамилия handle — отправить заявку на регистрацию\n"
                "/update_handle_request НовыйХендл — заявка на изменение хендла\n"
                "/help — показать это сообщение"
            )
    else:
        text = (
            "👋 <b>Привет! Я бот для Codeforces</b>\n\n"
            "Я рассылаю уведомления о Div2/3/4 раундах.\n"
            "Чтобы зарегистрироваться, отправьте:\n"
            "<code>/registration Имя Фамилия handle</code>"
        )

    await message.answer(text, parse_mode="HTML")

