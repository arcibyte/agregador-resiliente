### Agregador resiliente de APIs

servicio agregador desarrollado en **Python**, **FastAPI**, **Uvicorn**, **httpx** y **Pydantic v2** desarrollado para el curso de sistemas distribuidos.

el servicio consume de manera encadenada la API publica **Open-Meteo** aplicando caché en memoria con TTL, se integra con el servicio inestable de sensores tolerando fallos mediante timeouts explícitos, reintentos selectivos, *backoff* exponencial con *Full Jitter*, respeto de la cabecera `Retry-After` y recorrido completo de paginación por cursores, y garantiza idempotencia en operaciones de escritura mediante `Idempotency-Key`.

---

#### integrantes y roles de trabajo

| integrante | rol en el equipo | modulos/responsabilidades |
| :--- | :--- | :--- |
| RICARDO ALFONSO CELIS SANDOVAL | rol 1: operacion del servicio inestable y evidencias | `servicio_inestable.py`, `evidencias_reintentos.log`, `pruebas_curl.sh`, `peticiones.http`: arranque y parametrización del servicio inestable con semilla reproducible (`--semilla 42`), captura de trazas de reintentos, esperas y respeto de `Retry-After` |
| VALENTINA TARAZONA CRUZ | rol 2: cliente de la API externa y caché con TTL | `app/services/open_meteo_client.py`, `app/services/cache.py`, `app/schemas/clima.py`, `app/api/v1/clima.py`: encadenamiento de llamadas a Open-Meteo (Geocodificación → Pronóstico), validación con Pydantic v2 y caché en memoria con TTL |
| ANDRES YESID CAICEDO RUEDA | rol 3: resiliencia y paginación del servicio inestable | `app/services/sensores_client.py`, `app/api/v1/sensores.py`, `app/core/config.py`: Lectura de `SERVICIO_INESTABLE_URL`, timeouts explícitos, reintentos selectivos (`503`, `429`, timeouts vs. `400`, `404`), *backoff* exponencial con *Full Jitter*, respeto de `Retry-After` y paginación completa por cursores |
| JHON SEBASTIAN ARCINIEGAS GONZALEZ | rol 4: API propia, idempotencia, desarrollo de modulo resiliencia, pruebas y análisis | `app/main.py`, `app/core/exceptions.py`, `app/services/idempotency.py`, `tests/test_unidades.py`, `pruebas.py`: Contrato OpenAPI (`/docs`), códigos de estado HTTP semánticos, control de idempotencia mediante `Idempotency-Key` en `POST /v1/alertas`, revisión y apoyo transversal en la lógica de resiliencia (`sensores_client.py`), suite de pruebas de integración y respuestas de análisis del proyecto |

---
#### API externa elegida (`open-meteo.com`)

se seleccionó la API pública **Open-Meteo**, la cual no exige clave de autenticación y permite encadenar dos llamadas dentro de nuestro endpoint propio `GET /v1/ciudades/{nombre}/clima`

1. **llamada 1 geocodificación por nombre de ciudad**
   * endpoint: `GET https://geocoding-api.open-meteo.com/v1/search?name={nombre}&count=1&language=es&format=json`
   * proposito: resolver el nombre de la ciudad en coordenadas geográficas (`latitude`, `longitude`), país y región. Si la lista `results` está vacía, responde con `404 Not Found`
2. **llamada 2 (Encadenada) — Pronóstico meteorológico por coordenadas**
   * endpoint: `GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=3`
   * proposito: Consultar el clima actual y el pronóstico de los próximos 3 días. Validado estrictamente mediante modelos Pydantic v2 (`RespuestaGeocodificacionExterna` y `RespuestaPronosticoExterno`)

---

#### estructura del proyecto
elegimos desarrollar el proyecto basandonos en la arquitectura por Capas (Layered Architecture) combinada con una arquitectura modular, a continuación se detalla la estructura del mismo:

```text
taller_agregador_resiliente/
├── app/
│   ├── main.py                       # Application Factory y ciclo de vida (lifespan)
│   ├── core/                         # configuración (Settings), logging y manejo global de errores
│   ├── schemas/                      # modelos de validación estricta con Pydantic v2
│   ├── services/                     # lógica de negocio, CacheTTL, IdempotencyStore y clientes HTTP
│   └── api/                          # endpoints versionados v1 (clima, sensores, alertas, salud)
├── tests/
│   └── test_unidades.py              # pruebas unitarias asíncronas de servicios internos
├── main.py                           # punto de entrada raíz (compatible con uvicorn)
├── servicio_inestable.py             # servicio de sensores inestable (Anexo del taller)
├── requirements.txt                  # dependencias del proyecto
├── pruebas.py                        # suite automatizada de pruebas de integración
├── peticiones.http                   # colección para REST Client (VS Code / JetBrains)
├── pruebas_curl.sh                   # script ejecutable de pruebas con cURL
├── evidencias_reintentos.log         # trazas de reintentos, esperas y respeto de Retry-After
└── README.md                         # dozcumentación técnica y análisis
