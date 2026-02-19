# app/core/logger.py
import logging


def setup_logger():
    """Настройка основного логгера приложения"""
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)

    # Форматтер
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Добавляем обработчик только если его нет
    if not logger.handlers:
        logger.addHandler(console_handler)

    return logger


# Инициализация логгера при импорте
logger = setup_logger()
