import os

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.keyboard import main_menu_keyboard, topics_keyboard
from bot.utils import check_user_solution
from database.db import Session
from sqlalchemy import select
from database.models import User, Progress
from config import ADMIN_ID

# Инициализация роутеров
user_router = Router()
admin_router = Router()


# --- Хендлеры для пользователей ---

@user_router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Обработчик команды /start.
    Регистрирует пользователя, если его нет в базе, и выводит главное меню.
    """
    async with Session() as session:
        user = await session.get(User, message.from_user.id)
        if not user:
            user = User(telegram_id=message.from_user.id)
            session.add(user)
            await session.commit()
    await message.answer(
        "Добро пожаловать! Выберите действие:",
        reply_markup=main_menu_keyboard()
    )


class GetAssignmentStates(StatesGroup):
    waiting_for_topic = State()
    waiting_for_assignment = State()
    waiting_for_code = State()


@user_router.message(F.text == "Получить задание")
async def get_assignment(message: Message, state: FSMContext):
    """
    Обработчик нажатия на кнопку "Получить задание".
    Показывает пользователю список доступных тем.
    """
    keyboard = topics_keyboard()
    await message.answer("Выберите тему:", reply_markup=keyboard)
    await state.set_state(GetAssignmentStates.waiting_for_topic)


@user_router.callback_query(GetAssignmentStates.waiting_for_topic, F.data.startswith("topic:"))
async def process_topic_selection(callback: CallbackQuery, state: FSMContext):
    selected_topic = callback.data.split(":", 1)[1]
    assignments_path = os.path.join('assignments', selected_topic)
    assignments = next(os.walk(assignments_path))[1]  # Получаем список папок заданий в теме

    if assignments:
        keyboard = InlineKeyboardBuilder()
        for assignment in assignments:
            keyboard.button(
                text=f"{assignment}",
                callback_data=f"assignment:{selected_topic}:{assignment}"
            )
        keyboard.adjust(1)
        await callback.message.edit_text("Выберите задание:", reply_markup=keyboard.as_markup())
        await state.set_state(GetAssignmentStates.waiting_for_assignment)
        await state.update_data(selected_topic=selected_topic)
    else:
        await callback.message.edit_text("К сожалению, заданий по этой теме нет.")
        await callback.message.answer(
            "Вы можете воспользоваться главным меню:",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
    await callback.answer()


@user_router.callback_query(GetAssignmentStates.waiting_for_assignment, F.data.startswith("assignment:"))
async def send_assignment(callback: CallbackQuery, state: FSMContext):
    _, selected_topic, assignment_name = callback.data.split(":", 2)
    assignment_path = os.path.join('assignments', selected_topic, assignment_name)
    description_file = os.path.join(assignment_path, 'description.txt')
    tests_file = os.path.join(assignment_path, 'tests.py')

    if os.path.exists(description_file) and os.path.exists(tests_file):
        # Читаем описание задания
        with open(description_file, 'r', encoding='utf-8') as f:
            description = f.read()

        # Читаем тесты
        with open(tests_file, 'r', encoding='utf-8') as f:
            tests_code = f.read()

        await state.update_data(current_assignment={
            'topic': selected_topic,
            'name': assignment_name,
            'tests_code': tests_code
        })
        await callback.message.edit_text(
            f"Задание по теме '{selected_topic}':\n{description}\n\nОтправьте ваше решение:"
        )
        await callback.message.answer(
            "Вы можете воспользоваться главным меню:",
            reply_markup=main_menu_keyboard()
        )
        await state.set_state(GetAssignmentStates.waiting_for_code)
    else:
        await callback.message.answer("Задание не найдено.", reply_markup=main_menu_keyboard())
        await state.clear()
    await callback.answer()


@user_router.message(GetAssignmentStates.waiting_for_code)
async def receive_code(message: Message, state: FSMContext):
    user_code = message.text
    data = await state.get_data()
    current_assignment = data.get("current_assignment")

    if not current_assignment:
        await message.answer("Сначала получите задание командой 'Получить задание'.")
        await state.clear()
        return

    tests_code = current_assignment['tests_code']

    result = await check_user_solution(user_code, tests_code)
    await message.answer(result)
    if "Ваше решение верно!" in result:
        data = await state.get_data()
        current_assignment = data.get("current_assignment")
        async with Session() as session:
            progress = Progress(
                user_id=message.from_user.id,
                topic=current_assignment['topic'],
                assignment_name=current_assignment['name'],
                is_completed=True
            )
            session.add(progress)
            await session.commit()
    await state.clear()


@user_router.message(F.text == "Мой прогресс")
async def show_progress(message: Message):
    async with Session() as session:
        result = await session.execute(
            select(Progress.topic, Progress.assignment_name)
            .where(Progress.user_id == message.from_user.id, Progress.is_completed.is_(True))
        )
        completed_assignments = result.fetchall()
    if completed_assignments:
        response = "Вы успешно выполнили следующие задания:\n\n"
        for topic, assignment_name in completed_assignments:
            response += f"Тема: {topic}\nЗадание: {assignment_name}\n\n"
    else:
        response = "Вы ещё не выполнили ни одного задания."
    await message.answer(response)


# --- Хендлеры для администратора ---

class AddAssignmentStates(StatesGroup):
    waiting_for_topic = State()
    waiting_for_description = State()
    waiting_for_tests = State()


@admin_router.message(Command("add_assignment"))
async def cmd_add_assignment(message: Message, state: FSMContext):
    """
    Обработчик команды /add_assignment.
    Начинает процесс добавления нового задания.
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для этой команды.")
        return
    await message.answer("Введите тему задания:")
    await state.set_state(AddAssignmentStates.waiting_for_topic)


@admin_router.message(AddAssignmentStates.waiting_for_topic)
async def assignment_topic_entered(message: Message, state: FSMContext):
    """
    Обрабатывает ввод темы задания.
    """
    await state.update_data(topic=message.text)
    await message.answer("Введите описание задания:")
    await state.set_state(AddAssignmentStates.waiting_for_description)


@admin_router.message(AddAssignmentStates.waiting_for_description)
async def assignment_description_entered(message: Message, state: FSMContext):
    """
    Обрабатывает ввод описания задания.
    """
    await state.update_data(description=message.text)
    await message.answer(
        "Отправьте тесты для задания (в виде кода).\n"
        "Функция тестирования должна называться `test_solution`:"
    )
    await state.set_state(AddAssignmentStates.waiting_for_tests)


@admin_router.message(AddAssignmentStates.waiting_for_tests)
async def assignment_tests_entered(message: Message, state: FSMContext):
    """
    Обрабатывает ввод тестов для задания.
    Сохраняет задание в базе данных.
    """
    data = await state.get_data()
    topic = data['topic']
    description = data['description']
    tests_code = message.text

    # Сохраняем задание в базу данных
    async with Session() as session:
        assignment = Assignment(
            topic=topic,
            description=description,
            tests_code=tests_code
        )
        session.add(assignment)
        await session.commit()
    await message.answer("Задание успешно добавлено!")
    await state.clear()


# --- Регистрация всех хендлеров ---

def register_handlers(dp):
    dp.include_router(user_router)
    dp.include_router(admin_router)
