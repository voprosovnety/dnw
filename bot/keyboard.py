import os

from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def main_menu_keyboard():
    """
    Creates the main menu keyboard.
    Uses ReplyKeyboardBuilder for better layout control.
    """
    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.button(text="Get Assignment")
    keyboard_builder.button(text="My Progress")
    keyboard_builder.button(text="How to submit code?")
    keyboard_builder.adjust(2)
    return keyboard_builder.as_markup(resize_keyboard=True)


def topics_keyboard():
    """
    Creates an inline keyboard based on folders inside the 'assignments' directory.
    Each folder represents a topic.
    """
    topics = next(os.walk('assignments'))[1]
    keyboard_builder = InlineKeyboardBuilder()
    for topic in topics:
        keyboard_builder.button(
            text=topic,
            callback_data=f"topic:{topic}"
        )
    keyboard_builder.adjust(1)
    return keyboard_builder.as_markup()
