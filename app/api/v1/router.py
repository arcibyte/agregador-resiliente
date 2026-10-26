# enrutador principal de los endpoints
from fastapi import APIRouter

from app.api.v1 import alertas, clima, salud, sensores

api_router = APIRouter()
api_router.include_router(salud.router)
api_router.include_router(clima.router)
api_router.include_router(sensores.router)
api_router.include_router(alertas.router)
