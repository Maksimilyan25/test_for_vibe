# app/services/request_service.py
from datetime import datetime, timezone
from typing import Optional

from core.exceptions import (
    BusinessLogicException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from models.request import Request, RequestStatus
from models.user import User, UserRole
from schemas.request import RequestCreate, RequestFilterParams
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class RequestService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_request(
        self, request_data: RequestCreate, user: User | None = None
    ) -> Request:
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
        query = select(Request).where(Request.id == request_id)

        if user.role == UserRole.MASTER:
            query = query.where(Request.assigned_to == user.id)

        result = await self.db.execute(query)
        request = result.scalar_one_or_none()

        if not request:
            raise NotFoundException("Заявка не найдена")

        return request

    async def get_requests(
        self, filters: RequestFilterParams, user: User
    ) -> tuple[list[Request], int]:
        query = select(Request).order_by(Request.created_at.desc())
        count_query = select(func.count(Request.id))

        if user.role == UserRole.MASTER:
            query = query.where(Request.assigned_to == user.id)
            count_query = count_query.where(Request.assigned_to == user.id)

        if filters.status:
            query = query.where(Request.status == filters.status)
            count_query = count_query.where(Request.status == filters.status)

        if filters.master_id and user.role == UserRole.DISPATCHER:
            query = query.where(Request.assigned_to == filters.master_id)
            count_query = count_query.where(Request.assigned_to == filters.master_id)

        query = query.offset(filters.skip).limit(filters.limit)

        result = await self.db.execute(query)
        requests = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return requests, total

    async def assign_master(
        self, request_id: int, master_id: int, user: User
    ) -> Request:
        if user.role != UserRole.DISPATCHER:
            raise ForbiddenException("Только диспетчер может назначать мастеров")

        async with self.db.begin_nested():
            query = select(Request).where(Request.id == request_id).with_for_update()
            result = await self.db.execute(query)
            request = result.scalar_one_or_none()

            if not request:
                raise NotFoundException("Заявка не найдена")

            if request.status != RequestStatus.NEW:
                raise ConflictException(
                    f"Заявка уже {request.status.value}, назначение невозможно"
                )

            master = await self._get_master_by_id(master_id)
            if not master:
                raise NotFoundException("Мастер не найден")

            request.assigned_to = master_id
            request.status = RequestStatus.ASSIGNED
            request.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def cancel_request(self, request_id: int, user: User) -> Request:
        if user.role == UserRole.MASTER:
            check_query = select(Request).where(
                and_(Request.id == request_id, Request.assigned_to == user.id)
            )
            check_result = await self.db.execute(check_query)
            if not check_result.scalar_one_or_none():
                raise NotFoundException("Заявка не найдена")

        async with self.db.begin_nested():
            query = select(Request).where(Request.id == request_id).with_for_update()
            result = await self.db.execute(query)
            request = result.scalar_one_or_none()

            if not request:
                raise NotFoundException("Заявка не найдена")

            if user.role == UserRole.MASTER and request.assigned_to != user.id:
                raise ForbiddenException("Можно отменять только свои заявки")

            if request.status in [
                RequestStatus.DONE,
                RequestStatus.CANCELED,
                RequestStatus.IN_PROGRESS,
            ]:
                raise ConflictException(
                    f"Нельзя отменить заявку со статусом {request.status.value}"
                )

            request.status = RequestStatus.CANCELED
            request.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def take_to_work(self, request_id: int, user: User) -> Request:
        if user.role != UserRole.MASTER:
            raise ForbiddenException("Только мастер может брать заявки в работу")

        async with self.db.begin_nested():
            query = (
                select(Request)
                .where(and_(Request.id == request_id, Request.assigned_to == user.id))
                .with_for_update()
            )

            result = await self.db.execute(query)
            request = result.scalar_one_or_none()

            if not request:
                raise NotFoundException("Заявка не найдена или не назначена вам")

            if request.status != RequestStatus.ASSIGNED:
                raise ConflictException(
                    f"Нельзя взять в работу заявку со статусом {request.status.value}"
                )

            request.status = RequestStatus.IN_PROGRESS
            request.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def complete_request(self, request_id: int, user: User) -> Request:
        if user.role != UserRole.MASTER:
            raise ForbiddenException("Только мастер может завершать заявки")

        async with self.db.begin_nested():
            query = (
                select(Request)
                .where(and_(Request.id == request_id, Request.assigned_to == user.id))
                .with_for_update()
            )

            result = await self.db.execute(query)
            request = result.scalar_one_or_none()

            if not request:
                raise NotFoundException("Заявка не найдена или не назначена вам")

            if request.status != RequestStatus.IN_PROGRESS:
                raise ConflictException(
                    f"Нельзя завершить заявку со статусом {request.status.value}"
                )

            request.status = RequestStatus.DONE
            request.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def get_available_masters(self, user: User) -> list[User]:
        if user.role != UserRole.DISPATCHER:
            raise ForbiddenException(
                "Только диспетчер может просматривать список мастеров"
            )

        query = select(User).where(User.role == UserRole.MASTER)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_request_by_id(self, request_id: int) -> Request | None:
        query = select(Request).where(Request.id == request_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_master_by_id(self, master_id: int) -> User | None:
        query = select(User).where(
            and_(User.id == master_id, User.role == UserRole.MASTER)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
