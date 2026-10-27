### Agregador resiliente de APIs

servicio agregador desarrollado en **Python**, **FastAPI**, **Uvicorn**, **httpx** y **Pydantic v2** desarrollado para el curso de sistemas distribuidos.

el servicio consume de manera encadenada la API publica **Open-Meteo** aplicando caché en memoria con TTL, se integra con el servicio inestable de sensores tolerando fallos mediante timeouts explícitos, reintentos selectivos, *backoff* exponencial con *Full Jitter*, respeto de la cabecera `Retry-After` y recorrido completo de paginación por cursores, y garantiza idempotencia en operaciones de escritura mediante `Idempotency-Key`.

---

### integrantes y roles de trabajo

| integrante | rol en el equipo | modulos/responsabilidades |
| :--- | :--- | :--- |
| RICARDO ALFONSO CELIS SANDOVAL | rol 1: operacion del servicio inestable y evidencias | `servicio_inestable.py`, `evidencias_reintentos.log`, `pruebas_curl.sh`, `peticiones.http`: arranque y parametrización del servicio inestable con semilla reproducible (`--semilla 42`), captura de trazas de reintentos, esperas y respeto de `Retry-After` |
| VALENTINA TARAZONA CRUZ | rol 2: cliente de la API externa y caché con TTL | `app/services/open_meteo_client.py`, `app/services/cache.py`, `app/schemas/clima.py`, `app/api/v1/clima.py`: encadenamiento de llamadas a Open-Meteo (Geocodificación → Pronóstico), validación con Pydantic v2 y caché en memoria con TTL |
| ANDRES YESID CAICEDO RUEDA | rol 3: resiliencia y paginación del servicio inestable | `app/services/sensores_client.py`, `app/api/v1/sensores.py`, `app/core/config.py`: lectura de `SERVICIO_INESTABLE_URL`, timeouts explícitos, reintentos selectivos (`503`, `429`, timeouts vs. `400`, `404`), *backoff* exponencial con *Full Jitter*, respeto de `Retry-After` y paginación completa por cursores |
| JHON SEBASTIAN ARCINIEGAS GONZALEZ | rol 4: API propia, idempotencia, desarrollo de modulo resiliencia, pruebas y análisis | `app/main.py`, `app/core/exceptions.py`, `app/services/idempotency.py`, `tests/test_unidades.py`, `pruebas.py`: contrato OpenAPI (`/docs`), códigos de estado HTTP semánticos, control de idempotencia mediante `Idempotency-Key` en `POST /v1/alertas`, revisión y apoyo transversal en la lógica de resiliencia (`sensores_client.py`), suite de pruebas de integración y respuestas de análisis del proyecto |

---

### API externa elegida (`open-meteo.com`)

se seleccionó la API pública **Open-Meteo**, la cual no exige clave de autenticación y permite encadenar dos llamadas dentro de nuestro endpoint propio `GET /v1/ciudades/{nombre}/clima`

1. **llamada 1: geocodificación por nombre de ciudad**
   * endpoint: `GET https://geocoding-api.open-meteo.com/v1/search?name={nombre}&count=1&language=es&format=json`
   * proposito: resolver el nombre de la ciudad en coordenadas geográficas (`latitude`, `longitude`), país y región. Si la lista `results` está vacía, responde con `404 Not Found`
2. **llamada 2 (encadenada): pronóstico meteorológico por coordenadas**
   * endpoint: `GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=3`
   * proposito: consultar el clima actual y el pronóstico de los próximos 3 días. Validado estrictamente mediante modelos Pydantic v2 (`RespuestaGeocodificacionExterna` y `RespuestaPronosticoExterno`)

---

### endpoints de la API propia

| metodo | ruta | descripcion | codigos de estado |
|---|---|---|---|
| `GET` | `/v1/ciudades/{nombre}/clima` | clima actual y pronóstico a 3 días (Open-Meteo encadenado, con caché TTL) | `200`, `404` (ciudad inexistente), `422` (parámetros inválidos), `502`/`504` (falla de la API externa) |
| `GET` | `/v1/sensores` | sensores del servicio inestable con paginación completa y reintentos | `200`, `502`/`504` (servicio inestable agotó los reintentos) |
| `POST` | `/v1/alertas` | crea una alerta; exige cabecera `Idempotency-Key` | `201`, `422` |
| `GET` | `/salud` | comprobación de vida del agregador | `200` |

el contrato completo está disponible en `http://127.0.0.1:8000/docs` (OpenAPI).

---

### estructura del proyecto

elegimos desarrollar el proyecto basándonos en la arquitectura por capas (Layered Architecture) combinada con una arquitectura modular, a continuación se detalla la estructura del mismo:

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
└── README.md                       # documentación técnica y análisis
```

---

### instalacion

**Linux/macOS**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
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

Linux/macOS:
```bash
export SERVICIO_INESTABLE_URL="http://127.0.0.1:9000"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Windows (PowerShell):
```powershell
$env:SERVICIO_INESTABLE_URL="http://127.0.0.1:9000"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

### pruebas

**pruebas de integracion** (requieren el servicio inestable y el agregador en ejecución):
```bash
python pruebas.py
```

**pruebas unitarias:**
```bash
python -m pytest tests/test_unidades.py
```

**coleccion de peticiones para el docente:**

- `peticiones.http`: abrir con la extensión REST Client (VS Code) o el cliente HTTP de JetBrains y ejecutar cada petición.
- `pruebas_curl.sh`: ejecutar con `bash pruebas_curl.sh` (por defecto apunta a `http://127.0.0.1:8000`).

---

### medicion de latencia sin cache vs con cache

resultados sobre `GET /v1/ciudades/Bucaramanga/clima` con un TTL configurado en 60 segundos:

| peticion | estado de la cache | origen (`origen_datos`) | latencia interna (`latencia_ms`) | latencia total cliente HTTP | observacion |
|---|---|---|---|---|---|
| 1 | **sin cache (miss)** | `api_externa` | `642.18 ms` | `648.90 ms` | ejecuta las dos llamadas encadenadas hacia Open-Meteo y almacena en cache |
| 2 | **con cache (hit)** | `cache` | `0.04 ms` | `2.15 ms` | lectura instantanea en memoria RAM protegida por `asyncio.Lock` (> 99.6% mas rápida) |
| 3 | **con cache (hit)** | `cache` | `0.03 ms` | `1.89 ms` | evita trafico innecesario a internet y protege el límite de peticiones de la IP |
| 4 (tras 61s) | **expirada (miss)** | `api_externa` | `619.45 ms` | `625.12 ms` | al vencer el TTL de 60 s, refresca el pronostico desde la fuente externa |

registro del agregador que confirma el comportamiento de la caché:

```text
[00:02:12.189] [INFO] [agregador_resiliente] [CACHE MISS] Consultando Open-Meteo (2 llamadas encadenadas) para 'Bucaramanga'...
[00:02:14.066] [INFO] [agregador_resiliente] [CACHE HIT] Clima para 'Bucaramanga' servido desde caché en memoria.
```

---

### evidencias de reintentos y respeto de Retry-After

estos son extractos del archivo `evidencias_reintentos.log` (el archivo completo se entrega junto al código). la configuración usada fue `--tasa-fallos 0.30 --tasa-429 0.10 --tasa-lentitud 0.20 --latencia 4.0 --semilla 42`.

**1. timeouts (> 2.5 s) y 503 con backoff exponencial y jitter**

el techo del backoff se duplica en cada intento (0.40 s, 0.80 s, 1.60 s, 3.20 s, 6.40 s) y la espera real es un valor aleatorio dentro de ese techo (*Full Jitter*):

```text
[16:42:14.462] [INFO] [agregador_resiliente] [Intento 1/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'bzo1'}
[16:42:16.966] [WARNING] [agregador_resiliente] [Intento 1/6] Timeout detectado (> 2.5s) en /sensores. Backoff exponencial con jitter (techo=0.40s): esperando 0.31s...
[16:42:17.278] [INFO] [agregador_resiliente] [Intento 2/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'bzo1'}
[16:42:19.782] [WARNING] [agregador_resiliente] [Intento 2/6] Timeout detectado (> 2.5s) en /sensores. Backoff exponencial con jitter (techo=0.80s): esperando 0.61s...
[16:42:20.394] [INFO] [agregador_resiliente] [Intento 3/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'bzo1'}
[16:42:20.398] [WARNING] [agregador_resiliente] [Intento 3/6] Recibido 503 Service Unavailable en /sensores. Backoff exponencial con jitter (techo=1.60s): esperando 0.75s...
[16:42:21.149] [INFO] [agregador_resiliente] [Intento 4/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'bzo1'}
[16:42:23.653] [WARNING] [agregador_resiliente] [Intento 4/6] Timeout detectado (> 2.5s) en /sensores. Backoff exponencial con jitter (techo=3.20s): esperando 2.58s...
[16:42:26.233] [INFO] [agregador_resiliente] [Intento 5/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'bzo1'}
[16:42:26.237] [WARNING] [agregador_resiliente] [Intento 5/6] Recibido 503 Service Unavailable en /sensores. Backoff exponencial con jitter (techo=6.40s): esperando 3.46s...
[16:42:29.694] [INFO] [agregador_resiliente] [Intento 6/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'bzo1'}
[16:42:29.698] [INFO] [agregador_resiliente] [Intento 6/6] ÉXITO 200 en /sensores (params={'cursor': 'bzo1'})
```

**2. respeto de `Retry-After` ante un 429**

el servicio inestable indica `Retry-After: 2` y el cliente espera 2.19 s antes de reintentar, por lo que no recibe un segundo 429:

```text
[16:42:29.846] [INFO] [agregador_resiliente] [Intento 1/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'bzoxNQ=='}
[16:42:29.850] [WARNING] [agregador_resiliente] [Intento 1] Recibido 429 Too Many Requests con cabecera Retry-After=2s. Respetando espera de 2.19s...
[16:42:32.041] [INFO] [agregador_resiliente] [Intento 2/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'bzoxNQ=='}
[16:42:32.045] [INFO] [agregador_resiliente] [Intento 2/6] ÉXITO 200 en /sensores (params={'cursor': 'bzoxNQ=='})
```

lo mismo visto desde la terminal del servicio inestable:

```text
[16:42:29.850]       127.0.0.1 GET /sensores -> 429 (Retry-After: 2)
[16:42:32.045]       127.0.0.1 GET /sensores -> 200
```

**3. paginacion completa**

el cliente sigue el campo `siguiente` de cada respuesta hasta que llega `null`, acumulando los sensores de todas las páginas. con 23 sensores y 5 por página son 5 páginas (cursores sin parámetro, `bzo1`, `bzoxMA==`, `bzoxNQ==` y `bzoyMA==`, equivalentes a los desplazamientos 0, 5, 10, 15 y 20):

```text
[16:42:14.454] [INFO] [agregador_resiliente] [Intento 4/6] ÉXITO 200 en /sensores (params=None)
[16:42:29.698] [INFO] [agregador_resiliente] [Intento 6/6] ÉXITO 200 en /sensores (params={'cursor': 'bzo1'})
[16:42:29.838] [INFO] [agregador_resiliente] [Intento 2/6] ÉXITO 200 en /sensores (params={'cursor': 'bzoxMA=='})
[16:42:32.045] [INFO] [agregador_resiliente] [Intento 2/6] ÉXITO 200 en /sensores (params={'cursor': 'bzoxNQ=='})
[16:42:32.933] [INFO] [agregador_resiliente] [Intento 3/6] ÉXITO 200 en /sensores (params={'cursor': 'bzoyMA=='})
```

**4. errores no reintentables (404 y 400)**

los errores legítimos abortan de inmediato, sin reintentos:

```text
[16:42:33.441] [INFO] [agregador_resiliente] [Intento 1/6] GET http://127.0.0.1:9000/sensores/S-999/lectura params=None
[16:42:33.446] [WARNING] [agregador_resiliente] [Intento 1/6] Error 404 legítimo en /sensores/S-999/lectura. No es reintentable; abortando reintentos inmediatamente.
[16:42:33.846] [INFO] [agregador_resiliente] [Intento 1/6] GET http://127.0.0.1:9000/sensores params={'cursor': 'cursor_invalido_xyz'}
[16:42:33.851] [WARNING] [agregador_resiliente] [Intento 1/6] Error 400 legítimo en /sensores. No es reintentable; abortando reintentos inmediatamente.
```

---

### demostracion de idempotencia

al enviar dos peticiones idénticas con la cabecera `Idempotency-Key: alerta-unica-lab1-2026`:

```bash
curl -i -X POST http://127.0.0.1:8000/v1/alertas \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: alerta-unica-lab1-2026" \
  -d '{"sensor_id": "S-001", "severidad": "alta", "mensaje": "temperatura superior al umbral permitido en Laboratorio 1"}'
```

- **peticion 1** (`201 Created`, `X-Idempotent-Replay: false`): crea el recurso y retorna `ALT-1D1ED1C9`.
- **peticion 2** (`201 Created`, `X-Idempotent-Replay: true`): retorna exactamente el mismo JSON con `ALT-1D1ED1C9` sin duplicar efectos secundarios.

**peticion 1:**

```http
HTTP/1.1 201 Created
date: Tue, 27 Oct 2026 00:56:01 GMT
server: uvicorn
content-length: 220
content-type: application/json
x-idempotent-replay: false
```

```json
{"alerta_id":"ALT-1D1ED1C9","sensor_id":"S-001","severidad":"alta","mensaje":"temperatura superior al umbral permitido en Laboratorio 1","creada_en":"2026-10-27T00:56:02+00:00","idempotency_key":"alerta-unica-lab1-2026"}
```

**peticion 2 (misma clave y mismo cuerpo):**

```http
HTTP/1.1 201 Created
date: Tue, 27 Oct 2026 00:56:06 GMT
server: uvicorn
content-length: 220
content-type: application/json
x-idempotent-replay: true
```

```json
{"alerta_id":"ALT-1D1ED1C9","sensor_id":"S-001","severidad":"alta","mensaje":"temperatura superior al umbral permitido en Laboratorio 1","creada_en":"2026-10-27T00:56:02+00:00","idempotency_key":"alerta-unica-lab1-2026"}
```

el `alerta_id` y `creada_en` son idénticos en ambas respuestas: la segunda no creó una alerta nueva.

registro del agregador para una clave repetida y para una clave reutilizada con un cuerpo distinto (`409 Conflict`):

```text
[23:39:20.080] [INFO] [agregador_resiliente] [IDEMPOTENCIA] Nueva alerta creada: ALT-E393BD9C (clave='clave-001').
[23:39:20.080] [INFO] [agregador_resiliente] [IDEMPOTENCIA] Petición repetida detectada para clave 'clave-001'. Devolviendo alerta existente ALT-E393BD9C sin duplicar efectos.
[23:39:20.076] [INFO] [agregador_resiliente] [IDEMPOTENCIA] Nueva alerta creada: ALT-7E30553C (clave='clave-conflicto').
[23:39:20.078] [WARNING] [agregador_resiliente] [IDEMPOTENCIA] Conflicto 409: la clave 'clave-conflicto' se reutilizó con un cuerpo de peticion diferente
```

---

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
