
# coleccion ejecutable de peticiones de integracion para revisar todos los endpoints

""" ejecucion;
    python pruebas.py
"""

import os
import time
import uuid
import httpx

BASE_URL = os.getenv("AGREGADOR_URL", "http://127.0.0.1:8000").rstrip("/")


def separador(titulo: str) -> None:
    print("\n" + "=" * 78)
    print(f" PRUEBA: {titulo}")
    print("=" * 78)


def ejecutar_suite() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        separador("1 comprobacion de vida del agregador (GET /salud)")
        r_salud = client.get("/salud")
        print(f"estado HTTP: {r_salud.status_code}")
        print(f"respuesta  : {r_salud.json()}")
        assert r_salud.status_code == 200

        separador("2 API externa encadenada y latencia sin cache vs con cache (GET /v1/ciudades/{nombre}/clima)")
        ciudad = "Bucaramanga"

        t0 = time.perf_counter()
        r_clima_1 = client.get(f"/v1/ciudades/{ciudad}/clima")
        lat_cliente_1 = (time.perf_counter() - t0) * 1000.0
        datos_1 = r_clima_1.json()
        print(
            f"[Llamada 1 SIN CACHÉ] HTTP {r_clima_1.status_code} | "
            f"origen: {datos_1.get('origen_datos')} | "
            f"latencia interna: {datos_1.get('latencia_ms')} ms | "
            f"latencia cliente: {lat_cliente_1:.2f} ms"
        )
        assert r_clima_1.status_code == 200
        assert datos_1["origen_datos"] == "api_externa"

        t1 = time.perf_counter()
        r_clima_2 = client.get(f"/v1/ciudades/{ciudad}/clima")
        lat_cliente_2 = (time.perf_counter() - t1) * 1000.0
        datos_2 = r_clima_2.json()
        print(
            f"[Llamada 2 CON CACHÉ] HTTP {r_clima_2.status_code} | "
            f"origen: {datos_2.get('origen_datos')} | "
            f"latencia interna: {datos_2.get('latencia_ms')} ms | "
            f"latencia cliente: {lat_cliente_2:.2f} ms"
        )
        assert r_clima_2.status_code == 200
        assert datos_2["origen_datos"] == "cache"

        separador("3 codigos de estado en API externa: 404 (ciudad inexistente) y 422 (parmetro invalido)")
        r_404_ciudad = client.get("/v1/ciudades/CiudadInexistenteXYZ98765/clima")
        print(f"[ciudad inexistente] HTTP {r_404_ciudad.status_code} -> {r_404_ciudad.json()}")
        assert r_404_ciudad.status_code == 404

        r_422_ciudad = client.get("/v1/ciudades/A/clima")
        print(f"[nombre demasiado corto (<2 chars)] HTTP {r_422_ciudad.status_code}")
        assert r_422_ciudad.status_code == 422

        #recorrido completo de paginacion del servicio inestable con resiliencia
        separador("4 paginacion completa del servicio inestable (GET /v1/sensores)")
        r_sensores = client.get("/v1/sensores")
        datos_sensores = r_sensores.json()
        print(
            f"HTTP {r_sensores.status_code} | "
            f"total sensores: {datos_sensores['total_sensores']} | "
            f"paginas recorridas: {datos_sensores['paginas_recorridas']}"
        )
        print(f"primeros 3 sensores: {datos_sensores['sensores'][:3]}")
        assert r_sensores.status_code == 200
        assert datos_sensores["total_sensores"] == 23
        assert datos_sensores["paginas_recorridas"] == 5

        separador("5. lectura de sensor valido (S-001 -> 200) e Inexistente (S-999 -> 404 sin reintentos)")
        r_lec_ok = client.get("/v1/sensores/S-001/lectura")
        print(f"[Sensor S-001] HTTP {r_lec_ok.status_code} -> {r_lec_ok.json()}")
        assert r_lec_ok.status_code == 200

        t_404_ini = time.perf_counter()
        r_lec_404 = client.get("/v1/sensores/S-999/lectura")
        t_404_ms = (time.perf_counter() - t_404_ini) * 1000.0
        print(
            f"[Sensor S-999] HTTP {r_lec_404.status_code} ({t_404_ms:.2f} ms) -> {r_lec_404.json()}"
        )
        assert r_lec_404.status_code == 404

        separador("error 400 legitimo por cursor invalido (sin reintentos)")
        r_400 = client.get("/v1/sensores", params={"cursor_inicial": "cursor_invalido_xyz"})
        print(f"[cursor invalido] HTTP {r_400.status_code} -> {r_400.json()}")
        assert r_400.status_code == 400

        separador("7 demostracion de idempotencia (POST /v1/alertas con Idempotency-Key)")
        clave_idem = f"idem-key-{uuid.uuid4().hex[:10]}"
        cuerpo_alerta = {
            "sensor_id": "S-001",
            "severidad": "alta",
            "mensaje": "temperatura critica detectada en laboratorio 1",
        }

        r_post_1 = client.post(
            "/v1/alertas",
            json=cuerpo_alerta,
            headers={"Idempotency-Key": clave_idem},
        )
        r_post_2 = client.post(
            "/v1/alertas",
            json=cuerpo_alerta,
            headers={"Idempotency-Key": clave_idem},
        )

        print(
            f"[Intento 1] HTTP {r_post_1.status_code} | "
            f"X-Idempotent-Replay={r_post_1.headers.get('X-Idempotent-Replay')} | "
            f"Body={r_post_1.json()}"
        )
        print(
            f"[Intento 2] HTTP {r_post_2.status_code} | "
            f"X-Idempotent-Replay={r_post_2.headers.get('X-Idempotent-Replay')} | "
            f"Body={r_post_2.json()}"
        )
        assert r_post_1.status_code == 201
        assert r_post_2.status_code == 201
        assert r_post_1.json() == r_post_2.json()
        assert r_post_1.headers.get("X-Idempotent-Replay") == "false"
        assert r_post_2.headers.get("X-Idempotent-Replay") == "true"

        r_post_409 = client.post(
            "/v1/alertas",
            json={
                "sensor_id": "S-002",
                "severidad": "baja",
                "mensaje": "Payload distinto con la misma clave de idempotencia",
            },
            headers={"Idempotency-Key": clave_idem},
        )
        print(f"[misma clave con distinto payload] HTTP {r_post_409.status_code} -> {r_post_409.json()}")
        assert r_post_409.status_code == 409

        print("\ntodos los criterios de evaluación fueron verificados correctamente")


if __name__ == "__main__":
    ejecutar_suite()
