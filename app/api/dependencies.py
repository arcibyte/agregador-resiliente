from typing import Any, Dict
import httpx
from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.services.cache import CacheTTL
from app.services.idempotency import IdempotencyStore
from app.services.open_meteo_client import OpenMeteoClient
from app.services.sensores_client import SensoresResilienteClient


def obtener_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def obtener_cache_clima(request: Request) -> CacheTTL[Dict[str, Any]]:
    return request.app.state.cache_clima


def obtener_idempotency_store(request: Request) -> IdempotencyStore:
    return request.app.state.idempotency_store


def obtener_open_meteo_client(
    http_client: httpx.AsyncClient = Depends(obtener_http_client),
    cache: CacheTTL[Dict[str, Any]] = Depends(obtener_cache_clima),
    settings: Settings = Depends(get_settings),
) -> OpenMeteoClient:
    return OpenMeteoClient(
        http_client=http_client,
        cache=cache,
        settings=settings,
    )


def obtener_sensores_client(
    http_client: httpx.AsyncClient = Depends(obtener_http_client),
    settings: Settings = Depends(get_settings),
) -> SensoresResilienteClient:
    return SensoresResilienteClient(
        http_client=http_client,
        settings=settings,
    )
