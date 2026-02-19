from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from api.v1 import auth, requests, dispatcher, master

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(requests.router, prefix=settings.API_V1_PREFIX)
app.include_router(master.router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    return {
        "message": "Repair Service API",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}
