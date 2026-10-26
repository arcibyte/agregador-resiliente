
# endpoints para consultar el clima encadenando llamadas a Open-Meteo

import time
from fastapi import APIRouter, Depends, Path

from app.api.dependencies import obtener_open_meteo_client, obtener_sensores_client
from app.schemas.clima import RespuestaClimaCiudad
from app.schemas.common import ErrorRespuesta
from app.schemas.sensores import RespuestaReporteAmbientalCiudad
from app.services.open_meteo_client import OpenMeteoClient
from app.services.sensores_client import SensoresResilienteClient

router = APIRouter(prefix="/v1/ciudades", tags=["Clima (API Externa Open-Meteo)"])


@router.get(
    "/{nombre}/clima",
    response_model=RespuestaClimaCiudad,
    summary="obtiene ubicacion y pronóstico meteorologico encadenando dos llamadas a Open-Meteo",
    responses={
        200: {"description": "datos meteorologicos combinados obtenidos correctamente"},
        404: {
            "model": ErrorRespuesta,
            "description": "la ciudad solicitada no existe en Open-Meteo",
        },
        422: {"description": "parametros de ruta invalidos"},
        502: {
            "model": ErrorRespuesta,
            "description": "error de comunicacion o esquema invalido desde la API externa",
        },
        504: {
            "model": ErrorRespuesta,
            "description": "timeout al comunicarse con la API externa",
        },
    },
)
async def obtener_clima_ciudad(
    nombre: str = Path(
        ...,
        min_length=2,
        max_length=80,
        description="nombre de la ciudad a consultar (ej. Bogota, Bucaramanga, Madrid)",
    ),
    clima_client: OpenMeteoClient = Depends(obtener_open_meteo_client),
) -> RespuestaClimaCiudad:
    """encadena Geocoding + Forecast en Open-Meteo, usando caché en memoria con TTL."""
    inicio = time.perf_counter()
    datos, origen = await clima_client.obtener_clima_ciudad(nombre)
    latencia_ms = round((time.perf_counter() - inicio) * 1000.0, 2)
    return RespuestaClimaCiudad(
        **datos,
        origen_datos=origen,
        latencia_ms=latencia_ms,
    )


@router.get(
    "/{nombre}/reporte-ambiental",
    response_model=RespuestaReporteAmbientalCiudad,
    summary="combina en una sola respuesta el clima externo (Open-Meteo) y el inventario paginado de sensores",
    responses={
        200: {"description": "reporte ambiental combinado generado exitosamente"},
        404: {"model": ErrorRespuesta, "description": "ciudad no encontrada"},
        502: {"model": ErrorRespuesta, "description": "fallo en alguna dependencia"},
        504: {"model": ErrorRespuesta, "description": "timeout en alguna dependencia"},
    },
)
async def obtener_reporte_ambiental(
    nombre: str = Path(..., min_length=2, max_length=80),
    clima_client: OpenMeteoClient = Depends(obtener_open_meteo_client),
    sensores_client: SensoresResilienteClient = Depends(obtener_sensores_client),
) -> RespuestaReporteAmbientalCiudad:
    """integra los datos meteorologicos de Open-Meteo con los sensores del servicio inestable"""
    inicio = time.perf_counter()
    datos_clima, origen = await clima_client.obtener_clima_ciudad(nombre)
    latencia_ms = round((time.perf_counter() - inicio) * 1000.0, 2)
    clima_ciudad = RespuestaClimaCiudad(
        **datos_clima,
        origen_datos=origen,
        latencia_ms=latencia_ms,
    )
    resumen_sensores = await sensores_client.listar_todos_los_sensores()
    return RespuestaReporteAmbientalCiudad(
        clima_ciudad=clima_ciudad,
        resumen_sensores_locales=resumen_sensores,
    )
