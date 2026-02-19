# Сервис заявок на ремонт

Система для управления заявками на ремонт с разделением ролей (диспетчер и мастера). Проект контейнеризирован с использованием Docker и готов к запуску одной командой + 48 тестов проверки системы.

## Быстрый старт

### Требования для запуска в Docker
- Docker (версия 20.10+)
- Docker Compose (версия 2.0+)
- Git

### Установка и запуск

1. Клонировать репозиторий
   git clone git@github.com:Maksimilyan25/test_for_vibe.git

2. Перейти в директорию проекта
   cd test_for_vibe

3. Скопировать пример файла окружения
   cp .env.example .env

   PostgreSQL (укажите свои значения)
   POSTGRES_USER=your_db_user
   POSTGRES_PASSWORD=your_db_password
   POSTGRES_DB=your_db_name

   Backend
   SECRET_KEY=your_secret_key_here
   ACCESS_TOKEN_EXPIRE_MINUTES=30

4. Сгенерировать секретный ключ для backend
   openssl rand -hex 32
   
   Полученный ключ вставьте в файл .env вместо your_secret_key_here

5. Запустить контейнеры
   docker-compose up --build

При первом запуске автоматически:
- Создаются и запускаются контейнеры (PostgreSQL, Backend, Frontend)
- Применяются миграции базы данных (Alembic)
- Создаются тестовые пользователи и заявки (сиды)

### Доступные сервисы

Сервис: Backend API
URL: http://localhost:8000
Описание: REST API сервиса

Сервис: Документация API
URL: http://localhost:8000/docs
Описание: Swagger UI

Сервис: Frontend
URL: http://localhost:3000
Описание: Веб-интерфейс

### Тестовые пользователи

После запуска в системе автоматически создаются тестовые учетные записи:

**Диспетчер**
Поле: username
Значение: dispatcher1

Поле: password
Значение: dispatcher123

Поле: full_name
Значение: Иванов Петр Сергеевич

Поле: role
Значение: dispatcher

**Мастер 1**
Поле: username
Значение: master1

Поле: password
Значение: master123

Поле: full_name
Значение: Смирнов Александр Иванович

Поле: role
Значение: master

**Мастер 2**
Поле: username
Значение: master2

Поле: password
Значение: master123

Поле: full_name
Значение: Кузнецов Дмитрий Петрович

Поле: role
Значение: master

## Ключевой тест (по ТЗ)

Название: test_take_to_work_race_same_master

Что проверяет:
Действие "Взять в работу" должно быть безопасным при параллельных запросах. Если два запроса приходят одновременно, заявка не должна "сломаться".

Ожидаемое поведение:
- Первый запрос: успех (200 OK), статус заявки меняется на in_progress
- Второй запрос: отказ (409 Conflict), заявка остается в статусе in_progress

Почему это важно: Предотвращает ситуацию, когда заявка может быть взята в работу дважды или оказаться в некорректном состоянии.

## Другие тесты на race conditions

1. test_assign_master_race_two_dispatchers
Что проверяет: Два диспетчера одновременно назначают разных мастеров на одну заявку

2. test_cancel_request_race_two_dispatchers
Что проверяет: Два диспетчера одновременно пытаются отменить одну заявку

3. test_take_to_work_race_same_master
Что проверяет: Мастер дважды пытается взять одну заявку в работу

4. test_complete_request_race
Что проверяет: Мастер пытается завершить уже завершенную заявку

5. test_assign_then_cancel_should_succeed
Что проверяет: Назначение + отмена (проверка бизнес-логики)

6. test_cancel_after_take_should_fail
Что проверяет: Отмена после взятия в работу (должна быть запрещена)

7. test_complex_race_assign_take_cancel
Что проверяет: Сложный сценарий из нескольких последовательных действий

## Запуск тестов

С подробным логированием
docker-compose exec backend pytest tests/test_race_conditions.py -v -s

## Запуск всех тестов

pytest tests/