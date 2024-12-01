import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from bot.handlers import register_handlers
from database.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    await init_db()

    register_handlers(dp)

    # Запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
