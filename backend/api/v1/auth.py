from api.dependencies import get_current_user
from core.database import SessionDep
from core.security import create_access_token
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from models.user import User
from schemas.user import Token, UserCreate, UserResponse
from services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Аутентификация и авторизация"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="""
    Создает нового пользователя в системе.

    - **username**: уникальное имя пользователя (от 3 до 50 символов)
    - **full_name**: полное имя пользователя
    - **role**: роль пользователя (master/dispatcher)
    - **password**: пароль (от 6 символов)

    Возвращает данные созданного пользователя без пароля.
    """,
)
async def register(
    user_data: UserCreate,
    db: SessionDep,
):
    """
    Регистрация нового пользователя
    """
    service = UserService(db)
    try:
        user = await service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/login",
    response_model=Token,
    summary="Вход в систему",
    description="""
    Аутентификация пользователя и получение JWT токена.

    - **username**: имя пользователя
    - **password**: пароль

    Возвращает JWT токен, который нужно передавать в заголовке Authorization:
    ```
    Authorization: Bearer <токен>
    ```

    Токен действителен в течение 30 минут.
    """,
)
async def login(db: SessionDep, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Вход в систему, получение JWT токена
    """
    service = UserService(db)
    user = await service.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "role": user.role.value,
            "full_name": user.full_name,
        }
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Информация о текущем пользователе",
    description="""
    Возвращает информацию о текущем аутентифицированном пользователе.

    Требует наличие валидного JWT токена в заголовке Authorization.
    """,
)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Получить информацию о текущем пользователе
    """
    return current_user


@router.post(
    "/logout",
    summary="Выход из системы",
    description="""
    Выход из системы.

    Так как используется JWT, сервер не может аннулировать токен.
    Клиент должен самостоятельно удалить токен на своей стороне.

    Возвращает сообщение об успешном выходе.
    """,
)
async def logout():
    """
    Выход из системы (на клиенте просто удаляют токен)
    """
    return {"message": "Выход выполнен успешно. Удалите токен на стороне клиента."}
