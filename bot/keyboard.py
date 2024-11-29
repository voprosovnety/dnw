from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from database.db import Session
from database.models import Assignment
from sqlalchemy import select


def main_menu_keyboard():
    """
    Функция для создания клавиатуры главного меню.
    Использует ReplyKeyboardBuilder для удобства добавления новых кнопок.
    """
    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.button(text="Получить задание")
    keyboard_builder.button(text="Мой прогресс")
    keyboard_builder.adjust(2)  # Располагаем кнопки в один ряд (2 кнопки в строке)
    return keyboard_builder.as_markup(resize_keyboard=True)


async def topics_keyboard():
    """
    Асинхронная функция для создания клавиатуры с темами заданий.
    Использует InlineKeyboardMarkup для динамических кнопок.
    """
    async with Session() as session:
        result = await session.execute(select(Assignment.topic).distinct())
        topics = [row[0] for row in result.fetchall()]

    keyboard_builder = InlineKeyboardBuilder()
    for topic in topics:
        keyboard_builder.button(
            text=topic,
            callback_data=f"topic:{topic}"
        )
    keyboard_builder.adjust(1)  # Каждая кнопка на отдельной строке
    return keyboard_builder.as_markup()
