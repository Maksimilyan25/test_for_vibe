from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from core.database import get_db
from schemas.request import (
    RequestCreate,
    RequestInDB,
    RequestWithMaster,
    RequestFilterParams,
    RequestActionAssign,
)
from schemas.user import UserResponse
from services.request_service import RequestService
from api.dependencies import get_current_user, get_current_dispatcher
from models.user import User, UserRole

router = APIRouter(prefix="/requests", tags=["Заявки"])


@router.post(
    "/",
    response_model=RequestInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Создать заявку",
    description="Создание новой заявки. Доступно только диспетчеру.",
)
async def create_request(
    request_data: RequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_dispatcher),
):
    """Создание новой заявки (только диспетчер)"""
    service = RequestService(db)
    request = await service.create_request(request_data, current_user)
    return request


@router.get(
    "/",
    response_model=List[RequestWithMaster],
    summary="Список заявок",
    description="Получение списка заявок с фильтрацией. Диспетчер видит все, мастер - только свои.",
)
async def get_requests(
    status: Optional[str] = Query(
        None,
        pattern="^(new|assigned|in_progress|done|canceled)$",
        description="Фильтр по статусу",
    ),
    master_id: Optional[int] = Query(
        None, description="Фильтр по мастеру (только для диспетчера)"
    ),
    skip: int = Query(0, ge=0, description="Сколько пропустить"),
    limit: int = Query(100, ge=1, le=100, description="Сколько вернуть"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получение списка заявок"""
    service = RequestService(db)

    # Преобразуем статус в enum
    status_enum = None
    if status:
        from models.request import RequestStatus

        status_enum = RequestStatus(status)

    filters = RequestFilterParams(
        status=status_enum, master_id=master_id, skip=skip, limit=limit
    )

    requests, total = await service.get_requests(filters, current_user)

    # Обогащаем данными о мастере
    result = []
    for req in requests:
        req_dict = {
            "id": req.id,
            "client_name": req.client_name,
            "phone": req.phone,
            "address": req.address,
            "problem_text": req.problem_text,
            "status": req.status,
            "assigned_to": req.assigned_to,
            "created_at": req.created_at,
            "updated_at": req.updated_at,
        }

        if req.assigned_master:
            req_dict["assigned_master_name"] = req.assigned_master.full_name
            req_dict["assigned_master_username"] = req.assigned_master.username

        result.append(RequestWithMaster.model_validate(req_dict))

    return result


@router.get(
    "/{request_id}",
    response_model=RequestWithMaster,
    summary="Получить заявку",
    description="Получение заявки по ID. Мастер видит только свои заявки.",
)
async def get_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получение заявки по ID"""
    service = RequestService(db)
    request = await service.get_request(request_id, current_user)

    req_dict = {
        "id": request.id,
        "client_name": request.client_name,
        "phone": request.phone,
        "address": request.address,
        "problem_text": request.problem_text,
        "status": request.status,
        "assigned_to": request.assigned_to,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
    }

    if request.assigned_master:
        req_dict["assigned_master_name"] = request.assigned_master.full_name
        req_dict["assigned_master_username"] = request.assigned_master.username

    return RequestWithMaster.model_validate(req_dict)


@router.post(
    "/{request_id}/assign",
    response_model=RequestInDB,
    summary="Назначить мастера",
    description="Назначение мастера на заявку. Доступно только диспетчеру.",
)
async def assign_master(
    request_id: int,
    assign_data: RequestActionAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_dispatcher),
):
    """Назначить мастера на заявку"""
    service = RequestService(db)
    request = await service.assign_master(
        request_id, assign_data.master_id, current_user
    )
    return request


@router.post(
    "/{request_id}/cancel",
    response_model=RequestInDB,
    summary="Отменить заявку",
    description="Отмена заявки. Диспетчер может отменить любую, мастер - только свою.",
)
async def cancel_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Отменить заявку"""
    service = RequestService(db)
    request = await service.cancel_request(request_id, current_user)
    return request


@router.get(
    "/masters/available",
    response_model=List[UserResponse],
    summary="Список мастеров",
    description="Получить список всех мастеров для назначения. Доступно только диспетчеру.",
)
async def get_available_masters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_dispatcher),
):
    """Получить список всех мастеров"""
    service = RequestService(db)
    masters = await service.get_available_masters(current_user)
    return masters
