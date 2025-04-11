FROM python:3.12-slim

# Create non-root user for safer execution
RUN useradd -ms /bin/bash runner

USER runner
WORKDIR /home/runner

# Prevent Python from writing .pyc files and buffering output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default command to run code
CMD ["python", "runner.py"]
