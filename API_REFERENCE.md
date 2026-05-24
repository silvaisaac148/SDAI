# SDAI — API Reference

> Referencia HTTP completa. Para arquitectura ver [`ARCHITECTURE.md`](./ARCHITECTURE.md). Para instalación ver [`MANUAL_INSTALACION.md`](./MANUAL_INSTALACION.md).

**Base URL local:** `http://localhost:8000`
**OpenAPI/Swagger UI:** `http://localhost:8000/docs`
**OpenAPI JSON schema:** `http://localhost:8000/openapi.json`

---

## Autenticación

Casi todos los endpoints requieren cookie de sesión válida (`sdai_session`). Excepciones públicas:

| Endpoint | Por qué público |
|----------|-----------------|
| `GET /health` | Healthcheck (LB / Docker) |
| `POST /auth/login` | Obvio |
| `POST /events/ingest` | Sniffer interno (rate-limited 300 req/min por IP) |
| `GET /live/stream` | SSE consumido por dashboard tras login |
| `GET /login` `GET /dashboard` `GET /` | HTML pages (redirect a login si no hay sesión) |

### Flujo de login

```
POST /auth/login   {username, password}    → Set-Cookie: sdai_session=<hmac-signed-token>
GET  /auth/me                              → {username}
POST /auth/logout                          → cookie eliminada
```

La cookie es HMAC-SHA256 firmada con `SESSION_SECRET_KEY` + timestamp Unix. Resistente a replay y forgery.

---

## Endpoints por router

### `auth` — Autenticación

| Método | Path | Descripción | Requiere |
|--------|------|-------------|----------|
| POST | `/auth/login` | Login con username + password. Rate-limit 5 intentos/min por IP. | público |
| POST | `/auth/logout` | Cierra sesión (elimina cookie). | sesión |
| GET | `/auth/session` | Verifica sesión actual. | público |
| GET | `/auth/me` | Devuelve `{username, role}` del usuario logueado. | sesión |
| GET | `/auth/users` | Lista todos los usuarios (sin password_hash). | admin |
| POST | `/auth/users` | Crea usuario. Body: `{username, password, role}`. | admin |
| PATCH | `/auth/users/{username}` | Update parcial: `{password?, role?, active?}`. | admin |
| DELETE | `/auth/users/{username}` | Eliminación definitiva. No self, no bootstrap admin. | admin |

**Login request:**
```json
POST /auth/login
Content-Type: application/json

{ "username": "admin", "password": "tu_password" }
```

**Login response:**
```
HTTP/1.1 200 OK
Set-Cookie: sdai_session=admin.1748120000.abcdef...; HttpOnly; SameSite=Lax
Content-Type: application/json

{ "username": "admin", "expires_in_seconds": 86400 }
```

**Credenciales:** primero busca en tabla `users` (bcrypt hash). Si no existe o DB offline → fallback a `.env` `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

---

### `health` — Healthcheck

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/health` | Liveness probe. Siempre 200 si proceso vivo. |

```json
GET /health
→ { "status": "ok" }
```

---

### `config` — Configuración runtime

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/config` | Lista todas las configs como dict. |
| GET | `/config/{key}` | Una config específica. |
| POST | `/config` | Crear o actualizar una config (upsert). |

**Keys soportadas:**

| Key | Tipo | Default | Descripción |
|-----|------|---------|-------------|
| `port_scan_threshold` | int | 20 | Puertos distintos por src_ip en ventana 60s |
| `brute_force_threshold` | int | 5 | TCP SYN a puerto auth en 60s |
| `dos_threshold` | int | 500 | Packets/seg disparador |
| `blacklist_ips` | list[str] | [] | IPs en lista negra |

**Update:**
```json
POST /config
Content-Type: application/json

{ "key": "port_scan_threshold", "value": 25 }
```

State manager refresca configs cada 10s → cambios live sin reiniciar.

---

### `events` — Paquetes capturados

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/events/ingest` | Recibe paquete del sniffer. Rate-limit 300/min por IP. Público. |
| GET | `/events` | Lista paquetes con paginación y filtros. |
| GET | `/events/export` | CSV de eventos. |
| GET | `/events/investigate/{src_ip}` | Resumen agregado por IP origen. |

**Ingest** (interno):
```json
POST /events/ingest
{
  "timestamp": "2026-05-24T14:32:18Z",
  "src_ip": "192.168.1.10",
  "dst_ip": "8.8.8.8",
  "protocol": "TCP",
  "src_port": 49152,
  "dst_port": 443,
  "flags": "S",
  "length": 64
}
→ { "status": "ok", "event_id": 12345, "alerts_triggered": 0 }
```

**Flow optimizado (Sprint 7-8):**
- Tráfico normal (99%) → encola en batch_writer (batch 100 INSERT)
- Amenaza detectada → INSERT inmediato para obtener `event_id`

**List con filtros:**
```
GET /events?limit=50&offset=0&protocol=TCP&src_ip=192.168.1.10&since=2026-05-24T00:00:00Z
```

| Query param | Tipo | Default | Notas |
|-------------|------|---------|-------|
| `limit` | int 1-500 | 50 | |
| `offset` | int ≥0 | 0 | |
| `protocol` | str | — | `TCP`, `UDP`, `ICMP` |
| `src_ip` | str | — | Filtro exacto |
| `since` | ISO datetime | — | Solo eventos posteriores |

**Investigate IP:**
```json
GET /events/investigate/192.168.1.10
{
  "src_ip": "192.168.1.10",
  "geo": { "country": "Venezuela", "city": "Barinas", "lat": ..., "lon": ... },
  "events": [...],
  "alerts": [...],
  "ports": { "443": 120, "80": 45, "22": 3 },
  "protocols": { "TCP": 150, "UDP": 18 },
  "summary": {
    "events_count": 168,
    "alerts_count": 2,
    "high_severity_count": 0,
    "is_blacklisted": false
  }
}
```

**Export CSV:**
```
GET /events/export?limit=10000&protocol=TCP&since=2026-05-01T00:00:00Z
→ Content-Type: text/csv
→ Content-Disposition: attachment; filename=sdai_events.csv
```

---

### `alerts` — Amenazas detectadas

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/alerts` | Lista alertas con filtros. |
| GET | `/alerts/export` | CSV ejecutivo. |
| PATCH | `/alerts/{id}/resolve` | Marca alerta como atendida. |

**List:**
```
GET /alerts?severity=alta&resolved=false&since=2026-05-24&limit=100
```

| Query param | Tipo | Notas |
|-------------|------|-------|
| `severity` | `baja`\|`media`\|`alta` | — |
| `resolved` | bool | Mapea a campo `notified` |
| `since` | ISO datetime | — |
| `limit` | int 1-100 | default 50 |

**Response:**
```json
[
  {
    "id": 88,
    "event_id": 12345,
    "threat_type": "port_scan",
    "severity": "alta",
    "description": "35 puertos distintos en 60s",
    "notified": false,
    "created_at": "2026-05-24T14:32:18Z",
    "country": "Germany",
    "city": "Brandenburg",
    "latitude": 52.4125,
    "longitude": 12.5316,
    "events": { "src_ip": "45.155.205.231", "dst_ip": "192.168.1.10", ... }
  },
  ...
]
```

**Resolve:**
```
PATCH /alerts/88/resolve
→ { "id": 88, "notified": true }
```

---

### `stats` — Métricas dashboard

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/stats/summary` | KPIs + threat distribution + top sources + PPS + uptime. |
| GET | `/stats/pps` | Packets-per-second con history sparkline. |
| GET | `/stats/uptime` | Segundos desde arranque del state manager. |
| GET | `/stats/sensor` | Metadata sensor + estado canales notificación. |
| GET | `/stats/trend` | Series temporales por severidad. |
| POST | `/stats/reset` | Limpia sliding windows + cooldowns en memoria. |

**Summary:**
```json
GET /stats/summary
{
  "total_events": 18450,
  "total_alerts": 76,
  "unresolved_alerts": 12,
  "alerts_by_severity": { "baja": 3, "media": 28, "alta": 45 },
  "threat_distribution": {
    "port_scan": 18, "brute_force": 12, "malicious_ip": 9, "dos": 37
  },
  "top_sources": [
    { "src_ip": "45.155.205.231", "count": 1240, "country": "DE" },
    ...
  ],
  "current_pps": 87.3,
  "uptime_seconds": 3672
}
```

**PPS history:**
```
GET /stats/pps?history_buckets=60&bucket_seconds=1
→ {
    "current_pps": 87.3,
    "history": [12, 15, 22, 18, ..., 87]   // 60 valores
  }
```

**Trend:**
```
GET /stats/trend?minutes=60&buckets=12
→ {
    "buckets": [
      { "ts": "2026-05-24T13:30Z", "baja": 0, "media": 2, "alta": 1 },
      { "ts": "2026-05-24T13:35Z", "baja": 1, "media": 4, "alta": 0 },
      ...
    ]
  }
```

**Sensor info:**
```json
GET /stats/sensor
{
  "interface": "eth0",
  "supabase_connected": true,
  "telegram_configured": true,
  "email_configured": true,
  "platform": "Linux-6.5.0-x86_64",
  "is_admin": true,
  "gemini_available": false
}
```

**Reset (admin):**
```
POST /stats/reset
→ { "status": "ok", "cleared": ["sliding_windows", "cooldowns"] }
```
Nota: no borra DB, solo memoria. Útil para empezar baseline limpio.

---

### `live` — Stream tiempo real

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/live/stream` | Server-Sent Events. Push de cada paquete + alertas. |

**Cliente JavaScript:**
```js
const es = new EventSource('/live/stream');
es.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  // msg = { event: {...packet}, alerts: [...] }
  console.log(msg);
};
```

**Heartbeat:** cada 15s para mantener conexión viva detrás de proxies.

---

### `capture` — Control sniffer remoto

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/capture/start` | Arranca AsyncSniffer en la NIC configurada. |
| POST | `/capture/stop` | Detiene completamente. |
| POST | `/capture/pause` | Pausa procesamiento (sniffer sigue corriendo). |
| POST | `/capture/resume` | Reanuda. |
| GET | `/capture/status` | `{ running, paused, interface, packets_seen }` |

**Status:**
```json
GET /capture/status
{
  "running": true,
  "paused": false,
  "interface": "eth0",
  "packets_seen": 18432
}
```

---

### `ai` — Tutor IA (opcional)

Disponible solo si `GEMINI_API_KEY` o `GROQ_API_KEY` están configurados.

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/ai/explain` | Explica una alerta en lenguaje simple para no-técnicos. |
| POST | `/ai/chat` | Conversación libre con el asistente. |

**Explain:**
```json
POST /ai/explain
{ "alert_id": 88 }
→ { "explanation": "Un atacante desde Brandenburg (Alemania) intentó tocar 35 puertos distintos en tu servidor 192.168.1.10. Esto se llama Port Scan y normalmente es el paso previo a un ataque más serio. Recomendación: bloquear esa IP en tu firewall y revisar si algún puerto vulnerable estaba expuesto." }
```

---

## Códigos HTTP

| Código | Significado |
|--------|-------------|
| 200 | OK |
| 201 | Created (ingest) |
| 204 | No content (logout) |
| 400 | Bad request (payload inválido) |
| 401 | Sin sesión o cookie inválida |
| 404 | Recurso no encontrado |
| 422 | Validation error (Pydantic) |
| 429 | Rate limit excedido |
| 500 | Error interno (revisar logs) |

---

## Headers especiales

| Header | Uso |
|--------|-----|
| `Cookie: sdai_session=...` | Autenticación |
| `X-Forwarded-For` | Rate-limiter respeta IP cliente detrás de proxy |
| `X-Real-IP` | Alternativa a X-Forwarded-For |

---

## Errores comunes y solución

| Error | Causa | Fix |
|-------|-------|-----|
| `401 {"detail":"Sesión inválida"}` | Cookie expirada o `SESSION_SECRET_KEY` cambió | Re-login |
| `429 Too Many Requests` | Rate-limit (300/min ingest, 5/min login) | Esperar 60s |
| `500 Error fetching events` | Supabase offline o key inválida | Verificar `.env` |
| `422 validation error` | Body no cumple schema Pydantic | Ver `/docs` para el contrato |

---

## Generar cliente desde OpenAPI

```bash
# Python
pip install openapi-python-client
openapi-python-client generate --url http://localhost:8000/openapi.json

# TypeScript
npx openapi-typescript http://localhost:8000/openapi.json -o sdai-types.ts
```

---

## Ejemplos cURL completos

```bash
# Login + guardar cookie
curl -c cookies.txt -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"tu_pass"}'

# Listar alertas con cookie
curl -b cookies.txt http://localhost:8000/alerts?severity=alta

# Ingest manual
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d '{"src_ip":"45.155.205.231","dst_ip":"192.168.1.10","protocol":"TCP","src_port":54321,"dst_port":22,"flags":"S","length":64,"timestamp":"2026-05-24T14:00:00Z"}'

# Stream SSE
curl -b cookies.txt http://localhost:8000/live/stream
```
