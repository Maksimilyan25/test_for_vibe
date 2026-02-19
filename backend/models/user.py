from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Enum
import enum


from typing import TYPE_CHECKING
from core.database import Base

if TYPE_CHECKING:
    from models.request import Request


class UserRole(str, enum.Enum):
    DISPATCHER = "dispatcher"
    MASTER = "master"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    # Связи
    assigned_requests: Mapped[list["Request"]] = relationship(
        "Request", back_populates="assigned_master", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"User {self.username} ({self.role.value})"
