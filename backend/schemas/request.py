# app/schemas/request.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from models.request import RequestStatus


class RequestBase(BaseModel):
    client_name: str = Field(
        ..., min_length=1, max_length=100, description="Имя клиента"
    )
    phone: str = Field(..., min_length=1, max_length=20, description="Телефон")
    address: str = Field(..., min_length=1, max_length=200, description="Адрес")
    problem_text: str = Field(..., min_length=1, description="Описание проблемы")


class RequestCreate(RequestBase):
    """Схема для создания заявки (мастер не назначается при создании)"""

    pass


class RequestUpdate(BaseModel):
    client_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Имя клиента"
    )
    phone: Optional[str] = Field(
        None, min_length=1, max_length=20, description="Телефон"
    )
    address: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Адрес"
    )
    problem_text: Optional[str] = Field(
        None, min_length=1, description="Описание проблемы"
    )
    status: Optional[RequestStatus] = Field(None, description="Статус заявки")
    assigned_to: Optional[int] = Field(
        None, description="ID назначенного мастера (может быть пустым)"
    )


class RequestActionAssign(BaseModel):
    master_id: int = Field(..., description="ID мастера для назначения")


class RequestInDB(RequestBase):
    id: int = Field(..., description="ID заявки")
    status: RequestStatus = Field(..., description="Статус заявки")
    assigned_to: Optional[int] = Field(
        None, description="ID назначенного мастера (null если мастер не назначен)"
    )
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(
        None, description="Дата последнего обновления"
    )

    model_config = ConfigDict(from_attributes=True)


class RequestWithMaster(RequestInDB):
    assigned_master_name: Optional[str] = Field(
        None, description="Имя назначенного мастера (null если мастер не назначен)"
    )
    assigned_master_username: Optional[str] = Field(
        None, description="Username назначенного мастера (null если мастер не назначен)"
    )


class RequestFilterParams(BaseModel):
    status: Optional[RequestStatus] = Field(None, description="Фильтр по статусу")
    master_id: Optional[int] = Field(
        None, description="Фильтр по мастеру (показывает заявки только этого мастера)"
    )
    skip: int = Field(0, ge=0, description="Сколько пропустить")
    limit: int = Field(100, ge=1, le=100, description="Сколько вернуть")
