#!/bin/sh
set -e

echo "Применяем миграции..."
alembic upgrade head

echo "Проверяем и создаем сиды..."
python seed.py

echo "Запускаем приложение..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload