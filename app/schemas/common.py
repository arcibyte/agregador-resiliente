
from pydantic import BaseModel, ConfigDict, Field

class RespuestaSalud(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: str = Field(default="ok", examples=["ok"])
    servicio_inestable_url: str = Field(examples=["http://127.0.0.1:9000"])
    cache_ttl_segundos: float = Field(examples=[60.0])
    marca_tiempo: str = Field(examples=["2026-10-22T21:45:00+00:00"])


class ErrorRespuesta(BaseModel):
    detail: str = Field(..., description="descripcion legible de la causa del fallo")
    tipo_error: str = Field(
        default="ErrorDominio",
        description="clase de excepcion interna que origino la respuesta",
    )
    ruta: str = Field(default="/", description="Ruta HTTP invocada")
