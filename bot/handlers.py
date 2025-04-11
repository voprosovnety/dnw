import logging
import os
import html

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

router = Router()

logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Handler for /start command.
    Registers a user in the database if not already registered and shows the main menu.
    """
    async with Session() as session:
        user = await session.get(User, message.from_user.id)
        if not user:
            user = User(telegram_id=message.from_user.id)
            session.add(user)
            await session.commit()
    await message.answer(
        "Welcome! Choose an action:",
        reply_markup=main_menu_keyboard()
    )


class GetAssignmentStates(StatesGroup):
    """FSM states for assignment flow"""
    waiting_for_topic = State()
    waiting_for_assignment = State()
    waiting_for_code = State()


@router.message(F.text == "Get Assignment")
async def get_assignment(message: Message, state: FSMContext):
    """
    Presents the user with a list of available topics to choose from.
    """
    keyboard = topics_keyboard()
    await message.answer("Choose a topic:", reply_markup=keyboard)
    await state.set_state(GetAssignmentStates.waiting_for_topic)


@router.callback_query(GetAssignmentStates.waiting_for_topic, F.data.startswith("topic:"))
async def process_topic_selection(callback: CallbackQuery, state: FSMContext):
    """
    After a topic is selected, list all assignments inside that topic.
    """
    selected_topic = callback.data.split(":", 1)[1]
    assignments_path = os.path.join('assignments', selected_topic)
    assignments = next(os.walk(assignments_path))[1]  # Get list of assignment folders

    if assignments:
        keyboard = InlineKeyboardBuilder()
        for assignment in assignments:
            keyboard.button(
                text=f"{assignment}",
                callback_data=f"assignment:{selected_topic}:{assignment}"
            )
        keyboard.adjust(1)
        await callback.message.edit_text("Choose an assignment:", reply_markup=keyboard.as_markup())
        await state.set_state(GetAssignmentStates.waiting_for_assignment)
        await state.update_data(selected_topic=selected_topic)
    else:
        await callback.message.edit_text("No assignments available for this topic.")
        await callback.message.answer(
            "You can return to the main menu:",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
    await callback.answer()


@router.callback_query(GetAssignmentStates.waiting_for_assignment, F.data.startswith("assignment:"))
async def send_assignment(callback: CallbackQuery, state: FSMContext):
    """
    Sends the description of the selected assignment to the user.
    Also prepares test code for validation.
    """
    _, selected_topic, assignment_name = callback.data.split(":", 2)
    assignment_path = os.path.join('assignments', selected_topic, assignment_name)
    description_file = os.path.join(assignment_path, 'description.txt')
    tests_file = os.path.join(assignment_path, 'tests.py')

    if os.path.exists(description_file) and os.path.exists(tests_file):
        with open(description_file, 'r', encoding='utf-8') as f:
            description = html.escape(f.read())

        with open(tests_file, 'r', encoding='utf-8') as f:
            tests_code = f.read()

        await state.update_data(current_assignment={
            'topic': selected_topic,
            'name': assignment_name,
            'tests_code': tests_code,
            'function_name': assignment_name
        })
        await callback.message.edit_text(
            f"<b>Assignment - {selected_topic}:</b>\n\n<pre>{description}</pre>", parse_mode="HTML"
        )
        await callback.message.answer(
            "Send your solution as a .py file or paste it as formatted code (monospace)."
        )
        await state.set_state(GetAssignmentStates.waiting_for_code)
    else:
        await callback.message.answer("Assignment not found.", reply_markup=main_menu_keyboard())
        await state.clear()
    await callback.answer()


@router.message(GetAssignmentStates.waiting_for_code, F.content_type.in_(['document', 'text']))
async def receive_code(message: Message, state: FSMContext):
    """
    Receives the user's code either as a .py file or formatted text.
    Sends result of test evaluation.
    """
    user_code = ''

    if message.document:
        document = message.document
        if document.mime_type != 'text/x-python' and not document.file_name.endswith('.py'):
            await message.answer("Please send a file with .py extension.")
            return

        if document.file_size > 1024 * 50:
            await message.answer("The file is too large. Please send a file smaller than 50KB.")
            return

        file_info = await message.bot.get_file(document.file_id)
        destination = os.path.join('temp_code', document.file_name)
        os.makedirs('temp_code', exist_ok=True)

        await message.bot.download_file(file_info.file_path, destination)

        try:
            with open(destination, 'r', encoding='utf-8') as f:
                user_code = f.read()
        except Exception as e:
            logger.exception(f"Error reading file from user {message.from_user.id}: {e}")
            await message.answer("Could not read your file. Make sure it is a valid Python script.")
            return
        finally:
            os.remove(destination)

    elif message.content_type == 'text':
        if not message.entities:
            await message.answer("Please format your code as monospace or send a .py file.")
            return

        code_entities = [e for e in message.entities if e.type in ('pre', 'code')]
        if not code_entities:
            await message.answer("Please format your code as monospace or send a .py file.")
            return

        code_texts = []
        for entity in code_entities:
            offset = entity.offset
            length = entity.length
            code_texts.append(message.text[offset:offset + length])

        user_code = '\n'.join(code_texts)

    else:
        await message.answer("Unsupported content type. Please send .py file or formatted code.")
        return

    data = await state.get_data()
    current_assignment = data.get("current_assignment")

    if not current_assignment:
        await message.answer("You need to select an assignment first.")
        await state.clear()
        return

    tests_code = current_assignment['tests_code']
    function_name = current_assignment['function_name']

    result = await check_user_solution(user_code, tests_code, function_name)

    escaped_result = html.escape(result)
    await message.answer(f"<pre>{escaped_result}</pre>", parse_mode='HTML')

    if "correct" in result.lower() or "success" in result.lower():
        async with Session() as session:
            exists_query = select(Progress).where(
                Progress.user_id == message.from_user.id,
                Progress.topic.is_(current_assignment['topic']),
                Progress.assignment_name.is_(current_assignment['name']),
                Progress.is_completed.is_(True)
            )
            result = await session.execute(exists_query)
            existing = result.scalar_one_or_none()

            if not existing:
                progress = Progress(
                    user_id=message.from_user.id,
                    topic=current_assignment['topic'],
                    assignment_name=current_assignment['name'],
                    is_completed=True
                )
                session.add(progress)
                await session.commit()
        await state.clear()
    else:
        await message.answer("You can try submitting the corrected code again.")


@router.message(GetAssignmentStates.waiting_for_code)
async def unknown_message(message: Message):
    await message.answer("Please send a .py file or formatted code.")


@router.message(F.text == "My Progress")
async def show_progress(message: Message):
    """
    Displays completed assignments to the user.
    """
    async with Session() as session:
        result = await session.execute(
            select(Progress.topic, Progress.assignment_name)
            .where(Progress.user_id == message.from_user.id, Progress.is_completed.is_(True))
        )
        completed = result.fetchall()

    if completed:
        response = "You have completed the following assignments:\n\n"
        for topic, name in completed:
            response += f"Topic: {topic}\nAssignment: {name}\n\n"
    else:
        response = "You haven't completed any assignments yet."

    await message.answer(response)


@router.message(F.text == "How to submit code?")
async def faq(message: Message):
    """
    Instructions for submitting code.
    """
    await message.answer(
        """
You can submit your solution in two ways:

1. <b>By sending a .py file</b>
   - Create a .py file with your function. The function <b>name must match the assignment name</b>.
   - Example: For assignment <code>is_prime</code>, your function must be named <code>is_prime</code>.
   - Send this file to the bot.

2. <b>By sending formatted text</b>
   - Paste your code as a message
   - Select all the code and format it as monospace (Ctrl+Shift+M)

<b>Example:</b>
<pre>
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, n):
        if n % i == 0:
            return False
    return True
</pre>

<b>Important:</b>
- Do <b>not</b> include comments or additional text
- The function name must be <b>exactly</b> as stated in the assignment
        """,
        parse_mode="HTML"
    )


def register_handlers(dp):
    dp.include_router(router)
