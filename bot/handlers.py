import logging
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

router = Router()

logger = logging.getLogger(__name__)


@router.message(Command("start"))
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


@router.message(F.text == "Получить задание")
async def get_assignment(message: Message, state: FSMContext):
    keyboard = topics_keyboard()
    await message.answer("Выберите тему:", reply_markup=keyboard)
    await state.set_state(GetAssignmentStates.waiting_for_topic)


@router.callback_query(GetAssignmentStates.waiting_for_topic, F.data.startswith("topic:"))
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


@router.callback_query(GetAssignmentStates.waiting_for_assignment, F.data.startswith("assignment:"))
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
            f"Задание по теме '{selected_topic}':\n{description}", parse_mode="Markdown"
        )
        await state.set_state(GetAssignmentStates.waiting_for_code)
    else:
        await callback.message.answer("Задание не найдено.", reply_markup=main_menu_keyboard())
        await state.clear()
    await callback.answer()


@router.message(GetAssignmentStates.waiting_for_code, F.content_type.in_(['document', 'text']))
async def receive_code(message: Message, state: FSMContext):
    user_code = ''
    if message.document:
        # Обработка файлов, как и раньше
        document = message.document
        if document.mime_type != 'text/x-python' and not document.file_name.endswith('.py'):
            await message.answer("Пожалуйста, отправьте файл с расширением .py")
            return
        # Проверка размера файла
        if document.file_size > 1024 * 50:  # Ограничение 50 КБ
            await message.answer("Файл слишком большой. Пожалуйста, отправьте файл размером не более 50 КБ.")
            return
        # Получаем объект файла
        file_info = await message.bot.get_file(document.file_id)
        # Задаем путь для сохранения файла
        destination = os.path.join('temp_code', document.file_name)
        # Создаем директорию, если ее нет
        os.makedirs('temp_code', exist_ok=True)
        # Скачиваем файл
        await message.bot.download_file(file_info.file_path, destination)
        # Читаем содержимое файла
        try:
            with open(destination, 'r', encoding='utf-8') as f:
                user_code = f.read()
        except Exception as e:
            logger.exception(f"Ошибка при чтении файла от пользователя {message.from_user.id}: {e}")
            await message.answer(
                "Не удалось прочитать ваш файл. Убедитесь, что файл не поврежден и имеет правильный формат.")
            return
        finally:
            os.remove(destination)
    elif message.content_type == 'text':
        # Проверяем, что текст отформатирован как код
        if not message.entities:
            await message.answer(
                "Пожалуйста, отформатируйте ваш код как 'Monospace' или отправьте файл с расширением .py.")
            return

        code_entities = [entity for entity in message.entities if entity.type in ('pre', 'code')]
        if not code_entities:
            await message.answer(
                "Пожалуйста, отформатируйте ваш код как 'Monospace' или отправьте файл с расширением .py.")
            return

        # Извлекаем код из сообщения
        code_texts = []
        for entity in code_entities:
            offset = entity.offset
            length = entity.length
            code_texts.append(message.text[offset:offset + length])

        user_code = '\n'.join(code_texts)
    else:
        await message.answer(
            "Пожалуйста, отправьте ваш код в виде файла с расширением .py или отформатированного текста.")
        return

    data = await state.get_data()
    current_assignment = data.get("current_assignment")

    if not current_assignment:
        await message.answer("Сначала получите задание командой 'Получить задание'.")
        await state.clear()
        return

    tests_code = current_assignment['tests_code']

    result = await check_user_solution(user_code, tests_code)

    # Экранируем специальные символы и отправляем результат
    import html
    escaped_result = html.escape(result)
    await message.answer(f"<pre>{escaped_result}</pre>", parse_mode='HTML')

    # Обновление прогресса пользователя
    if "Ваше решение верно!" in result:
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


@router.message(GetAssignmentStates.waiting_for_code)
async def unknown_message(message: Message):
    await message.answer("Пожалуйста, отправьте ваш код в виде файла с расширением .py или отформатированного текста.")


@router.message(F.text == "Мой прогресс")
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


@router.message(F.text == "Как отправлять решения?")
async def faq(message: Message):
    await message.answer(
        """
Вы можете отправлять свои решения двумя способами:

1. **Файлом с расширением `.py`**

   - Создайте файл с расширением `.py`, содержащий вашу функцию `solution`.
   - Отправьте этот файл боту.

2. **Текстовым сообщением, отформатированным как код**

   - Вставьте ваш код в текстовое сообщение.
   - Выделите весь код(`Ctrl+A`).
   - Нажмите `Ctrl+Shift+M` (или `Cmd+Shift+M` на Mac) для форматирования текста в Monospace.
   
Пример содержания файла или сообщения:
```python
def solution(a):
    return a
```

**Важно:** Ваш код должен содержать **только** определение функции `solution`. 
Пожалуйста, не добавляйте дополнительный текст или комментарии.

Если у вас возникнут вопросы или проблемы, не стесняйтесь обращаться за помощью!
        """,
        parse_mode="Markdown"
    )


# --- Регистрация всех хендлеров ---

def register_handlers(dp):
    dp.include_router(router)
