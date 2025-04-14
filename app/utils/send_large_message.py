from aiogram import Bot

MAX_MESSAGE_LENGTH = 4000


async def send_large_message(bot: Bot, chat_id: int, text: str, **kwargs):
    lines = text.split("\n")
    chunk = ""

    for line in lines:
        # Проверка, не превысит ли добавление строки лимит
        if len(chunk) + len(line) + 1 < MAX_MESSAGE_LENGTH:
            chunk += line + "\n"
        else:
            await bot.send_message(chat_id, chunk.strip(), **kwargs)
            chunk = line + "\n"

    if chunk:
        await bot.send_message(chat_id, chunk.strip(), **kwargs)
