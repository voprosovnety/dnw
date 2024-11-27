import contextlib
from io import StringIO


async def check_user_solution(user_code, tests_code):
    try:
        # Создаем локальный словарь для выполнения кода пользователя
        local_vars = {}

        # Ограничиваем функции, доступные при выполнении кода
        allowed_builtins = {'__builtins__': {}}

        # Выполняем код пользователя
        exec(user_code, allowed_builtins, local_vars)

        # Проверяем, что функция `solution` определена
        if 'solution' not in local_vars:
            return "Ошибка: Функция `solution` не найдена."

        user_function = local_vars['solution']

        # Выполняем код тестов
        exec(tests_code, allowed_builtins, local_vars)

        # Проверяем, что функция тестирования `test_solution` определена
        if 'test_solution' not in local_vars:
            return "Ошибка: Функция тестирования `test_solution` не найдена."

        test_function = local_vars['test_solution']

        # Перенаправляем stdout, чтобы поймать возможные принты
        with contextlib.redirect_stdout(StringIO()):
            test_function(user_function)

        return "✅ Ваше решение верно!"

    except AssertionError as e:
        return f"❌ Тест не пройден: {e}"
    except Exception as e:
        return f"⚠️ Ошибка при выполнении кода: {e}"
