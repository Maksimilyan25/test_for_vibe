# app/services/request_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional, List, Tuple
from datetime import datetime, timezone

from models.request import Request, RequestStatus
from models.user import User, UserRole
from schemas.request import RequestCreate, RequestFilterParams
from core.exceptions import (
    NotFoundException,
    BusinessLogicException,
    ForbiddenException,
)


class RequestService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_request(self, request_data: RequestCreate, user: User) -> Request:
        """
        Создание новой заявки
        Доступно: только диспетчер
        """
        if user.role != UserRole.DISPATCHER:
            raise ForbiddenException("Только диспетчер может создавать заявки")

        db_request = Request(
            client_name=request_data.client_name,
            phone=request_data.phone,
            address=request_data.address,
            problem_text=request_data.problem_text,
            status=RequestStatus.NEW,
        )
        self.db.add(db_request)
        await self.db.commit()
        await self.db.refresh(db_request)
        return db_request

    async def get_request(self, request_id: int, user: User) -> Request:
        """
        Получение заявки по ID с проверкой прав
        """
        query = select(Request).where(Request.id == request_id)

        # Мастер видит только свои заявки
        if user.role == UserRole.MASTER:
            query = query.where(Request.assigned_to == user.id)

        result = await self.db.execute(query)
        request = result.scalar_one_or_none()

        if not request:
            raise NotFoundException("Заявка не найдена")

        return request

    async def get_requests(
        self, filters: RequestFilterParams, user: User
    ) -> Tuple[List[Request], int]:
        """
        Получение списка заявок с фильтрацией
        """
        # Базовый запрос
        query = select(Request).order_by(Request.created_at.desc())
        count_query = select(func.count(Request.id))

        # Фильтр по ролям
        if user.role == UserRole.MASTER:
            query = query.where(Request.assigned_to == user.id)
            count_query = count_query.where(Request.assigned_to == user.id)

        # Применяем фильтры
        if filters.status:
            query = query.where(Request.status == filters.status)
            count_query = count_query.where(Request.status == filters.status)

        if filters.master_id and user.role == UserRole.DISPATCHER:
            query = query.where(Request.assigned_to == filters.master_id)
            count_query = count_query.where(Request.assigned_to == filters.master_id)

        # Пагинация
        query = query.offset(filters.skip).limit(filters.limit)

        # Получаем результаты
        result = await self.db.execute(query)
        requests = list(result.scalars().all())

        # Получаем общее количество
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return requests, total

    async def assign_master(
        self, request_id: int, master_id: int, user: User
    ) -> Request:
        """
        Назначить мастера на заявку
        Доступно: только диспетчер
        """
        if user.role != UserRole.DISPATCHER:
            raise ForbiddenException("Только диспетчер может назначать мастеров")

        # Получаем заявку
        request = await self._get_request_by_id(request_id)
        if not request:
            raise NotFoundException("Заявка не найдена")

        # Проверяем статус
        if request.status != RequestStatus.NEW:
            raise BusinessLogicException(
                f"Нельзя назначить мастера на заявку со статусом {request.status.value}"
            )

        # Проверяем, что мастер существует
        master = await self._get_master_by_id(master_id)
        if not master:
            raise NotFoundException("Мастер не найден")

        # Назначаем мастера
        request.assigned_to = master_id
        request.status = RequestStatus.ASSIGNED
        request.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def cancel_request(self, request_id: int, user: User) -> Request:
        """
        Отменить заявку
        Диспетчер может отменить любую, мастер - только свою
        """
        request = await self.get_request(request_id, user)

        # Проверяем возможность отмены
        if request.status in [RequestStatus.DONE, RequestStatus.CANCELED]:
            raise BusinessLogicException(
                f"Нельзя отменить заявку со статусом {request.status.value}"
            )

        # Отменяем заявку
        request.status = RequestStatus.CANCELED
        request.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def take_to_work(self, request_id: int, user: User) -> Request:
        """
        Взять заявку в работу (assigned -> in_progress)
        Доступно: только мастер, только свои заявки
        """
        if user.role != UserRole.MASTER:
            raise ForbiddenException("Только мастер может брать заявки в работу")

        request = await self.get_request(request_id, user)

        if request.status != RequestStatus.ASSIGNED:
            raise BusinessLogicException(
                f"Нельзя взять в работу заявку со статусом {request.status.value}"
            )

        if request.assigned_to != user.id:
            raise ForbiddenException("Можно брать в работу только свои заявки")

        request.status = RequestStatus.IN_PROGRESS
        request.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def complete_request(self, request_id: int, user: User) -> Request:
        """
        Завершить заявку (in_progress -> done)
        Доступно: только мастер, только свои заявки
        """
        if user.role != UserRole.MASTER:
            raise ForbiddenException("Только мастер может завершать заявки")

        request = await self.get_request(request_id, user)

        if request.status != RequestStatus.IN_PROGRESS:
            raise BusinessLogicException(
                f"Нельзя завершить заявку со статусом {request.status.value}"
            )

        if request.assigned_to != user.id:
            raise ForbiddenException("Можно завершать только свои заявки")

        request.status = RequestStatus.DONE
        request.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def get_available_masters(self, user: User) -> List[User]:
        """
        Получить список всех мастеров
        Доступно: только диспетчер
        """
        if user.role != UserRole.DISPATCHER:
            raise ForbiddenException(
                "Только диспетчер может просматривать список мастеров"
            )

        query = select(User).where(User.role == UserRole.MASTER)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_request_by_id(self, request_id: int) -> Optional[Request]:
        """Внутренний метод получения заявки без проверки прав"""
        query = select(Request).where(Request.id == request_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_master_by_id(self, master_id: int) -> Optional[User]:
        """Внутренний метод получения мастера"""
        query = select(User).where(
            and_(User.id == master_id, User.role == UserRole.MASTER)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
