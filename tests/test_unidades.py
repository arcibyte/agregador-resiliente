#pruebas unitarias aisladas para los servicios de caché TTL e idempotencia, Se pueden ejecutar directamente con
"""python -m unittest discover -s tests -p "test_*.py" -v
    """

import asyncio
import unittest

from app.core.exceptions import ConflictoIdempotenciaError
from app.schemas.alertas import SeveridadAlerta, SolicitudCrearAlerta
from app.services.cache import CacheTTL
from app.services.idempotency import IdempotencyStore


class TestServiciosModulares(unittest.IsolatedAsyncioTestCase):
    """verifica el comportamiento asíncrono de CacheTTL e IdempotencyStore."""

    async def test_cache_ttl_hit_y_expiracion(self) -> None:
        cache = CacheTTL[str](ttl_segundos=0.15)
        self.assertIsNone(await cache.obtener("Bucaramanga"))

        await cache.guardar("Bucaramanga", "24.5 C")
        self.assertEqual(await cache.obtener("bucaramanga"), "24.5 C")

        await asyncio.sleep(0.20)
        self.assertIsNone(await cache.obtener("Bucaramanga"))

    async def test_idempotencia_creacion_y_replay(self) -> None:
        store = IdempotencyStore()
        solicitud = SolicitudCrearAlerta(
            sensor_id="S-001",
            severidad=SeveridadAlerta.ALTA,
            mensaje="Temperatura elevada en Laboratorio 1",
        )

        alerta_1, replay_1 = await store.registrar_o_recuperar_alerta(
            "clave-001", solicitud
        )
        alerta_2, replay_2 = await store.registrar_o_recuperar_alerta(
            "clave-001", solicitud
        )

        self.assertFalse(replay_1)
        self.assertTrue(replay_2)
        self.assertEqual(alerta_1.alerta_id, alerta_2.alerta_id)
        self.assertEqual(alerta_1.creada_en, alerta_2.creada_en)

    async def test_idempotencia_conflicto_payload_distinto(self) -> None:
        store = IdempotencyStore()
        solicitud_a = SolicitudCrearAlerta(
            sensor_id="S-001",
            severidad=SeveridadAlerta.ALTA,
            mensaje="Alerta original del sensor 1",
        )
        solicitud_b = SolicitudCrearAlerta(
            sensor_id="S-002",
            severidad=SeveridadAlerta.BAJA,
            mensaje="Alerta diferente con la misma clave",
        )

        await store.registrar_o_recuperar_alerta("clave-conflicto", solicitud_a)
        with self.assertRaises(ConflictoIdempotenciaError):
            await store.registrar_o_recuperar_alerta("clave-conflicto", solicitud_b)


if __name__ == "__main__":
    unittest.main()
