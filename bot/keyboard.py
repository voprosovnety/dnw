from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database.db import Session
from database.models import Assignment
from sqlalchemy import select


def main_menu_keyboard():
    keyboard = [
        [KeyboardButton(text="Получить задание")],
        [KeyboardButton(text="Мой прогресс")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


async def topics_keyboard():
    async with Session() as session:
        result = await session.execute(
            select(Assignment.topic).distinct()
        )
        topics = [row[0] for row in result.fetchall()]
    keyboard = [[KeyboardButton(text=topic)] for topic in topics]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
