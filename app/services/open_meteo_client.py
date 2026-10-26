from typing import Any, Dict, Tuple
import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import (
    ContratoExternoInvalidoError,
    DependenciaNoDisponibleError,
    DependenciaTimeoutError,
    RecursoExternoNoEncontradoError,
)
from app.core.logging import logger
from app.schemas.clima import (
    CoordenadasGeo,
    OrigenDatosClima,
    RespuestaGeocodificacionExterna,
    RespuestaPronosticoExterno,
    ResultadoGeocodificacion,
    ResumenDiaClima,
)
from app.services.cache import CacheTTL


class OpenMeteoClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        cache: CacheTTL[Dict[str, Any]],
        settings: Settings,
    ) -> None:
        self._client = http_client
        self._cache = cache
        self._settings = settings
        self._timeout = httpx.Timeout(
            settings.timeout_externo_read_s,
            connect=settings.timeout_externo_connect_s,
        )

    async def obtener_clima_ciudad(
        self, nombre_ciudad: str
    ) -> Tuple[Dict[str, Any], OrigenDatosClima]:
        dato_en_cache = await self._cache.obtener(nombre_ciudad)
        if dato_en_cache is not None:
            logger.info(
                f"[CACHE HIT] Clima para '{nombre_ciudad}' servido desde cache en memoria"
            )
            return dato_en_cache, OrigenDatosClima.CACHE

        logger.info(
            f"[CACHE MISS] consultando Open-Meteo (2 llamadas encadenadas) para '{nombre_ciudad}'..."
        )
        ubicacion = await self._geocodificar_ciudad(nombre_ciudad)
        pronostico = await self._consultar_pronostico_coordenadas(
            latitud=ubicacion.latitude,
            longitud=ubicacion.longitude,
        )

        dias_resumen = [
            ResumenDiaClima(
                fecha=fecha,
                temp_max_c=t_max,
                temp_min_c=t_min,
            )
            for fecha, t_max, t_min in zip(
                pronostico.daily.time,
                pronostico.daily.temperature_2m_max,
                pronostico.daily.temperature_2m_min,
            )
        ]

        datos_agregados: Dict[str, Any] = {
            "ciudad": ubicacion.name,
            "pais": ubicacion.country or "desconocido",
            "region": ubicacion.admin1,
            "coordenadas": CoordenadasGeo(
                latitud=ubicacion.latitude,
                longitud=ubicacion.longitude,
            ),
            "zona_horaria": pronostico.timezone,
            "temperatura_actual_c": pronostico.current.temperature_2m,
            "humedad_relativa_pct": pronostico.current.relative_humidity_2m,
            "velocidad_viento_kmh": pronostico.current.wind_speed_10m,
            "pronostico_proximos_dias": dias_resumen,
        }

        await self._cache.guardar(nombre_ciudad, datos_agregados)
        return datos_agregados, OrigenDatosClima.API_EXTERNA

    async def _geocodificar_ciudad(
        self, nombre_ciudad: str
    ) -> ResultadoGeocodificacion:
        try:
            respuesta = await self._client.get(
                self._settings.open_meteo_geocoding_url,
                params={
                    "name": nombre_ciudad,
                    "count": 1,
                    "language": "es",
                    "format": "json",
                },
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise DependenciaTimeoutError(
                "timeout al consultar el servicio de geocodificación de Open-Meteo."
            ) from exc
        except httpx.RequestError as exc:
            raise DependenciaNoDisponibleError(
                f"error de red al conectar con Open-Meteo Geocoding: {exc}"
            ) from exc

        if respuesta.status_code != 200:
            raise DependenciaNoDisponibleError(
                f"Open-Meteo Geocoding respondio con codigo inesperado {respuesta.status_code}."
            )

        try:
            datos_geo = RespuestaGeocodificacionExterna.model_validate(respuesta.json())
        except (ValidationError, ValueError) as exc:
            raise ContratoExternoInvalidoError(
                f"respuesta invalida de Open-Meteo Geocoding segun modelo Pydantic v2: {exc}"
            ) from exc

        if not datos_geo.results:
            raise RecursoExternoNoEncontradoError(
                f"no se encontro ninguna ciudad con el nombre '{nombre_ciudad}' en Open-Meteo"
            )

        return datos_geo.results[0]

    async def _consultar_pronostico_coordenadas(
        self, latitud: float, longitud: float
    ) -> RespuestaPronosticoExterno:
        try:
            respuesta = await self._client.get(
                self._settings.open_meteo_forecast_url,
                params={
                    "latitude": latitud,
                    "longitude": longitud,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
                    "daily": "temperature_2m_max,temperature_2m_min",
                    "timezone": "auto",
                    "forecast_days": 3,
                },
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise DependenciaTimeoutError(
                "timeout al consultar el pronóstico meteorologico en Open-Meteo"
            ) from exc
        except httpx.RequestError as exc:
            raise DependenciaNoDisponibleError(
                f"error de red al conectar con Open-Meteo Forecast; {exc}"
            ) from exc

        if respuesta.status_code != 200:
            raise DependenciaNoDisponibleError(
                f"open-Meteo Forecast respondió con codigo inesperado {respuesta.status_code}."
            )

        try:
            return RespuestaPronosticoExterno.model_validate(respuesta.json())
        except (ValidationError, ValueError) as exc:
            raise ContratoExternoInvalidoError(
                f"respuesta invalida de Open-Meteo Forecast segun modelo Pydantic v2 {exc}"
            ) from exc
