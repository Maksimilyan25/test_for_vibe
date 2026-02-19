# tests/conftest.py (дополнение)
import asyncio
from typing import AsyncGenerator, Dict

import pytest
import pytest_asyncio
from core.config import settings
from core.database import Base, get_db
from core.security import create_access_token
from httpx import ASGITransport, AsyncClient
from main import app
from models.user import User, UserRole
from schemas.user import UserCreate
from services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Используем test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False,  # отключаем логирование SQL для тестов
)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для всей сессии тестов"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Создает и очищает базу данных перед каждым тестом"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # База будет очищена перед следующим тестом


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Клиент для тестирования эндпоинтов"""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Сессия базы данных для тестов"""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()
        await session.close()


# ============= ФИКСТУРЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ =============


@pytest_asyncio.fixture
async def dispatcher_user(db_session: AsyncSession) -> User:
    """Создание тестового диспетчера через сервис"""
    user_service = UserService(db_session)
    user_create = UserCreate(
        username="test_dispatcher",
        full_name="Тестовый Диспетчер",
        password="dispatcher123",
        role=UserRole.DISPATCHER,
    )
    user = await user_service.create_user(user_create)
    return user


@pytest_asyncio.fixture
async def master_user(db_session: AsyncSession) -> User:
    """Создание тестового мастера через сервис"""
    user_service = UserService(db_session)
    user_create = UserCreate(
        username="test_master",
        full_name="Тестовый Мастер",
        password="master123",
        role=UserRole.MASTER,
    )
    user = await user_service.create_user(user_create)
    return user


@pytest_asyncio.fixture
async def second_master_user(db_session: AsyncSession) -> User:
    """Создание второго тестового мастера через сервис"""
    user_service = UserService(db_session)
    user_create = UserCreate(
        username="test_master2",
        full_name="Тестовый Мастер 2",
        password="master123",
        role=UserRole.MASTER,
    )
    user = await user_service.create_user(user_create)
    return user


# ============= ФИКСТУРЫ ДЛЯ ТОКЕНОВ И ЗАГОЛОВКОВ =============


@pytest.fixture
def dispatcher_token(dispatcher_user: User) -> str:
    """Создание токена для диспетчера"""
    return create_access_token(data={"sub": dispatcher_user.username})


@pytest.fixture
def master_token(master_user: User) -> str:
    """Создание токена для мастера"""
    return create_access_token(data={"sub": master_user.username})


@pytest.fixture
def second_master_token(second_master_user: User) -> str:
    """Создание токена для второго мастера"""
    return create_access_token(data={"sub": second_master_user.username})


@pytest.fixture
def dispatcher_headers(dispatcher_token: str) -> Dict[str, str]:
    """Заголовки с токеном диспетчера"""
    return {"Authorization": f"Bearer {dispatcher_token}"}


@pytest.fixture
def master_headers(master_token: str) -> Dict[str, str]:
    """Заголовки с токеном мастера"""
    return {"Authorization": f"Bearer {master_token}"}


@pytest.fixture
def second_master_headers(second_master_token: str) -> Dict[str, str]:
    """Заголовки с токеном второго мастера"""
    return {"Authorization": f"Bearer {second_master_token}"}


# ============= ФИКСТУРЫ ДЛЯ ТЕСТОВЫХ ДАННЫХ =============


@pytest.fixture
def valid_request_data() -> Dict[str, str]:
    """Валидные данные для создания заявки"""
    return {
        "client_name": "Иван Петров",
        "phone": "+7 (999) 123-45-67",
        "address": "ул. Ленина, д. 10, кв. 5",
        "problem_text": "Не работает стиральная машина",
    }


@pytest.fixture
def another_request_data() -> Dict[str, str]:
    """Другие валидные данные для создания заявки"""
    return {
        "client_name": "Мария Сидорова",
        "phone": "+7 (999) 765-43-21",
        "address": "ул. Гагарина, д. 15, кв. 42",
        "problem_text": "Течет кран на кухне",
    }


@pytest.fixture
def invalid_request_data() -> Dict[str, str]:
    """Невалидные данные для создания заявки (пустые поля)"""
    return {"client_name": "", "phone": "", "address": "", "problem_text": ""}
