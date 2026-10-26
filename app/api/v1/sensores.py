
# endpoints resilientes que consumen el servicio inestable de sensores

from typing import Optional
from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import obtener_sensores_client
from app.schemas.common import ErrorRespuesta
from app.schemas.sensores import LecturaSensorExterna, RespuestaListadoSensores
from app.services.sensores_client import SensoresResilienteClient

router = APIRouter(prefix="/v1/sensores", tags=["Sensores (Servicio Inestable)"])


@router.get(
    "",
    response_model=RespuestaListadoSensores,
    summary="eecorre la paginacion completa de sensores tolerando fallos transitorios",
    responses={
        200: {"description": "lista completa de sensores recopilada exitosamente"},
        400: {
            "model": ErrorRespuesta,
            "description": "cursor invalido reportado por el servicio de sensores (no se reintenta)",
        },
        502: {
            "model": ErrorRespuesta,
            "description": "el servicio inestable falló tras agotar todos los reintentos",
        },
        504: {
            "model": ErrorRespuesta,
            "description": "Timeout en el servicio inestable tras agotar los reintentos",
        },
    },
)
async def listar_todos_los_sensores(
    cursor_inicial: Optional[str] = Query(
        default=None,
        description="cursor opcional para iniciar desde una posicion específica (util para verificar errores 400)",
    ),
    sensores_client: SensoresResilienteClient = Depends(obtener_sensores_client),
) -> RespuestaListadoSensores:
    return await sensores_client.listar_todos_los_sensores(
        cursor_inicial=cursor_inicial
    )


@router.get(
    "/{sensor_id}/lectura",
    response_model=LecturaSensorExterna,
    summary="consulta la lectura actual de un sensor específico con reintentos selectivos",
    responses={
        200: {"description": "lectura del sensor obtenida exitosamente"},
        404: {
            "model": ErrorRespuesta,
            "description": "el sensor solicitado no existe (no se reintenta)",
        },
        502: {
            "model": ErrorRespuesta,
            "description": "el servicio inestable falló tras agotar los reintentos",
        },
        504: {
            "model": ErrorRespuesta,
            "description": "Timeout en el servicio inestable tras agotar los reintentos",
        },
    },
)
async def obtener_lectura_sensor(
    sensor_id: str = Path(
        ...,
        min_length=2,
        max_length=20,
        description="identificador del sensor (ej. S-001)",
    ),
    sensores_client: SensoresResilienteClient = Depends(obtener_sensores_client),
) -> LecturaSensorExterna:
    return await sensores_client.obtener_lectura_sensor(sensor_id=sensor_id)
