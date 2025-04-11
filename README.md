# Telegram Code Checker Bot

A Telegram bot that delivers coding challenges and evaluates user-submitted Python solutions inside a secure Docker
environment.

## Features

- Choose assignments by topic via Telegram UI
- Submit code via `.py` file or formatted text
- Secure execution in Docker sandbox
- Tracks user progress (which tasks are completed)
- Built with [Aiogram 3](https://docs.aiogram.dev/), SQLite, and SQLAlchemy

---

## How it works

1. User chooses a topic and assignment via Telegram
2. The bot sends the description from `/assignments/<topic>/<name>/description.txt`
3. The user submits a function with the name matching the assignment folder
4. The bot runs the code with test cases via Docker and returns the result

---

## Setup

### Requirements

- Python 3.11+
- Docker installed and running

### Install dependencies

```bash
pip install -r requirements.txt
```

### Environment variables

Create a `.env` file with:

```
BOT_TOKEN=your_bot_token
```

### Run the bot

```bash
python main.py
```

---

## Assignment format

Each task should be placed in `assignments/<topic>/<name>` folder with:

- `description.txt`: task description (HTML-safe text)
- `tests.py`: test cases. Should define a `test_solution(fn)` function.

Example:

```python
# tests.py

def test_solution(fn):
    assert fn(2) is True
    assert fn(4) is False
```

---

## Project structure

```
project/
│
├── bot/
│   ├── handlers.py
│   ├── keyboard.py
│   └── utils.py
│
├── database/
│   ├── db.py
│   └── models.py
│
├── assignments/
│   └── ...
│
├── Dockerfile
├── main.py
├── .env
└── requirements.txt
```

---

## License

MIT

---

## Author

Made by [@voprosovnety](https://github.com/voprosovnety). You can’t afford him, but this is open source anyway.
