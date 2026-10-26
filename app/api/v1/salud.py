
# endpoint de comprobación de vida del servicio agregador


from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.common import RespuestaSalud

router = APIRouter(tags=["Operación"])


@router.get(
    "/salud",
    response_model=RespuestaSalud,
    summary="comprobacion de vida del servicio agregador",
)
async def verificar_salud(
    settings: Settings = Depends(get_settings),
) -> RespuestaSalud:
    return RespuestaSalud(
        estado="ok",
        servicio_inestable_url=settings.servicio_inestable_url,
        cache_ttl_segundos=settings.cache_ttl_segundos,
        marca_tiempo=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
