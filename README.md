### Agregador resiliente de APIs

servicio agregador desarrollado en **Python**, **FastAPI**, **Uvicorn**, **httpx** y **Pydantic v2** desarrollado para el curso de sistemas distribuidos.

el servicio consume de manera encadenada la API publica **Open-Meteo** aplicando caché en memoria con TTL, se integra con el servicio inestable de sensores tolerando fallos mediante timeouts explícitos, reintentos selectivos, *backoff* exponencial con *Full Jitter*, respeto de la cabecera `Retry-After` y recorrido completo de paginación por cursores, y garantiza idempotencia en operaciones de escritura mediante `Idempotency-Key`.

---

### integrantes y roles de trabajo

| integrante | rol en el equipo | modulos/responsabilidades |
| :--- | :--- | :--- |
| RICARDO ALFONSO CELIS SANDOVAL | rol 1: operacion del servicio inestable y evidencias | `servicio_inestable.py`, `evidencias_reintentos.log`, `pruebas_curl.sh`, `peticiones.http`: arranque y parametrización del servicio inestable con semilla reproducible (`--semilla 42`), captura de trazas de reintentos, esperas y respeto de `Retry-After` |
| VALENTINA TARAZONA CRUZ | rol 2: cliente de la API externa y caché con TTL | `app/services/open_meteo_client.py`, `app/services/cache.py`, `app/schemas/clima.py`, `app/api/v1/clima.py`: encadenamiento de llamadas a Open-Meteo (Geocodificación → Pronóstico), validación con Pydantic v2 y caché en memoria con TTL |
| ANDRES YESID CAICEDO RUEDA | rol 3: resiliencia y paginación del servicio inestable | `app/services/sensores_client.py`, `app/api/v1/sensores.py`, `app/core/config.py`: Lectura de `SERVICIO_INESTABLE_URL`, timeouts explícitos, reintentos selectivos (`503`, `429`, timeouts vs. `400`, `404`), *backoff* exponencial con *Full Jitter*, respeto de `Retry-After` y paginación completa por cursores |
| JHON SEBASTIAN ARCINIEGAS GONZALEZ | rol 4: API propia, idempotencia, desarrollo de modulo resiliencia, pruebas y análisis | `app/main.py`, `app/core/exceptions.py`, `app/services/idempotency.py`, `tests/test_unidades.py`, `pruebas.py`: Contrato OpenAPI (`/docs`), códigos de estado HTTP semánticos, control de idempotencia mediante `Idempotency-Key` en `POST /v1/alertas`, revisión y apoyo transversal en la lógica de resiliencia (`sensores_client.py`), suite de pruebas de integración y respuestas de análisis del proyecto |

---
### API externa elegida (`open-meteo.com`)

se seleccionó la API pública **Open-Meteo**, la cual no exige clave de autenticación y permite encadenar dos llamadas dentro de nuestro endpoint propio `GET /v1/ciudades/{nombre}/clima`

1. **llamada 1 geocodificación por nombre de ciudad**
   * endpoint: `GET https://geocoding-api.open-meteo.com/v1/search?name={nombre}&count=1&language=es&format=json`
   * proposito: resolver el nombre de la ciudad en coordenadas geográficas (`latitude`, `longitude`), país y región. Si la lista `results` está vacía, responde con `404 Not Found`
2. **llamada 2 (encadenada) pronóstico meteorológico por coordenadas**
   * endpoint: `GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=3`
   * proposito: Consultar el clima actual y el pronóstico de los próximos 3 días. Validado estrictamente mediante modelos Pydantic v2 (`RespuestaGeocodificacionExterna` y `RespuestaPronosticoExterno`)

---

### estructura del proyecto
elegimos desarrollar el proyecto basandonos en la arquitectura por Capas (Layered Architecture) combinada con una arquitectura modular, a continuación se detalla la estructura del mismo:

```text
taller_agregador_resiliente/
├── app/
│   ├── main.py                     # Application Factory y ciclo de vida (lifespan)
│   ├── core/                       # configuración (Settings), logging y manejo global de errores
│   ├── schemas/                    # modelos de validación estricta con Pydantic v2
│   ├── services/                   # lógica de negocio, CacheTTL, IdempotencyStore y clientes HTTP
│   └── api/                        # endpoints versionados v1 (clima, sensores, alertas, salud)
├── tests/
│   └── test_unidades.py            # pruebas unitarias asíncronas de servicios internos
├── main.py                         # punto de entrada raíz (compatible con uvicorn)
├── servicio_inestable.py           # servicio de sensores inestable (Anexo del taller)
├── requirements.txt                # dependencias del proyecto
├── pruebas.py                      # suite automatizada de pruebas de integración
├── peticiones.http                 # colección para REST Client (VS Code / JetBrains)
├── pruebas_curl.sh                 # script ejecutable de pruebas con cURL
├── evidencias_reintentos.log       # trazas de reintentos, esperas y respeto de Retry-After
└── README.md                       # dozcumentación técnica y análisis
```
### instalacion
**Linux/macOS**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
**Windows**
```bash
python -m venv venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
**nota:** cada servicio se debe ejecutar en una terminal por aparte

**servicio inestable**
```bash
python servicio_inestable.py --tasa-fallos 0.30 --tasa-429 0.10 --tasa-lentitud 0.20 --semilla 42
```

**servicio agregador**
```bash
# Linux/macOS
export SERVICIO_INESTABLE_URL="[http://127.0.0.1:9000](http://127.0.0.1:9000)"
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Windows(PowerShell)
$env:SERVICIO_INESTABLE_URL="[http://127.0.0.1:9000](http://127.0.0.1:9000)"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
**pruebas de integracion**
```bash
python pruebas.py
```
### medicion de latencia sin cache vs con cache
resultados sobre `GET /v1/ciudades/Bucaramanga/clima` con un TTL configurado en 60 segundos:

| peticion | estado de la cache | origen (`origen_datos`) | latencia interna (`latencia_ms`) | latencia total cliente HTTP | 0bservacion |
|---|---|---|---|---|---|
| 1 | **sin cache (miss)** | `api_externa` | `642.18 ms` | `648.90 ms` | ejecuta las dos llamadas encadenadas hacia Open-Meteo y almacena en cache |
| 2 | **con cache (hit)** | `cache` | `0.04 ms` | `2.15 ms` | lectura instantanea en memoria RAM protegida por `asyncio.Lock` (> 99.6% mas rápida) |
| 3 | **son cache (hit)** | `cache` | `0.03 ms` | `1.89 ms` | evita trafico innecesario a internet y protege el límite de peticiones de la IP |
| 4 (tras 61s) | **expirada (miss)** | `api_externa` | `619.45 ms` | `625.12 ms` | al vencer el TTL de 60 s, refresca el pronostico desde la fuente externa. |

### evidencias de reintentos y respeto de Retry-After
este es un extracto del archivo `evidencias_reintentos.log`:
```text
[16:42:10.128] [INFO] [agregador_resiliente] [Intento 1/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'bzo1'}
[16:42:10.132] [WARNING] [agregador_resiliente] [Intento 1] Recibido 429 Too Many Requests con cabecera Retry-After=2s. Respetando espera de 2.13s...
[16:42:12.261] [INFO] [agregador_resiliente] [Intento 2/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'bzo1'}
[16:42:12.265] [WARNING] [agregador_resiliente] [Intento 2] Recibido 503 Service Unavailable en /sensores. Backoff exponencial con jitter (techo=0.80s): esperando 0.42s...
[16:42:12.684] [INFO] [agregador_resiliente] [Intento 3/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'bzo1'}
[16:42:12.688] [INFO] [agregador_resiliente] [Intento 3/6] ÉXITO 200 en /sensores (params={'cursor': 'bzo1'})
```
demostracion de idempotencia
al enviar dos peticiones idénticas con la cabecera `Idempotency-Key: alerta-unica-lab1-2026`:

- **peticion 1** (`201 Created`, `X-Idempotent-Replay: false`): crea el recurso y retorna `ALT-7B4E91C2`.
- **peticion 2** (`201 Created`, `X-Idempotent-Replay: true`): retorna exactamente el mismo JSON con `ALT-7B4E91C2` sin duplicar efectos secundarios.

### respuestas a las preguntas de analisis
**a) ¿Por qué es peligroso reintentar un POST sin clave de idempotencia?**

porque si ocurre un timeout o perdida de red tras procesar el post en el servidor pero antes de que la respuesta llegue al cliente, el cliente no conoce el estado de la operacion. reintentar a ciegas un metodo no idempotente (`POST`) provoca la ejecucion repetida de la logica de negocio, generando efectos secundarios duplicados (multiples alertas, cobros dobles o registros repetidos).

**b) ¿Qué ocurriría si 50 clientes reintentaran al mismo tiempo sin jitter?**

ocurriria una estampida de reintentos (*thundering herd*). si 50 clientes sufren un fallo simultaneo y usan un backoff exponencial determinista sin aleatoriedad, se sincronizaran en fase y golpearan al servidor exactamente en los mismos instantes periodicos (1 s, 2 s, 4 s, ...), saturandolo de manera indefinida. el jitter desincroniza los reintentos distribuyendolos en el tiempo.

**c) ¿Qué tan desactualizados pueden estar los datos que entrega su caché, y cuándo sería inaceptable?**

estan desactualizados como maximo el tiempo del ttl configurado (60 segundos). es aceptable para pronosticos climaticos o catalogos, pero inaceptable en sistemas de tiempo real donde una lectura obsoleta implica riesgos fisicos o financieros (monitoreo de signos vitales, calderas industriales, saldos bancarios o trading de alta frecuencia).

**d) ¿Qué cambiaría en su diseño si el servicio corriera en varias réplicas detrás de un balanceador?**

las instancias en memoria local quedarian aisladas. requeririamos:

1. redis como almacen de idempotencia atomico (`SET key value NX EX ttl`).
2. redis como cache distribuida compartida para que un hit beneficie a todas las replicas.
3. compartir el estado de `Retry-After` en redis para pausar a todas las replicas bajo la misma ip de salida ante un castigo 429.



