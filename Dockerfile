# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости для веб-приложения
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY src/ ./src/
COPY models/ ./models/
COPY templates/ ./templates/
COPY static/ ./static/

# Открываем порт для FastAPI
EXPOSE 8008

# Запускаем веб-приложение
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8008"]