"""
inicializa un unico pool de conexiones HTTPX compartido, 
la cache con TTL y el almacén de idempotencia, registrando los routers y manejadores de errores
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

import httpx
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import registrar_manejadores_excepciones
from app.core.logging import logger
from app.services.cache import CacheTTL
from app.services.idempotency import IdempotencyStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    limites_pool = httpx.Limits(max_keepalive_connections=20, max_connections=100)

    async with httpx.AsyncClient(limits=limites_pool) as http_client:
        app.state.http_client = http_client
        app.state.cache_clima = CacheTTL[Dict[str, Any]](
            ttl_segundos=settings.cache_ttl_segundos
        )
        app.state.idempotency_store = IdempotencyStore()
        logger.info(
            f"agregador resiliente iniciado,servicio inestable configurado en: "
            f"{settings.servicio_inestable_url}"
        )
        yield
        logger.info("cerrando recursos y pool de conexiones HTTP del agregador...")


def create_app() -> FastAPI:
    """crea y configura la aplicacion FastAPI siguiendo el patrón Application Factory."""
    settings = get_settings()
    aplicacion = FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # fallback de estado para entornos de test que no ejecuten lifespan explicitamente
    aplicacion.state.http_client = httpx.AsyncClient()
    aplicacion.state.cache_clima = CacheTTL[Dict[str, Any]](
        ttl_segundos=settings.cache_ttl_segundos
    )
    aplicacion.state.idempotency_store = IdempotencyStore()

    registrar_manejadores_excepciones(aplicacion)
    aplicacion.include_router(api_router)
    return aplicacion


app = create_app()
