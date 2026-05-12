# Dockerfile — образ для FastAPI backend
# Базується на офіційному Python 3.11 slim (легка версія без зайвого)

FROM python:3.11-slim

# Робоча директорія всередині контейнера
WORKDIR /code

# Спочатку копіюємо тільки requirements.txt і ставимо залежності.
# Docker кешує цей шар — поки requirements не змінився, pip install не запускається.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Потім копіюємо код. Якщо код змінився, а залежності ні —
# Docker перебілдить тільки цей шар (швидко).
COPY ./app ./app

# Команда, яка стартує сервер при запуску контейнера.
# --reload: автоперезавантаження при зміні файлів (тільки для dev!)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]