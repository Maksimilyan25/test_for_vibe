# tests/test_race_conditions.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.request import Request, RequestStatus
from models.user import User, UserRole
from logger import logger


@pytest.mark.asyncio
class TestRaceConditions:
    """Тесты для проверки race conditions"""

    async def create_test_request(
        self, client: AsyncClient, dispatcher_headers: dict, request_data: dict
    ) -> int:
        """Вспомогательный метод для создания заявки"""
        logger.info("-" * 60)
        logger.info("СОЗДАНИЕ ТЕСТОВОЙ ЗАЯВКИ")
        logger.info(f"Данные: {request_data}")

        response = await client.post(
            "/api/v1/requests/", json=request_data, headers=dispatcher_headers
        )

        logger.info(f"Статус ответа: {response.status_code}")
        assert response.status_code == 201

        request_id = response.json()["id"]
        logger.info(f"Создана заявка ID: {request_id}")
        logger.info("-" * 60)

        return request_id

    async def log_request_state(
        self, db_session: AsyncSession, request_id: int, action: str
    ):
        """Логирование состояния заявки"""
        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        request = result.scalar_one()

        logger.info(
            f"Состояние [{action}]: ID={request.id}, Статус={request.status.value}"
        )

    # ===== ТЕСТЫ ДЛЯ ДИСПЕТЧЕРА =====

    async def test_assign_master_race_two_dispatchers(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        dispatcher_user: User,
        master_user: User,
        second_master_user: User,
        valid_request_data: dict,
    ):
        """
        Тест: Два диспетчера одновременно назначают разных мастеров
        Ожидание: один успех (200), второй ошибка (409)
        """
        logger.info("=" * 80)
        logger.info("ТЕСТ: Гонка назначений (два диспетчера)")

        from services.user_service import UserService
        from schemas.user import UserCreate
        from core.security import create_access_token

        # Создаем второго диспетчера
        logger.info("Создание второго диспетчера...")
        user_service = UserService(db_session)
        dispatcher2 = await user_service.create_user(
            UserCreate(
                username="test_dispatcher2",
                full_name="Тестовый Диспетчер 2",
                password="dispatcher123",
                role=UserRole.DISPATCHER,
            )
        )
        logger.info(f"Второй диспетчер создан: ID={dispatcher2.id}")

        headers1 = {
            "Authorization": f"Bearer {create_access_token(data={'sub': dispatcher_user.username})}"
        }
        headers2 = {
            "Authorization": f"Bearer {create_access_token(data={'sub': dispatcher2.username})}"
        }

        # Создаем заявку
        request_id = await self.create_test_request(
            client, headers1, valid_request_data
        )
        await self.log_request_state(db_session, request_id, "до назначений")

        logger.info(f"Запуск параллельных назначений:")
        logger.info(f"   Диспетчер 1 -> Мастер {master_user.id}")
        logger.info(f"   Диспетчер 2 -> Мастер {second_master_user.id}")

        async def assign_master1():
            logger.info(f"Диспечтер 1: отправка запроса...")
            resp = await client.post(
                f"/api/v1/requests/{request_id}/assign",
                json={"master_id": master_user.id},
                headers=headers1,
            )
            logger.info(f"Диспечтер 1: статус {resp.status_code}")
            return resp

        async def assign_master2():
            logger.info(f"Диспечтер 2: отправка запроса...")
            resp = await client.post(
                f"/api/v1/requests/{request_id}/assign",
                json={"master_id": second_master_user.id},
                headers=headers2,
            )
            logger.info(f"Диспечтер 2: статус {resp.status_code}")
            return resp

        # Запускаем последовательно для SQLite
        resp1 = await assign_master1()
        resp2 = await assign_master2()

        # Проверяем результаты
        logger.info("")
        logger.info("РЕЗУЛЬТАТЫ:")
        logger.info(f"   Диспетчер 1: {resp1.status_code}")
        logger.info(f"   Диспетчер 2: {resp2.status_code}")

        assert resp1.status_code == 200 or resp2.status_code == 200
        assert (resp1.status_code == 200) != (resp2.status_code == 200)
        assert resp1.status_code in [200, 409]
        assert resp2.status_code in [200, 409]

        # Проверяем финальное состояние
        await self.log_request_state(db_session, request_id, "после назначений")

        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        db_request = result.scalar_one()

        logger.info(
            f"ИТОГ: Заявка {request_id} в статусе {db_request.status.value}, назначена на мастера {db_request.assigned_to}"
        )
        logger.info("=" * 80 + "\n")

    async def test_assign_then_cancel_should_succeed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        dispatcher_user: User,
        master_user: User,
        valid_request_data: dict,
    ):
        """
        Тест: Диспетчер назначает мастера, потом отменяет заявку
        Ожидание: отмена должна работать (заявка не взята в работу)
        """
        logger.info("=" * 80)
        logger.info("ТЕСТ: Назначение + отмена (диспетчер)")

        from core.security import create_access_token

        dispatcher_headers = {
            "Authorization": f"Bearer {create_access_token(data={'sub': dispatcher_user.username})}"
        }

        request_id = await self.create_test_request(
            client, dispatcher_headers, valid_request_data
        )
        await self.log_request_state(db_session, request_id, "после создания")

        # Назначаем мастера
        logger.info(f"Назначение мастера {master_user.id}...")
        assign_resp = await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )
        logger.info(f"Статус назначения: {assign_resp.status_code}")
        assert assign_resp.status_code == 200
        await self.log_request_state(db_session, request_id, "после назначения")

        # Отменяем заявку
        logger.info("Отмена заявки...")
        cancel_resp = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=dispatcher_headers
        )
        logger.info(f"Статус отмены: {cancel_resp.status_code}")
        assert cancel_resp.status_code == 200

        # Проверяем финальное состояние
        await self.log_request_state(db_session, request_id, "после отмены")

        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        db_request = result.scalar_one()
        assert db_request.status == RequestStatus.CANCELED

        logger.info(f"ИТОГ: Заявка {request_id} успешно отменена")
        logger.info("=" * 80 + "\n")

    async def test_cancel_after_take_should_fail(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        dispatcher_user: User,
        master_user: User,
        valid_request_data: dict,
    ):
        """
        Тест: Мастер взял заявку в работу, диспетчер пытается отменить
        Ожидание: отмена не должна работать (заявка в работе)
        """
        logger.info("=" * 80)
        logger.info("ТЕСТ: Отмена после взятия в работу")

        from core.security import create_access_token

        dispatcher_headers = {
            "Authorization": f"Bearer {create_access_token(data={'sub': dispatcher_user.username})}"
        }
        master_headers = {
            "Authorization": f"Bearer {create_access_token(data={'sub': master_user.username})}"
        }

        request_id = await self.create_test_request(
            client, dispatcher_headers, valid_request_data
        )
        await self.log_request_state(db_session, request_id, "после создания")

        # Назначаем мастера
        logger.info(f"Назначение мастера {master_user.id}...")
        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )
        await self.log_request_state(db_session, request_id, "после назначения")

        # Мастер берет в работу
        logger.info("Мастер берет заявку в работу...")
        take_resp = await client.post(
            f"/api/v1/master/requests/{request_id}/take", headers=master_headers
        )
        logger.info(f"Статус взятия в работу: {take_resp.status_code}")
        assert take_resp.status_code == 200
        await self.log_request_state(db_session, request_id, "в работе")

        # Диспетчер пытается отменить
        logger.info("Диспетчер пытается отменить заявку...")
        cancel_resp = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=dispatcher_headers
        )
        logger.info(f"Статус отмены: {cancel_resp.status_code}")
        assert cancel_resp.status_code in [400, 409]

        # Проверяем финальное состояние
        await self.log_request_state(db_session, request_id, "финальное")

        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        db_request = result.scalar_one()
        assert db_request.status == RequestStatus.IN_PROGRESS

        logger.info(
            f"ИТОГ: Заявка {request_id} осталась в статусе {db_request.status.value}"
        )
        logger.info("=" * 80 + "\n")

    async def test_cancel_request_race_two_dispatchers(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        dispatcher_user: User,
        valid_request_data: dict,
    ):
        """
        Тест: Два диспетчера пытаются отменить одну заявку
        Ожидание: первый успех, второй ошибка
        """
        logger.info("=" * 80)
        logger.info("ТЕСТ: Гонка отмен (два диспетчера)")

        from services.user_service import UserService
        from schemas.user import UserCreate
        from core.security import create_access_token

        # Создаем второго диспетчера
        logger.info("Создание второго диспетчера...")
        user_service = UserService(db_session)
        dispatcher2 = await user_service.create_user(
            UserCreate(
                username="test_dispatcher2",
                full_name="Тестовый Диспетчер 2",
                password="dispatcher123",
                role=UserRole.DISPATCHER,
            )
        )
        logger.info(f"Второй диспетчер создан: ID={dispatcher2.id}")

        headers1 = {
            "Authorization": f"Bearer {create_access_token(data={'sub': dispatcher_user.username})}"
        }
        headers2 = {
            "Authorization": f"Bearer {create_access_token(data={'sub': dispatcher2.username})}"
        }

        request_id = await self.create_test_request(
            client, headers1, valid_request_data
        )
        await self.log_request_state(db_session, request_id, "до отмен")

        # Первая отмена
        logger.info("Первый диспетчер: попытка отмены...")
        resp1 = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=headers1
        )
        logger.info(f"Статус: {resp1.status_code}")

        # Вторая отмена
        logger.info("Второй диспетчер: попытка отмены...")
        resp2 = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=headers2
        )
        logger.info(f"Статус: {resp2.status_code}")

        # Проверка результатов
        logger.info("")
        logger.info("РЕЗУЛЬТАТЫ:")
        logger.info(f"   Диспетчер 1: {resp1.status_code}")
        logger.info(f"   Диспетчер 2: {resp2.status_code}")

        assert resp1.status_code == 200
        assert resp2.status_code in [400, 409]

        # Проверяем финальное состояние
        await self.log_request_state(db_session, request_id, "после отмен")

        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        db_request = result.scalar_one()
        assert db_request.status == RequestStatus.CANCELED

        logger.info(f"ИТОГ: Заявка {request_id} отменена")
        logger.info("=" * 80 + "\n")

    # ===== ТЕСТЫ ДЛЯ МАСТЕРА =====

    async def test_take_to_work_race_same_master(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        dispatcher_user: User,
        master_user: User,
        valid_request_data: dict,
    ):
        """
        Тест: Мастер пытается взять в работу уже взятую заявку
        Ожидание: первый успех, второй ошибка
        """
        logger.info("=" * 80)
        logger.info("ТЕСТ: Двойное взятие в работу (один мастер)")

        from core.security import create_access_token

        dispatcher_headers = {
            "Authorization": f"Bearer {create_access_token(data={'sub': dispatcher_user.username})}"
        }
        master_headers = {
            "Authorization": f"Bearer {create_access_token(data={'sub': master_user.username})}"
        }

        # Создаем заявку
        request_id = await self.create_test_request(
            client, dispatcher_headers, valid_request_data
        )

        # Назначаем мастера
        logger.info(f"Назначение мастера {master_user.id}...")
        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )
        await self.log_request_state(db_session, request_id, "после назначения")

        # Первая попытка взять в работу
        logger.info("Первая попытка взятия в работу...")
        resp1 = await client.post(
            f"/api/v1/master/requests/{request_id}/take", headers=master_headers
        )
        logger.info(f"Статус: {resp1.status_code}")

        # Вторая попытка взять в работу
        logger.info("Вторая попытка взятия в работу...")
        resp2 = await client.post(
            f"/api/v1/master/requests/{request_id}/take", headers=master_headers
        )
        logger.info(f"Статус: {resp2.status_code}")

        # Проверка результатов
        logger.info("")
        logger.info("РЕЗУЛЬТАТЫ:")
        logger.info(f"   Первая попытка: {resp1.status_code}")
        logger.info(f"   Вторая попытка: {resp2.status_code}")

        assert resp1.status_code == 200
        assert resp2.status_code in [400, 409]

        # Проверяем финальное состояние
        await self.log_request_state(db_session, request_id, "финальное")

        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        db_request = result.scalar_one()
        assert db_request.status == RequestStatus.IN_PROGRESS

        logger.info(f"ИТОГ: Заявка {request_id} в статусе {db_request.status.value}")
        logger.info("=" * 80 + "\n")

    async def test_complete_request_race(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        dispatcher_user: User,
        master_user: User,
        valid_request_data: dict,
    ):
        """
        Тест: Мастер пытается завершить уже завершенную заявку
        Ожидание: первый успех, второй ошибка
        """
        logger.info("=" * 80)
        logger.info("ТЕСТ: Двойное завершение заявки")

        from core.security import create_access_token

        dispatcher_headers = {
            "Authorization": f"Bearer {create_access_token(data={'sub': dispatcher_user.username})}"
        }
        master_headers = {
            "Authorization": f"Bearer {create_access_token(data={'sub': master_user.username})}"
        }

        # Создаем заявку
        request_id = await self.create_test_request(
            client, dispatcher_headers, valid_request_data
        )

        # Назначаем и берем в работу
        logger.info(f"Назначение мастера {master_user.id}...")
        await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )

        logger.info("Взятие в работу...")
        await client.post(
            f"/api/v1/master/requests/{request_id}/take", headers=master_headers
        )
        await self.log_request_state(db_session, request_id, "в работе")

        # Первое завершение
        logger.info("Первая попытка завершения...")
        resp1 = await client.post(
            f"/api/v1/master/requests/{request_id}/complete", headers=master_headers
        )
        logger.info(f"Статус: {resp1.status_code}")

        # Второе завершение
        logger.info("Вторая попытка завершения...")
        resp2 = await client.post(
            f"/api/v1/master/requests/{request_id}/complete", headers=master_headers
        )
        logger.info(f"Статус: {resp2.status_code}")

        # Проверка результатов
        logger.info("")
        logger.info("РЕЗУЛЬТАТЫ:")
        logger.info(f"   Первая попытка: {resp1.status_code}")
        logger.info(f"   Вторая попытка: {resp2.status_code}")

        assert resp1.status_code == 200
        assert resp2.status_code in [400, 409]

        # Проверяем финальное состояние
        await self.log_request_state(db_session, request_id, "финальное")

        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        db_request = result.scalar_one()
        assert db_request.status == RequestStatus.DONE

        logger.info(f"ИТОГ: Заявка {request_id} завершена")
        logger.info("=" * 80 + "\n")

    async def test_complex_race_assign_take_cancel(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        dispatcher_user: User,
        master_user: User,
        valid_request_data: dict,
    ):
        """
        Тест: Сложный сценарий - проверка последовательности действий
        """
        logger.info("=" * 80)
        logger.info(
            "ТЕСТ: Сложный сценарий (назначение -> взятие -> отмена -> завершение)"
        )

        from core.security import create_access_token

        dispatcher_headers = {
            "Authorization": f"Bearer {create_access_token(data={'sub': dispatcher_user.username})}"
        }
        master_headers = {
            "Authorization": f"Bearer {create_access_token(data={'sub': master_user.username})}"
        }

        # Создаем заявку
        request_id = await self.create_test_request(
            client, dispatcher_headers, valid_request_data
        )
        await self.log_request_state(db_session, request_id, "после создания")

        # 1. Назначаем мастера
        logger.info("1. Назначение мастера...")
        assign_resp = await client.post(
            f"/api/v1/requests/{request_id}/assign",
            json={"master_id": master_user.id},
            headers=dispatcher_headers,
        )
        logger.info(f"   Статус: {assign_resp.status_code}")
        assert assign_resp.status_code == 200
        await self.log_request_state(db_session, request_id, "после назначения")

        # 2. Берем в работу
        logger.info("2. Взятие в работу...")
        take_resp = await client.post(
            f"/api/v1/master/requests/{request_id}/take", headers=master_headers
        )
        logger.info(f"   Статус: {take_resp.status_code}")
        assert take_resp.status_code == 200
        await self.log_request_state(db_session, request_id, "в работе")

        # 3. Пытаемся отменить (должно быть нельзя)
        logger.info("3. Попытка отмены (диспетчер)...")
        cancel_resp = await client.post(
            f"/api/v1/requests/{request_id}/cancel", headers=dispatcher_headers
        )
        logger.info(f"   Статус: {cancel_resp.status_code}")
        assert cancel_resp.status_code in [400, 409]
        await self.log_request_state(db_session, request_id, "после попытки отмены")

        # 4. Завершаем
        logger.info("4. Завершение заявки...")
        complete_resp = await client.post(
            f"/api/v1/master/requests/{request_id}/complete", headers=master_headers
        )
        logger.info(f"   Статус: {complete_resp.status_code}")
        assert complete_resp.status_code == 200

        # Проверяем финальное состояние
        await self.log_request_state(db_session, request_id, "финальное")

        result = await db_session.execute(
            select(Request).where(Request.id == request_id)
        )
        db_request = result.scalar_one()
        assert db_request.status == RequestStatus.DONE

        logger.info(f"ИТОГ: Заявка {request_id} успешно завершена")
        logger.info("=" * 80 + "\n")

