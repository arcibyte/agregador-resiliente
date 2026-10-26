import asyncio
import random
from typing import Any, Dict, List, Optional

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import (
    ContratoExternoInvalidoError,
    DependenciaNoDisponibleError,
    DependenciaTimeoutError,
    PeticionExternaInvalidaError,
    RecursoExternoNoEncontradoError,
)
from app.core.logging import logger
from app.schemas.sensores import (
    LecturaSensorExterna,
    PaginaSensoresExterna,
    RespuestaListadoSensores,
    SensorItem,
)


class SensoresResilienteClient:
    """cliente HTTP con tolerancia a fallos transitorios hacia servicio_inestable.py"""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        settings: Settings,
    ) -> None:
        self._client = http_client
        self._settings = settings
        self._timeout = httpx.Timeout(
            settings.timeout_inestable_read_s,
            connect=settings.timeout_inestable_connect_s,
        )

    async def listar_todos_los_sensores(
        self, cursor_inicial: Optional[str] = None
    ) -> RespuestaListadoSensores:
        sensores_acumulados: List[SensorItem] = []
        cursor_actual = cursor_inicial
        paginas_recorridas = 0

        while True:
            params = {"cursor": cursor_actual} if cursor_actual is not None else None
            respuesta = await self._get_con_reintentos("/sensores", params=params)

            try:
                pagina = PaginaSensoresExterna.model_validate(respuesta.json())
            except (ValidationError, ValueError) as exc:
                raise ContratoExternoInvalidoError(
                    f"respuesta de paginación malformada desde el servicio de sensores: {exc}"
                ) from exc

            sensores_acumulados.extend(pagina.sensores)
            paginas_recorridas += 1

            if pagina.siguiente is None:
                break
            cursor_actual = pagina.siguiente

        return RespuestaListadoSensores(
            total_sensores=len(sensores_acumulados),
            paginas_recorridas=paginas_recorridas,
            sensores=sensores_acumulados,
        )

    async def obtener_lectura_sensor(self, sensor_id: str) -> LecturaSensorExterna:
        """consulta la lectura actual de un sensor en GET /sensores/{id}/lectura."""
        respuesta = await self._get_con_reintentos(f"/sensores/{sensor_id}/lectura")
        try:
            return LecturaSensorExterna.model_validate(respuesta.json())
        except (ValidationError, ValueError) as exc:
            raise ContratoExternoInvalidoError(
                f"formato de lectura inválido desde el servicio de sensores: {exc}"
            ) from exc

    async def _get_con_reintentos(
        self, ruta: str, params: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        url = f"{self._settings.servicio_inestable_url}{ruta}"
        max_intentos = self._settings.max_intentos
        base_backoff = self._settings.base_backoff_s
        ultimo_fallo_fue_timeout = False

        for intento in range(1, max_intentos + 1):
            try:
                logger.info(
                    f"[Intento {intento}/{max_intentos}] GET {url} params={params}"
                )
                respuesta = await self._client.get(
                    url, params=params, timeout=self._timeout
                )
                codigo = respuesta.status_code

                #rspuesta exitosa
                if codigo == 200:
                    logger.info(
                        f"[Intento {intento}/{max_intentos}] ÉXITO 200 en {ruta} (params={params})"
                    )
                    return respuesta

                # 2 errores definitivos del cliente (400, 404)
                if codigo in (400, 404):
                    logger.warning(
                        f"[Intento {intento}/{max_intentos}] Error {codigo} legítimo en {ruta}. "
                        "no es reintentable; abortando reintentos inmediatamente"
                    )
                    detalle = self._extraer_detalle_error(respuesta)
                    if codigo == 400:
                        raise PeticionExternaInvalidaError(detalle)
                    raise RecursoExternoNoEncontradoError(detalle)

                # 3 Limite de peticiones (429)
                if codigo == 429:
                    ultimo_fallo_fue_timeout = False
                    if intento == max_intentos:
                        logger.error(
                            f"[Intento {intento}/{max_intentos}] se agotaron los intentos tras recibir 429 en {ruta}."
                        )
                        break

                    espera = self._calcular_espera_429(
                        respuesta=respuesta, intento=intento, base_backoff=base_backoff
                    )
                    await asyncio.sleep(espera)
                    continue

                # 4 fallo transitorio del servidor (503) de Backoff exponencial con Full Jitter
                if codigo == 503:
                    ultimo_fallo_fue_timeout = False
                    if intento == max_intentos:
                        logger.error(
                            f"[Intento {intento}/{max_intentos}] se agotaron los intentos tras recibir 503 en {ruta}."
                        )
                        break

                    techo_backoff = base_backoff * (2 ** (intento - 1))
                    espera = random.uniform(0.10, max(0.15, techo_backoff))
                    logger.warning(
                        f"[Intento {intento}/{max_intentos}] Recibido 503 Service Unavailable en {ruta}. "
                        f"Backoff exponencial con jitter (techo={techo_backoff:.2f}s): esperando {espera:.2f}s..."
                    )
                    await asyncio.sleep(espera)
                    continue

                # cualquier otro código inesperado de la dependencia
                raise DependenciaNoDisponibleError(
                    f"El servicio de sensores respondio con estado inesperado {codigo}."
                )

            except httpx.TimeoutException:
                ultimo_fallo_fue_timeout = True
                if intento == max_intentos:
                    logger.error(
                        f"[Intento {intento}/{max_intentos}] Timeout definitivo tras agotar {max_intentos} intentos en {ruta}."
                    )
                    break

                techo_backoff = base_backoff * (2 ** (intento - 1))
                espera = random.uniform(0.10, max(0.15, techo_backoff))
                logger.warning(
                    f"[Intento {intento}/{max_intentos}] Timeout detectado (> {self._timeout.read}s) en {ruta}. "
                    f"Backoff exponencial con jitter (techo={techo_backoff:.2f}s): esperando {espera:.2f}s..."
                )
                await asyncio.sleep(espera)

            except httpx.RequestError as exc:
                ultimo_fallo_fue_timeout = False
                if intento == max_intentos:
                    logger.error(
                        f"[Intento {intento}/{max_intentos}] error de conexion definitivo con el servicio inestable: {exc}"
                    )
                    break

                techo_backoff = base_backoff * (2 ** (intento - 1))
                espera = random.uniform(0.10, max(0.15, techo_backoff))
                logger.warning(
                    f"[Intento {intento}/{max_intentos}] error de red ({exc}). "
                    f"Reintentando en {espera:.2f}s..."
                )
                await asyncio.sleep(espera)

        if ultimo_fallo_fue_timeout:
            raise DependenciaTimeoutError(
                f"El servicio inestable de sensores excedio el tiempo de espera tras {max_intentos} intentos"
            )
        raise DependenciaNoDisponibleError(
            f"El servicio inestable de sensores no estuvo disponible tras {max_intentos} intentos"
        )

    @staticmethod
    def _extraer_detalle_error(respuesta: httpx.Response) -> str:
        """extrae el mensaje de error del cuerpo JSON devuelto por el servicio inestable"""
        try:
            cuerpo = respuesta.json()
            return str(
                cuerpo.get("detail") or cuerpo.get("detalle") or respuesta.text
            )
        except Exception:
            return respuesta.text

    @staticmethod
    def _calcular_espera_429(
        respuesta: httpx.Response, intento: int, base_backoff: float
    ) -> float:
        retry_after_hdr = respuesta.headers.get("Retry-After")
        if retry_after_hdr is not None:
            try:
                espera_base = float(retry_after_hdr)
            except ValueError:
                espera_base = base_backoff * (2 ** (intento - 1))
            # Jitter positivo pequeño (0.10 s a 0.30 s) sobre Retry-After para garantizar
            # que el reloj monotónico del servidor haya levantado el bloqueo por IP.
            espera = espera_base + random.uniform(0.10, 0.30)
            logger.warning(
                f"[Intento {intento}] Recibido 429 Too Many Requests con "
                f"cabecera Retry-After={retry_after_hdr}s. Respetando espera de {espera:.2f}s..."
            )
            return espera

        techo = base_backoff * (2 ** (intento - 1))
        espera = random.uniform(0.10, max(0.15, techo))
        logger.warning(
            f"[Intento {intento}] Recibido 429 sin cabecera Retry-After. "
            f"esperando {espera:.2f}s (backoff con jitter)..."
        )
        return espera
