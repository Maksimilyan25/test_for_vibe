import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from main import app
from core.database import Base, get_db
from core.config import settings

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
    # Не удаляем после теста, чтобы можно было увидеть данные при отладке
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
