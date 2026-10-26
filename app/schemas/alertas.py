from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class SeveridadAlerta(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"

class SolicitudCrearAlerta(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sensor_id: str = Field(
        ...,
        min_length=2,
        max_length=32,
        examples=["S-001"],
        description="identificador del sensor asociado a la alerta",
    )
    severidad: SeveridadAlerta = Field(
        ...,
        examples=[SeveridadAlerta.ALTA],
        description="nivel de severidad: baja, media, alta o critica",
    )
    mensaje: str = Field(
        ...,
        min_length=5,
        max_length=300,
        examples=["temperatura superior al umbral permitido en Laboratorio 1"],
        description="descripción detallada del evento detectado",
    )

class RespuestaAlerta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alerta_id: str = Field(examples=["ALT-8F4A2C1D"])
    sensor_id: str = Field(examples=["S-001"])
    severidad: SeveridadAlerta
    mensaje: str
    creada_en: str = Field(examples=["2026-10-22T21:45:00+00:00"])
    idempotency_key: str = Field(examples=["alerta-unica-lab1-2026"])
