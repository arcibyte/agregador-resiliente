
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from app.core.exceptions import ConflictoIdempotenciaError
from app.core.logging import logger
from app.schemas.alertas import RespuestaAlerta, SolicitudCrearAlerta


class IdempotencyStore:

    def __init__(self) -> None:
        self._registros: Dict[str, Tuple[Dict[str, Any], RespuestaAlerta]] = {}
        self._lock = asyncio.Lock()

    async def registrar_o_recuperar_alerta(
        self, idempotency_key: str, solicitud: SolicitudCrearAlerta
    ) -> Tuple[RespuestaAlerta, bool]:
        payload_actual = solicitud.model_dump(mode="json")

        async with self._lock:
            if idempotency_key in self._registros:
                payload_previo, alerta_previa = self._registros[idempotency_key]
                if payload_previo != payload_actual:
                    logger.warning(
                        f"[IDEMPOTENCIA] Conflicto 409: la clave '{idempotency_key}' "
                        "se reutilizo con un cuerpo de petición diferente"
                    )
                    raise ConflictoIdempotenciaError(
                        "la clave Idempotency-Key ya fue utilizada con parametros de alerta distintos"
                    )

                logger.info(
                    f"[IDEMPOTENCIA] Peticion repetida detectada para clave '{idempotency_key}'. "
                    f"devolviendo alerta existente {alerta_previa.alerta_id} sin duplicar efectos"
                )
                return alerta_previa, True

            nueva_alerta = RespuestaAlerta(
                alerta_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                sensor_id=solicitud.sensor_id,
                severidad=solicitud.severidad,
                mensaje=solicitud.mensaje,
                creada_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                idempotency_key=idempotency_key,
            )
            self._registros[idempotency_key] = (payload_actual, nueva_alerta)
            logger.info(
                f"[IDEMPOTENCIA] nueva alerta creada; {nueva_alerta.alerta_id} "
                f"(clave='{idempotency_key}')."
            )
            return nueva_alerta, False
