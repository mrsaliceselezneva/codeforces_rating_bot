from aiogram import Bot

MAX_MESSAGE_LENGTH = 4000


async def send_large_message(bot: Bot, chat_id: int, text: str, **kwargs):
    for i in range(0, len(text), MAX_MESSAGE_LENGTH):
        await bot.send_message(chat_id, text[i:i + MAX_MESSAGE_LENGTH], **kwargs)
