
# permite cambiar la URL del servicio inestable o los parametros de resiliencia sin modificar el codigo fuente

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_title: str = "agregador resiliente con open meteo"
    app_version: str = "2.0.0"
    app_description: str = (
    )

    open_meteo_geocoding_url: str = os.getenv(
        "OPEN_METEO_GEOCODING_URL",
        "https://geocoding-api.open-meteo.com/v1/search",
    )
    open_meteo_forecast_url: str = os.getenv(
        "OPEN_METEO_FORECAST_URL",
        "https://api.open-meteo.com/v1/forecast",
    )

    timeout_externo_read_s: float = float(os.getenv("TIMEOUT_EXTERNO_S", "5.0"))
    timeout_externo_connect_s: float = 3.0

    timeout_inestable_read_s: float = float(os.getenv("TIMEOUT_INESTABLE_S", "2.5"))
    timeout_inestable_connect_s: float = 2.0

    max_intentos: int = int(os.getenv("MAX_INTENTOS", "6"))
    base_backoff_s: float = float(os.getenv("BASE_BACKOFF_S", "0.4"))
    cache_ttl_segundos: float = float(os.getenv("CACHE_TTL_SEGUNDOS", "60.0"))
    log_file: str = os.getenv("AGREGADOR_LOG_FILE", "evidencias_reintentos.log")

    @property
    def servicio_inestable_url(self) -> str:
        return os.getenv("SERVICIO_INESTABLE_URL", "http://127.0.0.1:9000").rstrip("/")


def get_settings() -> Settings:
    return Settings()
