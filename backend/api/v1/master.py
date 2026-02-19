from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from core.database import get_db
from schemas.request import (
    RequestInDB,
    RequestWithMaster,
    RequestFilterParams,
)
from services.request_service import RequestService
from api.dependencies import get_current_master
from models.user import User
from models.request import RequestStatus

router = APIRouter(prefix="/master", tags=["Мастер"])


@router.get(
    "/requests",
    response_model=List[RequestWithMaster],
    summary="Список моих заявок",
    description="Получение списка заявок, назначенных на текущего мастера",
)
async def get_my_requests(
    status: Optional[str] = Query(
        None,
        pattern="^(new|assigned|in_progress|done|canceled)$",
        description="Фильтр по статусу",
    ),
    skip: int = Query(0, ge=0, description="Сколько пропустить"),
    limit: int = Query(100, ge=1, le=100, description="Сколько вернуть"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_master),
):
    """
    Получение списка заявок, назначенных на текущего мастера.
    Мастер видит только те заявки, где он назначен исполнителем.
    """
    service = RequestService(db)

    # Преобразуем статус в enum
    status_enum = None
    if status:
        status_enum = RequestStatus(status)

    filters = RequestFilterParams(
        status=status_enum, master_id=current_user.id, skip=skip, limit=limit
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


@router.post(
    "/requests/{request_id}/take",
    response_model=RequestInDB,
    summary="Взять в работу",
    description="Взять заявку в работу (перевод из assigned в in_progress)",
)
async def take_request_to_work(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_master),
):
    """
    Действие мастера: "Взять в работу"

    Переводит заявку из статуса 'assigned' в 'in_progress'.
    Доступно только для заявок, назначенных на текущего мастера.
    """
    service = RequestService(db)
    request = await service.take_to_work(request_id, current_user)
    return request


@router.post(
    "/requests/{request_id}/complete",
    response_model=RequestInDB,
    summary="Завершить",
    description="Завершить заявку (перевод из in_progress в done)",
)
async def complete_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_master),
):
    """
    Действие мастера: "Завершить"

    Переводит заявку из статуса 'in_progress' в 'done'.
    Доступно только для заявок, назначенных на текущего мастера.
    """
    service = RequestService(db)
    request = await service.complete_request(request_id, current_user)
    return request


@router.get(
    "/requests/{request_id}",
    response_model=RequestWithMaster,
    summary="Детали заявки",
    description="Получение детальной информации по заявке (только свои)",
)
async def get_request_details(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_master),
):
    """
    Получение детальной информации по конкретной заявке.
    Доступно только для заявок, назначенных на текущего мастера.
    """
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


@router.get(
    "/stats",
    response_model=dict,
    summary="Статистика по моим заявкам",
    description="Получение статистики по заявкам текущего мастера",
)
async def get_my_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_master)
):
    """
    Получение статистики по заявкам мастера:
    - всего назначено
    - в работе
    - завершено
    - отменено
    """
    service = RequestService(db)

    filters = RequestFilterParams(master_id=current_user.id, skip=0, limit=100)

    requests, total = await service.get_requests(filters, current_user)

    stats = {
        "total": total,
        "new": 0,
        "assigned": 0,
        "in_progress": 0,
        "done": 0,
        "canceled": 0,
    }

    for req in requests:
        stats[req.status.value] += 1

    return stats
