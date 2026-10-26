
# endpoint idempotente para la creacion de alertas

from fastapi import APIRouter, Depends, Header, Response, status

from app.api.dependencies import obtener_idempotency_store
from app.schemas.alertas import RespuestaAlerta, SolicitudCrearAlerta
from app.schemas.common import ErrorRespuesta
from app.services.idempotency import IdempotencyStore

router = APIRouter(prefix="/v1/alertas", tags=["Alertas (Idempotencia)"])


@router.post(
    "",
    response_model=RespuestaAlerta,
    status_code=status.HTTP_201_CREATED,
    summary="crea una alerta de forma idempotente mediante la cabecera Idempotency-Key",
    responses={
        201: {
            "description": "alerta creada (o recuperada de forma idempotente sin efectos duplicados)"
        },
        409: {
            "model": ErrorRespuesta,
            "description": "la misma Idempotency-Key fue reutilizada con un cuerpo de peticion distinto",
        },
        422: {
            "description": "falta la cabecera Idempotency-Key o los datos del cuerpo son invalidos"
        },
    },
)
async def crear_alerta(
    solicitud: SolicitudCrearAlerta,
    response: Response,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=4,
        max_length=128,
        description="clave unica generada por el cliente para garantizar idempotencia en reintentos",
    ),
    store: IdempotencyStore = Depends(obtener_idempotency_store),
) -> RespuestaAlerta:
    alerta, es_replay = await store.registrar_o_recuperar_alerta(
        idempotency_key=idempotency_key,
        solicitud=solicitud,
    )
    response.headers["X-Idempotent-Replay"] = "true" if es_replay else "false"
    return alerta
