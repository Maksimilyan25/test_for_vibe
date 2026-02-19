#!/usr/bin/env python
"""
Скрипт для наполнения базы данных тестовыми данными (сидами)
Запускается автоматически при старте контейнера
"""

import asyncio

from core.database import async_session
from core.security import get_password_hash
from models.user import User, UserRole
from models.request import Request, RequestStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def check_data_exists(session: AsyncSession) -> bool:
    """Проверяет, есть ли уже данные в БД"""
    # Проверяем пользователей
    result = await session.execute(select(User).limit(1))
    user = result.scalar_one_or_none()

    if user:
        print("✓ Данные уже существуют, пропускаем создание сидов")
        return True

    print("→ Данных нет, создаем сиды...")
    return False


async def create_users(session: AsyncSession):
    """Создание пользователей (1 диспетчер, 2 мастера)"""
    print("  Создаем пользователей...")

    users_data = [
        # Диспетчер
        {
            "username": "dispatcher1",
            "full_name": "Иванов Петр Сергеевич",
            "role": UserRole.DISPATCHER,
            "password": "dispatcher123",
        },
        # Мастера
        {
            "username": "master1",
            "full_name": "Смирнов Александр Иванович",
            "role": UserRole.MASTER,
            "password": "master123",
        },
        {
            "username": "master2",
            "full_name": "Кузнецов Дмитрий Петрович",
            "role": UserRole.MASTER,
            "password": "master123",
        },
    ]

    created_users = []
    for user_data in users_data:
        hashed_password = get_password_hash(user_data["password"])
        user = User(
            username=user_data["username"],
            full_name=user_data["full_name"],
            role=user_data["role"],
            hashed_password=hashed_password,
        )
        session.add(user)
        created_users.append(user)
        print(f"    + {user_data['role'].value}: {user_data['full_name']}")

    await session.flush()
    return created_users


async def create_requests(session: AsyncSession, users: list[User]):
    """Создание заявок для проверки"""
    print("  Создаем заявки...")

    masters = [u for u in users if u.role == UserRole.MASTER]
    master1, master2 = masters[0], masters[1]

    requests_data = [
        # Новая заявка (без мастера)
        {
            "client_name": "Соколова Елена Владимировна",
            "phone": 79161234567,
            "address": "ул. Ленина, д. 10, кв. 5",
            "problem_text": "Не работает стиральная машина, при отжиме сильная вибрация и шум",
            "status": RequestStatus.NEW,
            "assigned_to": None,
        },
        # Еще одна новая
        {
            "client_name": "Морозов Андрей Викторович",
            "phone": 79269876543,
            "address": "пр. Мира, д. 25, кв. 12",
            "problem_text": "Протекает кран на кухне, нужна замена смесителя",
            "status": RequestStatus.NEW,
            "assigned_to": None,
        },
        # Назначена мастеру 1
        {
            "client_name": "Волкова Татьяна Николаевна",
            "phone": 79031234567,
            "address": "ул. Гагарина, д. 5, кв. 45",
            "problem_text": "Розетка искрит, пропадает свет в комнате",
            "status": RequestStatus.ASSIGNED,
            "assigned_to": master1.id,
        },
        # В работе у мастера 1
        {
            "client_name": "Козлов Сергей Петрович",
            "phone": 79159876543,
            "address": "ул. Пушкина, д. 15, кв. 8",
            "problem_text": "Не включается холодильник, требуется диагностика",
            "status": RequestStatus.IN_PROGRESS,
            "assigned_to": master1.id,
        },
        # Назначена мастеру 2
        {
            "client_name": "Новикова Ирина Александровна",
            "phone": 79261112233,
            "address": "пр. Ленинградский, д. 30, кв. 56",
            "problem_text": "Замена проводки в квартире, нужна консультация",
            "status": RequestStatus.ASSIGNED,
            "assigned_to": master2.id,
        },
        # В работе у мастера 2
        {
            "client_name": "Лебедев Михаил Юрьевич",
            "phone": 79039998877,
            "address": "ул. Советская, д. 8, кв. 23",
            "problem_text": "Установка люстры и подключение",
            "status": RequestStatus.IN_PROGRESS,
            "assigned_to": master2.id,
        },
        # Завершенная заявка (мастер 1)
        {
            "client_name": "Григорьева Анна Дмитриевна",
            "phone": 79174445566,
            "address": "ул. Кирова, д. 12, кв. 34",
            "problem_text": "Замена лампочек и ремонт выключателя",
            "status": RequestStatus.DONE,
            "assigned_to": master1.id,
        },
        # Завершенная заявка (мастер 2)
        {
            "client_name": "Федоров Павел Андреевич",
            "phone": 79257778899,
            "address": "пр. Октябрьский, д. 7, кв. 67",
            "problem_text": "Установка розеток для стиральной машины",
            "status": RequestStatus.DONE,
            "assigned_to": master2.id,
        },
        # Отмененная заявка
        {
            "client_name": "Семенова Ольга Викторовна",
            "phone": 79036667788,
            "address": "ул. Лесная, д. 3, кв. 19",
            "problem_text": "Ремонт электроплиты, не греет духовка",
            "status": RequestStatus.CANCELED,
            "assigned_to": None,
        },
    ]

    for req_data in requests_data:
        request = Request(**req_data)
        session.add(request)

    print(f"    + Создано {len(requests_data)} заявок")


async def main():
    """Главная функция"""
    print("\n" + "=" * 50)
    print("ПРОВЕРКА И СОЗДАНИЕ СИДОВ")
    print("=" * 50)

    async with async_session() as session:
        # Проверяем, есть ли данные
        exists = await check_data_exists(session)

        if not exists:
            # Создаем пользователей
            users = await create_users(session)

            # Создаем заявки
            await create_requests(session, users)

            # Сохраняем все изменения
            await session.commit()
            print("\n✓ Сиды успешно созданы!")
        else:
            print("✓ Сиды уже существуют, ничего не делаем")

    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
