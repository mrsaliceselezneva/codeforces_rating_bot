from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from app.db.database import get_db
from app.services.codeforces import get_user_info
from app.utils.rank_translation import translate_rank
from app.utils.rank_utils import compare_ranks
from app.utils.send_large_message import send_large_message

load_dotenv()

ADMINS = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()]
router = Router()


@router.message(Command("add_user"))
async def add_user(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    lines = message.text.strip().split("\n")[1:]  # пропускаем первую строку (/add_user)
    if not lines:
        await message.answer("⚠️ Введите список пользователей в формате:\n"
                             "/add_user\n"
                             "handle1 Имя1 Фамилия1\n"
                             "handle2 Имя2 Фамилия2")
        return

    added = []
    skipped = []

    for line in lines:
        parts = line.strip().split(maxsplit=2)
        if len(parts) != 3:
            skipped.append(f"❌ {line} (неверный формат)")
            continue

        handle, first_name, last_name = parts

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE handle = ?", (handle,))
            if cursor.fetchone():
                skipped.append(f"⚠️ {handle} уже есть")
                continue

            cursor.execute("""
                INSERT INTO users (handle, first_name, last_name, is_admin)
                VALUES (?, ?, ?, 0)
            """, (handle, first_name, last_name))
            conn.commit()
            added.append(f"✅ {handle}")

    lines = added + skipped
    await message.answer("\n".join(lines))


@router.message(Command("remove_user"))
async def remove_user(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    args = message.text.strip().split()[1:]
    if len(args) != 1:
        await message.answer("Используйте: /remove_user <handle>")
        return

    handle = args[0]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, last_name FROM users WHERE handle = ?", (handle,))
        row = cursor.fetchone()

        if not row:
            await message.answer(f"❌ Пользователь с handle <code>{handle}</code> не найден.", parse_mode="HTML")
            return

        cursor.execute("DELETE FROM users WHERE handle = ?", (handle,))
        conn.commit()

    await message.answer(f"🗑️ Пользователь <code>{handle}</code> удалён.", parse_mode="HTML")


@router.message(Command("update_ratings"))
async def update_ratings(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    interval = int(os.getenv("RATING_UPDATE_INTERVAL_MINUTES", "60"))
    now = datetime.utcnow()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = 'last_rating_update'")
        row = cursor.fetchone()
        if row and row[0]:
            last_update_time = datetime.fromisoformat(row[0])
            if now - last_update_time < timedelta(minutes=interval):
                remaining = timedelta(minutes=interval) - (now - last_update_time)
                mins = int(remaining.total_seconds() // 60)
                await message.answer(
                    f"⚠️ Обновление рейтингов доступно раз в {interval} минут.\n"
                    f"Подождите ещё {mins} мин."
                )
                return

    await message.answer("🔄 Обновляю рейтинги...")

    updates = []
    errors = []

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT telegram_id, first_name, last_name, handle, rank, rating, top_rank
            FROM users
            WHERE handle IS NOT NULL
        """)
        users = cursor.fetchall()

    for telegram_id, first_name, last_name, handle, old_rank, old_rating, top_rank in users:
        try:
            info = await get_user_info(handle)
            new_rank = info.get("rank", "unrated")
            new_rating = info.get("rating", 0)

            is_new_rank = new_rank != old_rank
            is_rating_increased = new_rating > (old_rating or 0)

            rank_translation = translate_rank(new_rank)
            link = f"<a href='https://codeforces.com/profile/{handle}'>{last_name} {first_name}</a>"

            emoji = "✅"
            comment = f"был {old_rating}, стал {new_rating}"

            if top_rank in (None, "", "unrated") and compare_ranks(new_rank, top_rank):
                emoji = "🏆"
                comment = f"повысилось звание до {rank_translation} (впервые)"
                top_rank_to_set = new_rank
            elif is_new_rank:
                emoji = "✅"
                comment = f"изменилось звание на {rank_translation}"
                top_rank_to_set = top_rank
            elif is_rating_increased:
                top_rank_to_set = top_rank
            else:
                top_rank_to_set = top_rank

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users
                    SET rank = ?, rating = ?, last_updated = ?, top_rank = ?
                    WHERE handle = ?
                """, (new_rank, new_rating, now.isoformat(), top_rank_to_set, handle))
                conn.commit()

            updates.append(f"{emoji} {link} — {comment}")

        except Exception as e:
            emoji = "❌"
            link = f"<a href='https://codeforces.com/profile/{handle}'>{last_name} {first_name}</a>"
            errors.append(f"{emoji} {link} — ошибка: {e}")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO metadata (key, value) VALUES ('last_rating_update', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (now.isoformat(),))
        conn.commit()

    result = "\n".join(updates + errors) or "Никаких изменений не обнаружено."
    await send_large_message(message.bot, message.chat.id, result, parse_mode="HTML")


@router.message(Command("list_users"))
async def list_users(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT first_name, last_name, handle
            FROM users
            ORDER BY last_name, first_name
        """)
        rows = cursor.fetchall()

    if not rows:
        await message.answer("❌ Зарегистрированных пользователей нет.")
        return

    lines = ["👥 Зарегистрированные пользователи:"]
    for first_name, last_name, handle in rows:
        lines.append(f"• {last_name} {first_name} — <code>{handle}</code>")

    text = "\n".join(lines)
    await send_large_message(message.bot, message.chat.id, text, parse_mode="HTML")


@router.message(Command("update_handle"))
async def update_handle(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    args = message.text.strip().split()[1:]
    if len(args) != 2:
        await message.answer("Используйте: /update_handle <старый_handle> <новый_handle>")
        return

    old_handle, new_handle = args

    with get_db() as conn:
        cursor = conn.cursor()

        # проверим, существует ли old_handle
        cursor.execute("SELECT 1 FROM users WHERE handle = ?", (old_handle,))
        if not cursor.fetchone():
            await message.answer(f"❌ Пользователь с handle <code>{old_handle}</code> не найден.", parse_mode="HTML")
            return

        # проверим, что новый handle ещё не занят
        cursor.execute("SELECT 1 FROM users WHERE handle = ?", (new_handle,))
        if cursor.fetchone():
            await message.answer(f"⚠️ Handle <code>{new_handle}</code> уже занят.", parse_mode="HTML")
            return

        cursor.execute(
            "UPDATE users SET handle = ? WHERE handle = ?",
            (new_handle, old_handle)
        )
        conn.commit()

    await message.answer(f"✅ Handle успешно обновлён:\n<code>{old_handle}</code> → <code>{new_handle}</code>", parse_mode="HTML")


@router.callback_query(F.data.startswith("approve:"))
async def handle_approve(callback: CallbackQuery):
    try:
        _, telegram_id_str, handle = callback.data.split(":")
        telegram_id = int(telegram_id_str)
    except ValueError:
        await callback.answer("Неверный формат callback.", show_alert=True)
        return

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, last_name, telegram_id FROM users WHERE handle = ?", (handle,))
        row = cursor.fetchone()

        if not row:
            await callback.answer("❌ Handle не найден в базе.", show_alert=True)
            return

        first_name, last_name, existing_telegram_id = row

        if existing_telegram_id:
            await callback.answer("⚠️ Пользователь уже подтверждён.", show_alert=True)
            return

        # Привязываем telegram_id
        cursor.execute("UPDATE users SET telegram_id = ? WHERE handle = ?", (telegram_id, handle))
        conn.commit()

    # сообщение админу
    await callback.message.edit_text(
        f"✅ Пользователь <b>{last_name} {first_name}</b> с handle <code>{handle}</code> успешно подтверждён.",
        parse_mode="HTML"
    )

    # сообщение пользователю
    try:
        await callback.bot.send_message(
            telegram_id,
            f"🎉 Ваша заявка одобрена!\n"
            f"Теперь вы будете получать уведомления о Div2/3/4 раундах Codeforces."
        )
    except Exception:
        await callback.message.answer("⚠️ Не удалось отправить сообщение пользователю.")

    await callback.answer()


@router.callback_query(F.data.startswith("confirm_handle_update:"))
async def confirm_handle_update(callback: CallbackQuery):
    try:
        _, telegram_id_str, old_handle, new_handle = callback.data.split(":")
        telegram_id = int(telegram_id_str)
    except ValueError:
        await callback.answer("Неверный формат callback.", show_alert=True)
        return

    with get_db() as conn:
        cursor = conn.cursor()

        # Проверим, что пользователь с таким telegram_id и старым handle существует
        cursor.execute("""
            SELECT first_name, last_name FROM users 
            WHERE telegram_id = ? AND handle = ?
        """, (telegram_id, old_handle))
        row = cursor.fetchone()

        if not row:
            await callback.answer("Пользователь не найден или handle не совпадает.", show_alert=True)
            return

        first_name, last_name = row

        # Обновляем handle
        cursor.execute("""
            UPDATE users SET handle = ? WHERE telegram_id = ?
        """, (new_handle, telegram_id))
        conn.commit()

    # Уведомление админу
    await callback.message.edit_text(
        f"✅ Handle пользователя <b>{last_name} {first_name}</b> обновлён:\n"
        f"<code>{old_handle}</code> → <code>{new_handle}</code>",
        parse_mode="HTML"
    )

    # Уведомление пользователю
    try:
        await callback.bot.send_message(
            telegram_id,
            f"✅ Ваш handle обновлён:\n"
            f"<code>{old_handle}</code> → <code>{new_handle}</code>"
        )
    except Exception:
        await callback.message.answer("⚠️ Не удалось отправить сообщение пользователю.")

    await callback.answer()
