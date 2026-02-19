# core/exceptions.py
from fastapi import HTTPException, status


class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Ресурс не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BusinessLogicException(HTTPException):
    def __init__(self, detail: str = "Ошибка бизнес-логики"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "Доступ запрещен"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Не авторизован"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
