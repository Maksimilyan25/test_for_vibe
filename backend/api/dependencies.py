from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession


from core.database import get_db
from services.user_service import UserService
from models.user import User, UserRole
from core.security import decode_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """
    Получение текущего пользователя из JWT токена
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Декодируем токен
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    username: str = payload.get("sub")
    if not username:
        raise credentials_exception

    # Получаем пользователя из БД
    service = UserService(db)
    user = await service.get_user_by_username(username)

    if not user:
        raise credentials_exception

    return user


async def get_current_master(current_user: User = Depends(get_current_user)) -> User:
    """
    Проверка что пользователь - мастер
    """
    if current_user.role != UserRole.MASTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Master role required.",
        )
    return current_user


async def get_current_dispatcher(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Проверка что пользователь - диспетчер
    """
    if current_user.role != UserRole.DISPATCHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Dispatcher role required.",
        )
    return current_user
