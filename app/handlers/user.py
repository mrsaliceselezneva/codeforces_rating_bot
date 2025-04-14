from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from db.database import get_db
import os

router = Router()
ADMINS = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()]


@router.message(Command("registration"))
async def handle_registration(message: Message):
    parts = message.text.strip().split(maxsplit=3)

    if len(parts) != 4:
        await message.answer("Используйте формат:\n/registration Имя Фамилия handle")
        return

    _, first_name, last_name, handle = parts
    telegram_id = message.from_user.id

    with get_db() as conn:
        cursor = conn.cursor()

        # есть ли пользователь с таким handle
        cursor.execute("SELECT telegram_id FROM users WHERE handle = ?", (handle,))
        row = cursor.fetchone()

        if not row:
            await message.answer("❌ Этот handle не найден. Попросите администратора добавить вас.")
            return

        existing_telegram_id = row[0]

        if existing_telegram_id:
            if existing_telegram_id == telegram_id:
                await message.answer("✅ Вы уже зарегистрированы.")
            else:
                await message.answer("❌ Этот handle уже привязан к другому пользователю.")
            return

    # отправляем заявку всем админам
    for admin_id in ADMINS:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"approve:{telegram_id}:{handle}")]
        ])
        await message.bot.send_message(
            admin_id,
            text=(
                f"📥 Заявка на регистрацию:\n"
                f"<b>{last_name} {first_name}</b>\n"
                f"Handle: <code>{handle}</code>\n"
                f"<a href='tg://user?id={telegram_id}'>Открыть профиль</a>"
            ),
            reply_markup=kb,
            parse_mode="HTML"
        )

    await message.answer("📨 Заявка отправлена администраторам. Ожидайте подтверждения.")


@router.message(Command("update_handle_request"))
async def update_handle_request(message: Message):
    telegram_id = message.from_user.id
    args = message.text.strip().split()

    if len(args) != 2:
        await message.answer("⚠️ Используйте: /update_handle_request <новый_handle>")
        return

    new_handle = args[1]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT handle, first_name, last_name FROM users WHERE telegram_id = ?
        """, (telegram_id,))
        row = cursor.fetchone()

    if not row:
        await message.answer("❌ Вы не зарегистрированы.")
        return

    old_handle, first_name, last_name = row

    for admin_id in ADMINS:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Принять",
                callback_data=f"confirm_handle_update:{telegram_id}:{new_handle}"
            )]
        ])
        await message.bot.send_message(
            admin_id,
            text=(
                f"📤 Запрос на изменение handle:\n"
                f"<b>{last_name} {first_name}</b>\n"
                f"Старый: <code>{old_handle}</code>\n"
                f"Новый: <a href='https://codeforces.com/profile/{new_handle}'>{new_handle}</a>"
            ),
            reply_markup=kb,
            parse_mode="HTML"
        )

    await message.answer("📨 Запрос на изменение handle отправлен администраторам.")

