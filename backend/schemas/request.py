from datetime import datetime
from typing import Optional

from models.request import RequestStatus
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RequestBase(BaseModel):
    client_name: str = Field(
        ..., min_length=1, max_length=100, description="Имя клиента"
    )
    phone: int = Field(
        ..., description="Телефон (только цифры)", gt=0
    )  # Изменено на int
    address: str = Field(..., min_length=1, max_length=200, description="Адрес")
    problem_text: str = Field(..., min_length=1, description="Описание проблемы")

    @field_validator("client_name")
    @classmethod
    def validate_client_name(cls, v: str) -> str:
        """Просто проверяем что не пустое"""
        if not v or not v.strip():
            raise ValueError("Имя не может быть пустым")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: int) -> int:
        """Проверяем что телефон положительное число"""
        if v <= 0:
            raise ValueError("Телефон должен быть положительным числом")

        # Опционально: проверка длины номера (например, от 10 до 15 цифр)
        phone_str = str(v)
        if len(phone_str) < 10 or len(phone_str) > 15:
            raise ValueError("Телефон должен содержать от 10 до 15 цифр")

        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Просто проверяем что не пустое"""
        if not v or not v.strip():
            raise ValueError("Адрес не может быть пустым")
        return v.strip()

    @field_validator("problem_text")
    @classmethod
    def validate_problem_text(cls, v: str) -> str:
        """Просто проверяем что не пустое"""
        if not v or not v.strip():
            raise ValueError("Описание проблемы не может быть пустым")
        return v.strip()


class RequestCreate(RequestBase):
    """Схема для создания заявки"""

    pass


class RequestUpdate(BaseModel):
    client_name: str | None = Field(
        None, min_length=1, max_length=100, description="Имя клиента"
    )
    phone: int | None = Field(  # Изменено на Optional[int]
        None, description="Телефон (только цифры)", gt=0
    )
    address: str | None = Field(None, min_length=1, max_length=200, description="Адрес")
    problem_text: str | None = Field(
        None, min_length=1, description="Описание проблемы"
    )
    status: RequestStatus | None = Field(None, description="Статус заявки")
    assigned_to: int | None = Field(
        None, description="ID назначенного мастера (может быть пустым)"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: int | None) -> int | None:
        """Проверяем телефон если он предоставлен"""
        if v is not None:
            if v <= 0:
                raise ValueError("Телефон должен быть положительным числом")

            # Опционально: проверка длины номера
            phone_str = str(v)
            if len(phone_str) < 10 or len(phone_str) > 15:
                raise ValueError("Телефон должен содержать от 10 до 15 цифр")

        return v


class RequestActionAssign(BaseModel):
    master_id: int = Field(..., description="ID мастера для назначения")


class RequestInDB(RequestBase):
    id: int = Field(..., description="ID заявки")
    status: RequestStatus = Field(..., description="Статус заявки")
    assigned_to: int | None = Field(
        None, description="ID назначенного мастера (null если мастер не назначен)"
    )
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime | None = Field(None, description="Дата последнего обновления")

    model_config = ConfigDict(from_attributes=True)


class RequestWithMaster(RequestInDB):
    assigned_master_name: str | None = Field(
        None, description="Имя назначенного мастера (null если мастер не назначен)"
    )
    assigned_master_username: str | None = Field(
        None, description="Username назначенного мастера (null если мастер не назначен)"
    )


class RequestFilterParams(BaseModel):
    status: RequestStatus | None = Field(None, description="Фильтр по статусу")
    master_id: int | None = Field(
        None, description="Фильтр по мастеру (показывает заявки только этого мастера)"
    )
    skip: int = Field(0, ge=0, description="Сколько пропустить")
    limit: int = Field(100, ge=1, le=100, description="Сколько вернуть")
