from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AgregadorBaseError(Exception):
    def __init__(self, detalle: str, codigo_http: int) -> None:
        super().__init__(detalle)
        self.detalle = detalle
        self.codigo_http = codigo_http


class PeticionExternaInvalidaError(AgregadorBaseError):
    """ error 400 originado por parámetros invalidos hacia la dependencia (ej; cursor corrupto)"""

    def __init__(self, detalle: str) -> None:
        super().__init__(detalle=detalle, codigo_http=status.HTTP_400_BAD_REQUEST)


class RecursoExternoNoEncontradoError(AgregadorBaseError):
    """wrror 404 cuando el recurso solicitado no existe en la API externa o servicio inestable"""

    def __init__(self, detalle: str) -> None:
        super().__init__(detalle=detalle, codigo_http=status.HTTP_404_NOT_FOUND)


class ConflictoIdempotenciaError(AgregadorBaseError):
    """error 409 cuando se reutiliza una misma Idempotency-Key con un payload diferente"""

    def __init__(self, detalle: str) -> None:
        super().__init__(detalle=detalle, codigo_http=status.HTTP_409_CONFLICT)


class DependenciaNoDisponibleError(AgregadorBaseError):
    """error 502 cuando la dependencia remota falla o devuelve respuestas malformadas"""

    def __init__(self, detalle: str) -> None:
        super().__init__(detalle=detalle, codigo_http=status.HTTP_502_BAD_GATEWAY)


class ContratoExternoInvalidoError(DependenciaNoDisponibleError):
    """error 502 específico cuando el JSON de la dependencia incumple el modelo Pydantic v2"""


class DependenciaTimeoutError(AgregadorBaseError):
    """error 504 cuando la dependencia remota excede el tiempo límite tras los reintentos"""

    def __init__(self, detalle: str) -> None:
        super().__init__(detalle=detalle, codigo_http=status.HTTP_504_GATEWAY_TIMEOUT)


def registrar_manejadores_excepciones(app: FastAPI) -> None:
    @app.exception_handler(AgregadorBaseError)
    async def manejar_error_dominio(
        request: Request, exc: AgregadorBaseError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.codigo_http,
            content={
                "detail": exc.detalle,
                "tipo_error": exc.__class__.__name__,
                "ruta": request.url.path,
            },
        )
