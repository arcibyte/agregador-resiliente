import asyncio
import time
from typing import Dict, Generic, Optional, Tuple, TypeVar

T = TypeVar("T")


class CacheTTL(Generic[T]):
    def __init__(self, ttl_segundos: float) -> None:
        if ttl_segundos <= 0:
            raise ValueError("el TTL debe ser mayor que cero segundos")
        self.ttl_segundos = ttl_segundos
        self._almacen: Dict[str, Tuple[float, T]] = {}
        self._lock = asyncio.Lock()

    async def obtener(self, clave: str) -> Optional[T]:
        clave_normalizada = clave.strip().lower()
        async with self._lock:
            entrada = self._almacen.get(clave_normalizada)
            if entrada is None:
                return None

            expira_en, valor = entrada
            if time.monotonic() > expira_en:
                del self._almacen[clave_normalizada]
                return None
            return valor

    async def guardar(self, clave: str, valor: T) -> None:
        clave_normalizada = clave.strip().lower()
        async with self._lock:
            self._almacen[clave_normalizada] = (
                time.monotonic() + self.ttl_segundos,
                valor,
            )

    async def limpiar(self) -> None:
        async with self._lock:
            self._almacen.clear()
