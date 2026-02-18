import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.user_service import UserService
from schemas.user import UserCreate


@pytest.mark.asyncio
class TestAuth:
    """Тесты для аутентификации"""

    async def test_register_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Успешная регистрация"""
        user_data = {
            "username": "user1",
            "full_name": "User One",
            "role": "master",
            "password": "123456",
        }

        response = await client.post("/api/v1/auth/register", json=user_data)

        # Проверяем статус ответа
        assert response.status_code in [200, 201]

        data = response.json()
        assert data["username"] == "user1"
        assert data["full_name"] == "User One"
        assert data["role"] == "master"
        assert "id" in data

    async def test_register_duplicate(self, client: AsyncClient):
        """Регистрация с существующим username"""
        # Первый пользователь
        user1 = {
            "username": "duplicate",
            "full_name": "First",
            "role": "master",
            "password": "123456",
        }
        response1 = await client.post("/api/v1/auth/register", json=user1)
        assert response1.status_code in [200, 201]

        # Второй с тем же username
        user2 = {
            "username": "duplicate",
            "full_name": "Second",
            "role": "dispatcher",
            "password": "123456",
        }
        response2 = await client.post("/api/v1/auth/register", json=user2)

        assert response2.status_code == 400
        error_detail = response2.json().get("detail", "")
        # Проверяем русское сообщение об ошибке
        assert "уже существует" in error_detail.lower()

    async def test_login_success(self, client: AsyncClient, db_session: AsyncSession):
        """Успешный вход"""
        # Регистрация пользователя напрямую через сервис с использованием UserCreate
        user_service = UserService(db_session)
        user_create = UserCreate(
            username="loginuser",
            full_name="Login User",
            password="123456",
            role="dispatcher",
        )
        user = await user_service.create_user(user_create)

        # Вход
        login_data = {"username": "loginuser", "password": "123456"}
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Вход с неправильным паролем"""
        # Регистрация пользователя
        user_service = UserService(db_session)
        user_create = UserCreate(
            username="wrongpass",
            full_name="Wrong Pass",
            password="123456",
            role="master",
        )
        user = await user_service.create_user(user_create)

        # Вход с неправильным паролем
        login_data = {"username": "wrongpass", "password": "wrong123"}
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 401
        error_detail = response.json().get("detail", "")
        # Проверяем русское сообщение об ошибке
        assert (
            "неверное имя" in error_detail.lower()
            or "неверный пароль" in error_detail.lower()
        )

    async def test_login_nonexistent(self, client: AsyncClient):
        """Вход с несуществующим пользователем"""
        login_data = {"username": "nobody", "password": "123456"}
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 401
        error_detail = response.json().get("detail", "")
        assert (
            "неверное имя" in error_detail.lower()
            or "неверный пароль" in error_detail.lower()
        )

    async def test_get_me_with_token(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Получение информации о себе с токеном"""
        # Создаем пользователя
        user_service = UserService(db_session)
        user_create = UserCreate(
            username="metest", full_name="Me Test", password="123456", role="dispatcher"
        )
        user = await user_service.create_user(user_create)

        # Логинимся
        login_data = {"username": "metest", "password": "123456"}
        login_response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert login_response.status_code == 200
        token = login_response.json().get("access_token")
        assert token is not None

        # Запрос /me
        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "metest"
        assert data["full_name"] == "Me Test"
        assert data["role"] == "dispatcher"

    async def test_get_me_no_token(self, client: AsyncClient):
        """Получение информации без токена"""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        """Получение информации с невалидным токеном"""
        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401

    async def test_full_flow(self, client: AsyncClient):
        """Полный цикл: регистрация -> логин -> получение профиля"""
        # Регистрация через API
        user_data = {
            "username": "fullflow",
            "full_name": "Full Flow User",
            "role": "master",
            "password": "123456",
        }
        reg_response = await client.post("/api/v1/auth/register", json=user_data)
        assert reg_response.status_code in [200, 201]

        # Логин
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "fullflow", "password": "123456"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        token = login_response.json().get("access_token")
        assert token is not None

        # Получение профиля
        me_response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "fullflow"
