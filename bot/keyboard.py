import os

from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


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


def topics_keyboard():
    """
    Функция для создания клавиатуры с темами заданий.
    """
    topics = next(os.walk('assignments'))[1]  # Получаем список папок в assignments/
    keyboard_builder = InlineKeyboardBuilder()
    for topic in topics:
        keyboard_builder.button(
            text=topic,
            callback_data=f"topic:{topic}"
        )
    keyboard_builder.adjust(1)
    return keyboard_builder.as_markup()
