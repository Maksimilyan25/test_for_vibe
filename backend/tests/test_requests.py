import pytest
from httpx import AsyncClient
from models.request import Request, RequestStatus
from models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestRequests:
    """Тесты для заявок"""

    async def test_create_request_public_success(
        self,
        client: AsyncClient,
        valid_request_data: dict,
        db_session: AsyncSession,
    ):
        """Публичный доступ: любой может создать заявку без авторизации"""
        # Убедимся что телефон передается как число (строка цифр)
        request_data = valid_request_data.copy()

        response = await client.post("/api/v1/requests/", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["client_name"] == request_data["client_name"]
        # Проверяем что телефон пришел как число
        assert isinstance(data["phone"], int)
        assert data["phone"] == request_data["phone"]
        assert data["address"] == request_data["address"]
        assert data["problem_text"] == request_data["problem_text"]
        assert data["status"] == "new"
        assert data["assigned_to"] is None

        result = await db_session.execute(
            select(Request).where(Request.id == data["id"])
        )
        db_request = result.scalar_one()
        assert db_request.client_name == request_data["client_name"]
        # Проверяем что в БД телефон сохранился как int
        assert isinstance(db_request.phone, int)
        assert db_request.phone == request_data["phone"]
        assert db_request.status == RequestStatus.NEW

    async def test_create_request_invalid_phone(
        self,
        client: AsyncClient,
        valid_request_data: dict,
    ):
        """Тест на невалидный телефон"""
        # Тест 1: телефон содержит буквы
        invalid_data = valid_request_data.copy()
        invalid_data["phone"] = "abc123def456"  # Строка с буквами

        response = await client.post("/api/v1/requests/", json=invalid_data)
        assert response.status_code == 422

        # Тест 2: телефон слишком короткий
        invalid_data["phone"] = "12345"  # Меньше 10 цифр

        response = await client.post("/api/v1/requests/", json=invalid_data)
        assert response.status_code == 422

        # Тест 3: телефон слишком длинный
        invalid_data["phone"] = "12345678901234567890"  # Больше 15 цифр

        response = await client.post("/api/v1/requests/", json=invalid_data)
        assert response.status_code == 422

        # Тест 4: отрицательное число
        invalid_data["phone"] = -1234567890

        response = await client.post("/api/v1/requests/", json=invalid_data)
        assert response.status_code == 422

    async def test_create_request_phone_as_string(
        self,
        client: AsyncClient,
        valid_request_data: dict,
        db_session: AsyncSession,
    ):
        """Тест что телефон может передаваться как строка цифр"""
        request_data = valid_request_data.copy()
        request_data["phone"] = str(request_data["phone"])

        response = await client.post("/api/v1/requests/", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data["phone"], int)
        assert str(data["phone"]) == request_data["phone"]

        # Проверяем в БД
        result = await db_session.execute(
            select(Request).where(Request.id == data["id"])
        )
        db_request = result.scalar_one()
        assert isinstance(db_request.phone, int)
        assert str(db_request.phone) == request_data["phone"]

    async def test_get_requests_list_dispatcher(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        valid_request_data: dict,
        another_request_data: dict,
    ):
        """Диспетчер видит все заявки"""
        await client.post("/api/v1/requests/", json=valid_request_data)
        await client.post("/api/v1/requests/", json=another_request_data)

        response = await client.get("/api/v1/requests/", headers=dispatcher_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        for request in data:
            assert isinstance(request["phone"], int)

    async def test_get_requests_list_master(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        """Мастер видит только свои заявки"""
        create_resp = await client.post("/api/v1/requests/", json=valid_request_data)
        request_id = create_resp.json()["id"]

        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        response = await client.get("/api/v1/requests/", headers=master_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["assigned_to"] == master_user.id
        # Проверяем тип телефона
        assert isinstance(data[0]["phone"], int)

    async def test_assign_master_success(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        master_user: User,
        valid_request_data: dict,
        db_session: AsyncSession,
    ):
        create_resp = await client.post("/api/v1/requests/", json=valid_request_data)
        request_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == master_user.id
        assert data["status"] == "assigned"
        assert isinstance(data["phone"], int)

    async def test_assign_master_master_forbidden(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
        valid_request_data: dict,
    ):
        create_resp = await client.post("/api/v1/requests/", json=valid_request_data)
        request_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=master_headers,
        )

        assert response.status_code == 403

    async def test_cancel_request_dispatcher(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        valid_request_data: dict,
        db_session: AsyncSession,
    ):
        create_resp = await client.post("/api/v1/requests/", json=valid_request_data)
        request_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=dispatcher_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "canceled"
        assert isinstance(data["phone"], int)

    async def test_cancel_request_master_own(
        self,
        client: AsyncClient,
        master_user: User,
        master_headers: dict,
        dispatcher_headers: dict,
        valid_request_data: dict,
        db_session: AsyncSession,
    ):
        create_resp = await client.post("/api/v1/requests/", json=valid_request_data)
        request_id = create_resp.json()["id"]

        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        response = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=master_headers
        )

        assert response.status_code == 200
        assert response.json()["status"] == "canceled"
        assert isinstance(response.json()["phone"], int)

    async def test_cancel_request_master_not_own(
        self,
        client: AsyncClient,
        master_headers: dict,
        second_master_user: User,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        create_resp = await client.post("/api/v1/requests/", json=valid_request_data)
        request_id = create_resp.json()["id"]

        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": second_master_user.id},
            headers=dispatcher_headers,
        )

        response = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=master_headers
        )

        assert response.status_code == 404

    async def test_get_available_masters(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        master_user: User,
        second_master_user: User,
    ):
        response = await client.get(
            "/api/v1/requests/masters/available", headers=dispatcher_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        for user in data:
            assert user["role"] == "master"


@pytest.fixture
def valid_request_data() -> dict:
    """Валидные данные для создания заявки"""
    return {
        "client_name": "Иван Петров",
        "phone": 79991234567,
        "address": "ул. Ленина, д. 10, кв. 5",
        "problem_text": "Не работает стиральная машина",
    }


@pytest.fixture
def another_request_data() -> dict:
    """Другие валидные данные для создания заявки"""
    return {
        "client_name": "Петр Иванов",
        "phone": 79876543210,
        "address": "ул. Гагарина, д. 15, кв. 20",
        "problem_text": "Течет кран на кухне",
    }
