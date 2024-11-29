FROM python:3.12-slim

# Устанавливаем дополнительные пакеты, если необходимо
# RUN apt-get update && apt-get install -y ...

# Создаем пользователя без прав root
RUN useradd -ms /bin/bash runner

USER runner
WORKDIR /home/runner

# Копируем файлы, если необходимо
# COPY requirements.txt .
# RUN pip install -r requirements.txt

CMD ["python", "runner.py"]
