import asyncio
import os
import uuid

TEMP_DIR = 'temp_code'


async def check_user_solution(user_code, tests_code):
    # Создаем уникальный идентификатор для каждого запуска
    run_id = str(uuid.uuid4())
    code_dir = os.path.join(TEMP_DIR, run_id)
    os.makedirs(code_dir, exist_ok=True)

    runner_path = None

    try:
        # Создаем файл runner.py с кодом пользователя и тестами
        runner_code = f"""
{user_code}

{tests_code}

if __name__ == '__main__':
    test_solution(solution)
"""
        runner_path = os.path.join(code_dir, 'runner.py')
        with open(runner_path, 'w', encoding='utf-8') as f:
            f.write(runner_code)

        # Команда для запуска Docker-контейнера
        command = [
            'docker', 'run', '--rm',
            '--cpus', '0.5',  # Ограничение CPU
            '--memory', '256m',  # Ограничение памяти
            '--network', 'none',  # Отключаем сеть
            '-v', f'{os.path.abspath(code_dir)}:/home/runner',
            'code-runner'
        ]

        # Запускаем контейнер и ждем завершения
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
        except asyncio.TimeoutError:
            process.kill()
            return "❌ Превышено время выполнения (5 секунд)."

        if process.returncode == 0:
            return "✅ Ваше решение верно!"
        else:
            error_message = stderr.decode().strip()
            return f"❌ Тест не пройден:\n{error_message}"

    except Exception as e:
        return f"⚠️ Ошибка при выполнении кода: {e}"
    finally:
        # Удаляем временные файлы
        try:
            os.remove(runner_path)
            os.rmdir(code_dir)
        except Exception:
            pass
