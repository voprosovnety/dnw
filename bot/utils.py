import asyncio
import os
import uuid

TEMP_DIR = 'temp_code'


async def check_user_solution(user_code: str, tests_code: str, function_name: str) -> str:
    """
    Evaluates user code by running it inside a Docker container with provided tests.

    Args:
        user_code (str): The code written by the user (should define a function called 'solution')
        tests_code (str): Code that tests the 'solution' function using assertions

    Returns:
        str: Result message, either success or failure with error details.
    """
    run_id = str(uuid.uuid4())
    code_dir = os.path.join(TEMP_DIR, run_id)
    os.makedirs(code_dir, exist_ok=True)

    runner_path = None

    try:
        # Create alias so that test_solution(solution) works
        alias_code = f"solution = {function_name}"

        runner_code = f"""{user_code}

{alias_code}

{tests_code}

if __name__ == '__main__':
    test_solution(solution)
"""

        runner_path = os.path.join(code_dir, 'runner.py')
        with open(runner_path, 'w', encoding='utf-8') as f:
            f.write(runner_code)

        # Define Docker command
        command = [
            'docker', 'run', '--rm',
            '--cpus', '0.5',
            '--memory', '256m',
            '--network', 'none',
            '-v', f'{os.path.abspath(code_dir)}:/home/runner',
            'code-runner'
        ]

        # Run the container
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
        except asyncio.TimeoutError:
            process.kill()
            return "⏱ Execution time exceeded the 5-second limit."

        if process.returncode == 0:
            return "✅ Your solution is correct!"
        else:
            error_message = stderr.decode().strip()
            return f"❌ Test failed:\n{error_message}"

    except Exception as e:
        return f"⚠️ An error occurred while running the code: {e}"
    finally:
        try:
            os.remove(runner_path)
            os.rmdir(code_dir)
        except Exception:
            pass
