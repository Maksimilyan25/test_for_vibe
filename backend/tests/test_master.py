# tests/test_master.py
import pytest
from httpx import AsyncClient
from models.request import Request, RequestStatus
from models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestMasterRequests:
    """Тесты для мастера: работа с заявками"""

    # ===== 1. СПИСОК МОИХ ЗАЯВОК =====

    async def test_get_my_requests_success(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
        second_master_user: User,
        dispatcher_headers: dict,
        valid_request_data: dict,
        another_request_data: dict,
    ):
        """Успешное получение списка своих заявок"""
        # Создаем заявку и назначаем на первого мастера
        resp1 = await client.post("/api/v1/requests/", json=valid_request_data)
        req1_id = resp1.json()["id"]
        await client.post(
            f"/api/v1/requests/{req1_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        # Создаем заявку и назначаем на второго мастера
        resp2 = await client.post("/api/v1/requests/", json=another_request_data)
        req2_id = resp2.json()["id"]
        await client.post(
            f"/api/v1/requests/{req2_id}/assign",
            json={"master_id": second_master_user.id},
            headers=dispatcher_headers,
        )

        response = await client.get("/api/v1/master/requests", headers=master_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["client_name"] == valid_request_data["client_name"]
        assert data[0]["assigned_to"] == master_user.id

    async def test_get_my_requests_filter_by_status(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        """Фильтрация своих заявок по статусу"""
        resp1 = await client.post("/api/v1/requests/", json=valid_request_data)
        req1_id = resp1.json()["id"]
        await client.post(
            f"/api/v1/requests/{req1_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        resp2 = await client.post("/api/v1/requests/", json=valid_request_data)
        req2_id = resp2.json()["id"]
        await client.post(
            f"/api/v1/requests/{req2_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        await client.post(
            f"/api/v1/master/requests/{req1_id}/take", headers=master_headers
        )

        response = await client.get(
            "/api/v1/master/requests?status=assigned", headers=master_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "assigned"

        response = await client.get(
            "/api/v1/master/requests?status=in_progress", headers=master_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "in_progress"

    async def test_get_my_requests_empty_list(
        self, client: AsyncClient, master_headers: dict
    ):
        response = await client.get("/api/v1/master/requests", headers=master_headers)
        assert response.status_code == 200
        data = response.json()
        assert data == []

    async def test_get_my_requests_pagination(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        for i in range(3):
            resp = await client.post("/api/v1/requests/", json=valid_request_data)
            req_id = resp.json()["id"]
            await client.post(
                f"/api/v1/requests/{req_id}/assign",
                json={"master_id": master_user.id},
                headers=dispatcher_headers,
            )

        response = await client.get(
            "/api/v1/master/requests?skip=1&limit=1", headers=master_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    # ===== 2. ВЗЯТЬ В РАБОТУ =====

    async def test_take_to_work_success(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
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
            f"/api/v1/master/requests/{request_id}/take", headers=master_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        db_request = result.scalar_one()
        assert db_request.status == RequestStatus.IN_PROGRESS

    async def test_take_to_work_not_assigned_to_me(
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
            f"/api/v1/master/requests/{request_id}/take", headers=master_headers
        )

        assert response.status_code == 404

    async def test_take_to_work_wrong_status(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        create_resp = await client.post("/api/v1/requests/", json=valid_request_data)
        request_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/master/requests/{request_id}/take", headers=master_headers
        )

        assert response.status_code == 404

    async def test_take_to_work_not_found(
        self, client: AsyncClient, master_headers: dict
    ):
        response = await client.post(
            "/api/v1/master/requests/99999/take", headers=master_headers
        )
        assert response.status_code == 404

    # ===== 3. ЗАВЕРШИТЬ ЗАЯВКУ =====

    async def test_complete_request_success(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
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
        await client.post(
            f"/api/v1/master/requests/{request_id}/take", headers=master_headers
        )

        response = await client.post(
            f"/api/v1/master/requests/{request_id}/complete", headers=master_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"

        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        db_request = result.scalar_one()
        assert db_request.status == RequestStatus.DONE

    async def test_complete_request_not_in_progress(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        create_resp = await client.post("/api/v1/requests/", json=valid_request_data)
        request_id = create_resp.json()["id"]
        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        response = await client.post(
            f"/api/v1/master/requests/{request_id}/complete", headers=master_headers
        )

        assert response.status_code == 409  # Conflict

    async def test_complete_request_not_mine(
        self,
        client: AsyncClient,
        master_headers: dict,
        second_master_user: User,
        second_master_headers: dict,
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
        await client.post(
            f"/api/v1/master/requests/{request_id}/take", headers=second_master_headers
        )

        response = await client.post(
            f"/api/v1/master/requests/{request_id}/complete", headers=master_headers
        )

        assert response.status_code == 404

    async def test_complete_request_not_found(
        self, client: AsyncClient, master_headers: dict
    ):
        response = await client.post(
            "/api/v1/master/requests/99999/complete", headers=master_headers
        )
        assert response.status_code == 404

    # ===== 4. ПОЛУЧЕНИЕ КОНКРЕТНОЙ ЗАЯВКИ =====

    async def test_get_my_request_details_success(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        create_resp = await client.post("/api/v1/requests/", json=valid_request_data)
        request_id = create_resp.json()["id"]
        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        response = await client.get(
            f"/api/v1/master/requests/{request_id}", headers=master_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == request_id
        assert data["client_name"] == valid_request_data["client_name"]
        assert data["assigned_to"] == master_user.id

    async def test_get_other_master_request_forbidden(
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

        response = await client.get(
            f"/api/v1/master/requests/{request_id}", headers=master_headers
        )

        assert response.status_code == 404

    async def test_get_my_request_not_found(
        self, client: AsyncClient, master_headers: dict
    ):
        response = await client.get(
            "/api/v1/master/requests/99999", headers=master_headers
        )
        assert response.status_code == 404

    # ===== 5. СТАТИСТИКА =====

    async def test_get_my_stats_success(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        # Заявка 1: assigned
        resp1 = await client.post("/api/v1/requests/", json=valid_request_data)
        req1_id = resp1.json()["id"]
        await client.post(
            f"/api/v1/requests/{req1_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        # Заявка 2: in_progress
        resp2 = await client.post("/api/v1/requests/", json=valid_request_data)
        req2_id = resp2.json()["id"]
        await client.post(
            f"/api/v1/requests/{req2_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )
        await client.post(
            f"/api/v1/master/requests/{req2_id}/take", headers=master_headers
        )

        # Заявка 3: done
        resp3 = await client.post("/api/v1/requests/", json=valid_request_data)
        req3_id = resp3.json()["id"]
        await client.post(
            f"/api/v1/requests/{req3_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )
        await client.post(
            f"/api/v1/master/requests/{req3_id}/take", headers=master_headers
        )
        await client.post(
            f"/api/v1/master/requests/{req3_id}/complete", headers=master_headers
        )

        # Заявка 4: canceled
        resp4 = await client.post("/api/v1/requests/", json=valid_request_data)
        req4_id = resp4.json()["id"]
        await client.post(
            f"/api/v1/requests/{req4_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )
        await client.post(
            f"/api/v1/requests/{req4_id}/cancel", headers=dispatcher_headers
        )

        response = await client.get("/api/v1/master/stats", headers=master_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert data["assigned"] == 1
        assert data["in_progress"] == 1
        assert data["done"] == 1
        assert data["canceled"] == 1
        assert data["new"] == 0

    async def test_get_my_stats_empty(self, client: AsyncClient, master_headers: dict):
        response = await client.get("/api/v1/master/stats", headers=master_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["assigned"] == 0
        assert data["in_progress"] == 0
        assert data["done"] == 0
        assert data["canceled"] == 0
        assert data["new"] == 0

    # ===== 6. ДОПОЛНИТЕЛЬНЫЕ ПРОВЕРКИ =====

    async def test_master_cannot_assign(
        self,
        client: AsyncClient,
        master_headers: dict,
        second_master_user: User,
        dispatcher_headers: dict,
        valid_request_data: dict,
    ):
        create_resp = await client.post("/api/v1/requests/", json=valid_request_data)
        request_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": second_master_user.id},
            headers=master_headers,
        )

        assert response.status_code == 403

    async def test_master_can_create_request(
        self,
        client: AsyncClient,
        master_headers: dict,
        valid_request_data: dict,
    ):
        """Мастер может создавать заявки (публичный доступ)"""
        response = await client.post(
            "/api/v1/requests/", json=valid_request_data, headers=master_headers
        )
        assert response.status_code == 201

    async def test_master_can_cancel_own_request(
        self,
        client: AsyncClient,
        master_headers: dict,
        master_user: User,
        dispatcher_headers: dict,
        valid_request_data: dict,
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

    async def test_master_cannot_cancel_others_request(
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
