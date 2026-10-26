#!/usr/bin/env bash
# script de pruebas con cURL
set -e
BASE_URL="${AGREGADOR_URL:-http://127.0.0.1:8000}"

echo "=== 1. GET /salud ==="
curl -s -i "$BASE_URL/salud"
echo -e "\n"

echo "=== 2. GET /v1/ciudades/Bucaramanga/clima (Llamada 1 - Sin Caché) ==="
curl -s "$BASE_URL/v1/ciudades/Bucaramanga/clima"
echo -e "\n"

echo "=== 3. GET /v1/ciudades/Bucaramanga/clima (Llamada 2 - Con Caché) ==="
curl -s "$BASE_URL/v1/ciudades/Bucaramanga/clima"
echo -e "\n"

echo "=== 4. GET /v1/ciudades/CiudadInexistenteXYZ999/clima (404 esperado) ==="
curl -s -i "$BASE_URL/v1/ciudades/CiudadInexistenteXYZ999/clima"
echo -e "\n"

echo "=== 5. GET /v1/sensores (Paginación completa resiliente) ==="
curl -s "$BASE_URL/v1/sensores"
echo -e "\n"

echo "=== 6. GET /v1/sensores/S-001/lectura (200 esperado) ==="
curl -s "$BASE_URL/v1/sensores/S-001/lectura"
echo -e "\n"

echo "=== 7. GET /v1/sensores/S-999/lectura (404 sin reintento) ==="
curl -s -i "$BASE_URL/v1/sensores/S-999/lectura"
echo -e "\n"

echo "=== 8. GET /v1/sensores?cursor_inicial=invalido (400 sin reintento) ==="
curl -s -i "$BASE_URL/v1/sensores?cursor_inicial=invalido"
echo -e "\n"

echo "=== 9. POST /v1/alertas (Petición 1 con Idempotency-Key) ==="
curl -s -i -X POST "$BASE_URL/v1/alertas" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-key-001" \
  -d '{"sensor_id": "S-001", "severidad": "alta", "mensaje": "Temperatura fuera de rango en Laboratorio 1"}'
echo -e "\n"

echo "=== 10. POST /v1/alertas (Petición 2 repetida con la misma Idempotency-Key) ==="
curl -s -i -X POST "$BASE_URL/v1/alertas" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-key-001" \
  -d '{"sensor_id": "S-001", "severidad": "alta", "mensaje": "Temperatura fuera de rango en Laboratorio 1"}'
echo -e "\n"
