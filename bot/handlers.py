from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from bot.keyboard import main_menu_keyboard, topics_keyboard
from bot.utils import check_user_solution
from database.db import Session
from sqlalchemy import select
from database.models import User, Assignment, Progress
from config import ADMIN_ID

user_router = Router()
admin_router = Router()


@user_router.message(F.text == "/start")
async def cmd_start(message: Message):
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
    waiting_for_code = State()


@user_router.message(F.text == "Получить задание")
async def get_assignment(message: Message, state: FSMContext):
    keyboard = await topics_keyboard()
    await message.answer("Выберите тему:", reply_markup=keyboard)
    await state.set_state(GetAssignmentStates.waiting_for_topic)


@user_router.message(GetAssignmentStates.waiting_for_topic)
async def send_assignment(message: Message, state: FSMContext):
    selected_topic = message.text
    async with Session() as session:
        result = await session.execute(
            select(Assignment).where(Assignment.topic == selected_topic)
        )
        assignments = result.scalars().all()
    if assignments:
        assignment = assignments[0]  # Можно выбрать случайное задание
        await state.update_data(current_assignment_id=assignment.id)
        await message.answer(
            f"Задание по теме '{assignment.topic}':\n{assignment.description}\n\nОтправьте ваше решение:",
            reply_markup=main_menu_keyboard()
        )
        await state.set_state(GetAssignmentStates.waiting_for_code)
    else:
        await message.answer("К сожалению, заданий по этой теме нет.", reply_markup=main_menu_keyboard())
        await state.clear()


@user_router.message(GetAssignmentStates.waiting_for_code)
async def receive_code(message: Message, state: FSMContext):
    user_code = message.text
    data = await state.get_data()
    assignment_id = data.get("current_assignment_id")

    if not assignment_id:
        await message.answer("Сначала получите задание командой 'Получить задание'.")
        await state.clear()
        return

    async with Session() as session:
        assignment = await session.get(Assignment, assignment_id)
        tests_code = assignment.tests_code

    result = await check_user_solution(user_code, tests_code)
    await message.answer(result)
    # Обновление прогресса пользователя
    if "✅ Ваше решение верно!" in result:
        async with Session() as session:
            progress = Progress(
                user_id=message.from_user.id,
                assignment_id=assignment_id,
                is_completed=True
            )
            session.add(progress)
            await session.commit()
    await state.clear()


@user_router.message(F.text == "Мой прогресс")
async def show_progress(message: Message):
    async with Session() as session:
        result = await session.execute(
            select(Assignment.topic, Assignment.description)
            .join(Progress, Assignment.id == Progress.assignment_id)
            .where(Progress.user_id == message.from_user.id, Progress.is_completed == True)
        )
        completed_assignments = result.fetchall()
    if completed_assignments:
        response = "Вы успешно выполнили следующие задания:\n\n"
        for topic, description in completed_assignments:
            response += f"Тема: {topic}\nЗадание: {description}\n\n"
    else:
        response = "Вы ещё не выполнили ни одного задания."
    await message.answer(response)


class AddAssignmentStates(StatesGroup):
    waiting_for_topic = State()
    waiting_for_description = State()
    waiting_for_tests = State()


@admin_router.message(F.text == "/add_assignment")
async def cmd_add_assignment(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для этой команды.")
        return
    await message.answer("Введите тему задания:")
    await state.set_state(AddAssignmentStates.waiting_for_topic)


@admin_router.message(AddAssignmentStates.waiting_for_topic)
async def assignment_topic_entered(message: Message, state: FSMContext):
    await state.update_data(topic=message.text)
    await message.answer("Введите описание задания:")
    await state.set_state(AddAssignmentStates.waiting_for_description)


@admin_router.message(AddAssignmentStates.waiting_for_description)
async def assignment_description_entered(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer(
        "Отправьте тесты для задания (в виде кода). Функция тестирования должна называться `test_solution`:")
    await state.set_state(AddAssignmentStates.waiting_for_tests)


@admin_router.message(AddAssignmentStates.waiting_for_tests)
async def assignment_tests_entered(message: Message, state: FSMContext):
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


def register_handlers(dp):
    dp.include_router(user_router)
    dp.include_router(admin_router)
