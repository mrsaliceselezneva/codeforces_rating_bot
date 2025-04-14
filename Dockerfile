FROM python:3.10-slim

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Обновление сертификатов
RUN python -m pip install --upgrade pip certifi

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники
COPY . .

# Запускаем main.py из новой папки
CMD ["python", "app/main.py"]
