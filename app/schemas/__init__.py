
#exportacion centralizada de modelos Pydantic v2

from app.schemas.alertas import RespuestaAlerta, SeveridadAlerta, SolicitudCrearAlerta
from app.schemas.clima import (
    ClimaActualExterno,
    CoordenadasGeo,
    OrigenDatosClima,
    PronosticoDiarioExterno,
    RespuestaClimaCiudad,
    RespuestaGeocodificacionExterna,
    RespuestaPronosticoExterno,
    ResultadoGeocodificacion,
    ResumenDiaClima,
)
from app.schemas.common import ErrorRespuesta, RespuestaSalud
from app.schemas.sensores import (
    LecturaSensorExterna,
    PaginaSensoresExterna,
    RespuestaListadoSensores,
    RespuestaReporteAmbientalCiudad,
    SensorItem,
)

__all__ = [
    "ClimaActualExterno",
    "CoordenadasGeo",
    "ErrorRespuesta",
    "LecturaSensorExterna",
    "OrigenDatosClima",
    "PaginaSensoresExterna",
    "PronosticoDiarioExterno",
    "RespuestaAlerta",
    "RespuestaClimaCiudad",
    "RespuestaGeocodificacionExterna",
    "RespuestaListadoSensores",
    "RespuestaPronosticoExterno",
    "RespuestaReporteAmbientalCiudad",
    "RespuestaSalud",
    "ResultadoGeocodificacion",
    "ResumenDiaClima",
    "SensorItem",
    "SeveridadAlerta",
    "SolicitudCrearAlerta",
]
