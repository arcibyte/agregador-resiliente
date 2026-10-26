from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.clima import RespuestaClimaCiudad

class SensorItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, examples=["S-001"])
    tipo: str = Field(min_length=1, examples=["temperatura"])
    ubicacion: str = Field(min_length=1, examples=["laboratorio 1"])

class PaginaSensoresExterna(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensores: List[SensorItem]
    siguiente: Optional[str] = None

class LecturaSensorExterna(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_id: str = Field(examples=["S-001"])
    tipo: str = Field(examples=["temperatura"])
    valor: float = Field(examples=[24.6])
    unidad: str = Field(examples=["°C"])
    marca_tiempo: str = Field(examples=["2026-10-22T21:45:00+00:00"])

class RespuestaListadoSensores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_sensores: int = Field(ge=0, examples=[23])
    paginas_recorridas: int = Field(ge=1, examples=[5])
    sensores: List[SensorItem]

class RespuestaReporteAmbientalCiudad(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clima_ciudad: RespuestaClimaCiudad
    resumen_sensores_locales: RespuestaListadoSensores
