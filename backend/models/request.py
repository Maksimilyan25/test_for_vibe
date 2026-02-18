from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Enum, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class RequestStatus(str, enum.Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELED = "canceled"


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    problem_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), nullable=False, default=RequestStatus.NEW
    )

    assigned_to: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Связи
    assigned_master: Mapped[Optional["User"]] = relationship(
        "User", back_populates="assigned_requests", lazy="joined"
    )

    def __repr__(self) -> str:
        return f"Request {self.id} - {self.client_name} ({self.status.value})"
