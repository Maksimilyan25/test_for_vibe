# tests/test_dispatcher.py
import pytest
from httpx import AsyncClient
from models.request import Request, RequestStatus
from models.user import User, UserRole
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestDispatcherRequests:
    """Тесты для диспетчера: создание и управление заявками"""

    # ===== 1. СОЗДАНИЕ ЗАЯВКИ (уже есть) =====

    async def test_create_request_success(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        valid_request_data: dict,
        db_session: AsyncSession,
    ):
        """Успешное создание заявки диспетчером"""
        response = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["client_name"] == valid_request_data["client_name"]
        assert data["phone"] == valid_request_data["phone"]
        assert data["address"] == valid_request_data["address"]
        assert data["problem_text"] == valid_request_data["problem_text"]
        assert data["status"] == "new"
        assert data["assigned_to"] is None

        # Проверяем в БД
        result = await db_session.execute(
            select(Request).where(Request.id == data["id"])
        )
        db_request = result.scalar_one()
        assert db_request.client_name == valid_request_data["client_name"]
        assert db_request.status == RequestStatus.NEW

    async def test_create_request_master_forbidden(
        self, client: AsyncClient, master_headers: dict, valid_request_data: dict
    ):
        """Мастер не может создавать заявки"""
        response = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=master_headers
        )
        assert response.status_code == 403

    # ===== 2. СПИСОК ЗАЯВОК =====

    async def test_get_requests_list_success(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        valid_request_data: dict,
        another_request_data: dict,
        db_session: AsyncSession,
    ):
        """Успешное получение списка всех заявок"""
        # Создаем две заявки
        await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        await client.post(
            "/api/v1/requests/", json=another_request_data, headers=dispatcher_headers
        )

        # Получаем список
        response = await client.get("/api/v1/requests/", headers=dispatcher_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["client_name"] in [
            valid_request_data["client_name"],
            another_request_data["client_name"],
        ]
        assert data[1]["client_name"] in [
            valid_request_data["client_name"],
            another_request_data["client_name"],
        ]

    async def test_get_requests_filter_by_status(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        master_user: User,
        valid_request_data: dict,
        db_session: AsyncSession,
    ):
        """Фильтрация заявок по статусу"""
        # Создаем заявку
        create_resp = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        request_id = create_resp.json()["id"]

        # Назначаем мастера (статус станет assigned)
        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        # Фильтр по статусу assigned
        response = await client.get(
            "/api/v1/requests/?status=assigned", headers=dispatcher_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "assigned"

        # Фильтр по статусу new (должен быть пустым)
        response = await client.get(
            "/api/v1/requests/?status=new", headers=dispatcher_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_get_requests_filter_by_master(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        master_user: User,
        second_master_user: User,
        valid_request_data: dict,
        another_request_data: dict,
    ):
        """Фильтрация заявок по мастеру"""
        # Создаем первую заявку и назначаем на первого мастера
        resp1 = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        req1_id = resp1.json()["id"]
        await client.post(
            f"/api/v1/requests/{req1_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        # Создаем вторую заявку и назначаем на второго мастера
        resp2 = await client.post(
            "/api/v1/requests/", json=another_request_data, headers=dispatcher_headers
        )
        req2_id = resp2.json()["id"]
        await client.post(
            f"/api/v1/requests/{req2_id}/assign",
            json={"master_id": second_master_user.id},
            headers=dispatcher_headers,
        )

        # Фильтр по первому мастеру
        response = await client.get(
            f"/api/v1/requests/?master_id={master_user.id}", headers=dispatcher_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["assigned_to"] == master_user.id

    async def test_get_requests_pagination(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        """Пагинация списка заявок"""
        # Создаем 5 заявок
        for i in range(5):
            data = valid_request_data.copy()
            data["client_name"] = f"Client {i}"
            await client.post(
                "/api/v1/requests/", json=data, headers=dispatcher_headers
            )

        # Получаем с skip=2, limit=2
        response = await client.get(
            "/api/v1/requests/?skip=2&limit=2", headers=dispatcher_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_get_requests_empty_list(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
    ):
        """Пустой список заявок"""
        response = await client.get("/api/v1/requests/", headers=dispatcher_headers)

        assert response.status_code == 200
        data = response.json()
        assert data == []

    # ===== 3. НАЗНАЧЕНИЕ МАСТЕРА =====

    async def test_assign_master_success(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        master_user: User,
        valid_request_data: dict,
        db_session: AsyncSession,
    ):
        """Успешное назначение мастера на заявку"""
        # Создаем заявку
        create_resp = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        request_id = create_resp.json()["id"]

        # Назначаем мастера
        response = await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == master_user.id
        assert data["status"] == "assigned"

        # Проверяем в БД
        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        db_request = result.scalar_one()
        assert db_request.assigned_to == master_user.id
        assert db_request.status == RequestStatus.ASSIGNED

    async def test_assign_master_request_not_found(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        master_user: User,
    ):
        """Назначение мастера на несуществующую заявку"""
        response = await client.post(
            "/api/v1/requests/99999/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        assert response.status_code == 404

    async def test_assign_master_not_found(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        """Назначение несуществующего мастера"""
        # Создаем заявку
        create_resp = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        request_id = create_resp.json()["id"]

        # Назначаем несуществующего мастера
        response = await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": 99999},
            headers=dispatcher_headers,
        )

        assert response.status_code == 404

    async def test_assign_master_not_new_status(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        master_user: User,
        valid_request_data: dict,
    ):
        """Назначение мастера на заявку не в статусе new"""
        # Создаем заявку
        create_resp = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        request_id = create_resp.json()["id"]

        # Назначаем мастера (статус станет assigned)
        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        # Пытаемся назначить другого мастера
        response = await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        assert response.status_code == 400

    async def test_assign_master_master_forbidden(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
        valid_request_data: dict,
        dispatcher_headers: dict,
    ):
        """Мастер не может назначать мастеров"""
        # Создаем заявку (диспетчером)
        create_resp = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        request_id = create_resp.json()["id"]

        # Пытаемся назначить мастера (мастером)
        response = await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=master_headers,
        )

        assert response.status_code == 403

    # ===== 4. ОТМЕНА ЗАЯВКИ =====

    async def test_cancel_request_success(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        valid_request_data: dict,
        db_session: AsyncSession,
    ):
        """Успешная отмена заявки"""
        # Создаем заявку
        create_resp = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        request_id = create_resp.json()["id"]

        # Отменяем заявку
        response = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=dispatcher_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "canceled"

        # Проверяем в БД
        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        db_request = result.scalar_one()
        assert db_request.status == RequestStatus.CANCELED

    async def test_cancel_request_different_statuses(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        master_user: User,
        valid_request_data: dict,
    ):
        """Отмена заявки в разных статусах"""
        # Создаем заявку
        create_resp = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        request_id = create_resp.json()["id"]

        # Отмена в статусе new
        resp_new = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=dispatcher_headers
        )
        assert resp_new.status_code == 200
        assert resp_new.json()["status"] == "canceled"

        # Создаем новую заявку для теста assigned
        create_resp = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        request_id = create_resp.json()["id"]

        # Назначаем мастера (статус assigned)
        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        # Отмена в статусе assigned
        resp_assigned = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=dispatcher_headers
        )
        assert resp_assigned.status_code == 200
        assert resp_assigned.json()["status"] == "canceled"

    async def test_cancel_already_canceled_request(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        """Отмена уже отмененной заявки"""
        # Создаем заявку
        create_resp = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        request_id = create_resp.json()["id"]

        # Отменяем первый раз
        await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=dispatcher_headers
        )

        # Пытаемся отменить второй раз
        response = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=dispatcher_headers
        )

        assert response.status_code == 400

    async def test_cancel_done_request(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        master_user: User,
        valid_request_data: dict,
    ):
        """Отмена выполненной заявки"""
        # Создаем заявку
        create_resp = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        request_id = create_resp.json()["id"]

        # Назначаем мастера -> assigned
        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        # Мастер берет в работу -> in_progress
        master_token = (
            await client.post(
                "/api/v1/auth/login",
                data={"username": master_user.username, "password": "master123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        ).json()["access_token"]
        master_headers = {"Authorization": f"Bearer {master_token}"}

        await client.post(
            f"/api/v1/master/requests/{request_id}/take", headers=master_headers
        )

        # Мастер завершает -> done
        await client.post(
            f"/api/v1/master/requests/{request_id}/complete", headers=master_headers
        )

        # Диспетчер пытается отменить выполненную заявку
        response = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=dispatcher_headers
        )

        assert response.status_code == 400

    async def test_cancel_request_not_found(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
    ):
        """Отмена несуществующей заявки"""
        response = await client.post(
            "/api/v1/requests/99999/cancel", headers=dispatcher_headers
        )

        assert response.status_code == 404

    # ===== 5. ПОЛУЧЕНИЕ КОНКРЕТНОЙ ЗАЯВКИ =====

    async def test_get_request_by_id_success(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        """Успешное получение заявки по ID"""
        # Создаем заявку
        create_resp = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=dispatcher_headers
        )
        request_id = create_resp.json()["id"]

        # Получаем по ID
        response = await client.get(
            f"/api/v1/requests/{request_id}", headers=dispatcher_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == request_id
        assert data["client_name"] == valid_request_data["client_name"]

    async def test_get_request_by_id_not_found(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
    ):
        """Получение несуществующей заявки"""
        response = await client.get(
            "/api/v1/requests/99999", headers=dispatcher_headers
        )

        assert response.status_code == 404

    # ===== 6. СПИСОК ДОСТУПНЫХ МАСТЕРОВ =====

    async def test_get_available_masters_success(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        master_user: User,
        second_master_user: User,
        db_session: AsyncSession,
    ):
        """Успешное получение списка всех мастеров"""
        response = await client.get(
            "/api/v1/requests/masters/available", headers=dispatcher_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # У нас два мастера из фикстур

        # Проверяем, что оба мастера в списке
        master_ids = [user["id"] for user in data]
        assert master_user.id in master_ids
        assert second_master_user.id in master_ids

        # Проверяем, что все пользователи имеют роль master
        for user in data:
            assert user["role"] == "master"

    async def test_get_available_masters_only_masters(
        self,
        client: AsyncClient,
        dispatcher_headers: dict,
        dispatcher_user: User,
        master_user: User,
        db_session: AsyncSession,
    ):
        """В списке только пользователи с ролью master"""
        response = await client.get(
            "/api/v1/requests/masters/available", headers=dispatcher_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Проверяем, что диспетчера нет в списке
        dispatcher_ids = [user["id"] for user in data if user["role"] == "dispatcher"]
        assert len(dispatcher_ids) == 0

    async def test_get_available_masters_master_forbidden(
        self,
        client: AsyncClient,
        master_headers: dict,
    ):
        """Мастер не может получать список мастеров"""
        response = await client.get(
            "/api/v1/requests/masters/available", headers=master_headers
        )

        assert response.status_code == 403
