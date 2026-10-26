from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class OrigenDatosClima(str, Enum):
    CACHE = "cache"
    API_EXTERNA = "api_externa"


#codigo para los modelos de validación estricta hacia la API externa de Open-Meteo
class ResultadoGeocodificacion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str = Field(min_length=1)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    country: Optional[str] = "Desconocido"
    admin1: Optional[str] = None
    timezone: Optional[str] = "UTC"


class RespuestaGeocodificacionExterna(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: Optional[List[ResultadoGeocodificacion]] = None


class ClimaActualExterno(BaseModel):
    model_config = ConfigDict(extra="ignore")

    time: str
    temperature_2m: float
    relative_humidity_2m: int = Field(ge=0, le=100)
    wind_speed_10m: float = Field(ge=0.0)


class PronosticoDiarioExterno(BaseModel):
    model_config = ConfigDict(extra="ignore")

    time: List[str] = Field(min_length=1)
    temperature_2m_max: List[float] = Field(min_length=1)
    temperature_2m_min: List[float] = Field(min_length=1)


class RespuestaPronosticoExterno(BaseModel):
    model_config = ConfigDict(extra="ignore")

    latitude: float
    longitude: float
    timezone: str
    current: ClimaActualExterno
    daily: PronosticoDiarioExterno


# modelos del contrato propio expuesto al cliente
class CoordenadasGeo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitud: float
    longitud: float
class ResumenDiaClima(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: str
    temp_max_c: float
    temp_min_c: float

class RespuestaClimaCiudad(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ciudad: str
    pais: str
    region: Optional[str] = None
    coordenadas: CoordenadasGeo
    zona_horaria: str
    temperatura_actual_c: float
    humedad_relativa_pct: int
    velocidad_viento_kmh: float
    pronostico_proximos_dias: List[ResumenDiaClima]
    origen_datos: OrigenDatosClima = Field(
        description="dice si la respuesta provino de 'cache' o 'api_externa'"
    )
    latencia_ms: float = Field(
        ge=0.0, description="tiempo de procesamiento interno en milisegundos"
    )
