from typing import List, Optional

from core.security import get_password_hash, verify_password
from models.user import User, UserRole
from schemas.user import UserCreate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def authenticate_user(self, username: str, password: str) -> User | None:
        """Аутентификация пользователя"""
        user = await self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def get_all_masters(self) -> list[User]:
        result = await self.db.execute(select(User).where(User.role == UserRole.MASTER))
        return list(result.scalars().all())

    async def create_user(self, user_data: UserCreate) -> User:
        # Проверяем, не существует ли уже такой пользователь
        existing = await self.get_user_by_username(user_data.username)
        if existing:
            raise ValueError(
                f"Пользователь с именем {user_data.username} уже существует"
            )

        # Хешируем пароль
        hashed_password = get_password_hash(user_data.password)

        user = User(
            username=user_data.username,
            full_name=user_data.full_name,
            role=user_data.role,
            hashed_password=hashed_password,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
