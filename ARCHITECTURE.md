# SDAI · Arquitectura

Documento técnico de la arquitectura interna. Para visión de producto + instrucciones de instalación, ver [`README.md`](./README.md).

---

## Visión general

SDAI es un IDS (Intrusion Detection System) orientado a PyMEs sin equipo dedicado de ciberseguridad. Captura paquetes de red en vivo, analiza patrones de cuatro tipos de amenaza en sliding windows en memoria, persiste evidencia en Supabase, enriquece las alertas con geolocalización real y notifica por Telegram + Email. Todo se opera desde un dashboard estilo SOC en navegador.

El sistema se diseñó para correr en una laptop o Raspberry Pi conectada al switch principal de la PyME (modo "puerto espejo") y exponer un puerto HTTP local al administrador.

---

## Componentes

### 1. Captura — `capture/`

| Archivo | Responsabilidad |
|---------|-----------------|
| `sniffer.py` | CLI standalone basada en `scapy.sniff()`. Envía cada paquete decodificado por HTTP POST a `/events/ingest`. |
| `decoder.py` | Normaliza paquetes Scapy → dict (`src_ip`, `dst_ip`, `protocol`, `src_port`, `dst_port`, `flags`, `length`, `timestamp`). |
| `geoip_resolver.py` | Wrapper sobre `geoip2.database.Reader`. Resuelve IP → país/ciudad/lat/lon usando MaxMind GeoLite2. Detecta IPs privadas (RFC 1918) y reservadas. Tiene fallback determinista por hash MD5 cuando la DB no está disponible. |
| `state.py` | `DetectionStateManager`: orquestador en memoria. Mantiene sliding windows por src_ip para cada detector, cooldown anti-spam (30s por (ip, threat_type)), hot-reload de configs desde Supabase cada 10s, contador global de PPS, uptime. |
| `detectors/port_scan.py` | N puertos distintos en ventana → alerta. Severidad media (≥20) o alta (>30). |
| `detectors/brute_force.py` | N TCP SYN a puerto auth (22/21/23/3389) en ventana. **NO** cuenta UDP ni HTTP (descarta falsos positivos de DoS). |
| `detectors/malicious_ip.py` | Match contra `configurations.blacklist_ips`. Detecta dirección (entrada/salida). Severidad alta. |
| `detectors/dos.py` | Tasa global de paquetes por src_ip. Severidad alta. |

### 2. API + control plane — `backend/app/`

`FastAPI 0.115` con 7 routers:

| Router | Endpoints clave |
|--------|-----------------|
| `health` | `GET /health` |
| `config` | CRUD `/config` (umbrales runtime + blacklist) |
| `events` | `POST /ingest` (entrada del sniffer), `GET /events`, `GET /events/export` (CSV), `GET /events/investigate/{src_ip}` |
| `alerts` | `GET /alerts`, `GET /alerts/export`, `PATCH /{id}/resolve` |
| `stats` | `/summary`, `/pps`, `/uptime`, `/sensor`, `/trend`, `POST /reset` |
| `live` | `GET /live/stream` — Server-Sent Events |
| `capture` | `POST /start /stop /pause /resume`, `GET /status` (controla `AsyncSniffer`) |

Singletons compartidos en `app/services.py` (`state_manager`) y `app/capture_controller.py` (`controller`).

### 3. Persistencia — `db/`

`schema.sql` define 3 tablas en PostgreSQL (Supabase):

```sql
events           -- paquetes crudos (INET, JSONB raw_data)
  id, timestamp, src_ip, dst_ip, protocol, src_port, dst_port, flags, length, raw_data

alerts           -- amenazas detectadas
  id, event_id (FK), threat_type, severity, description, notified,
  created_at, country, city, latitude, longitude

configurations   -- umbrales + blacklist
  key (PK), value (JSONB), updated_at
```

RLS habilitado con policies `anon` permisivas para Sprint MVP (en producción cambiar a `service_role` y auth real). Índices en `(timestamp DESC)`, `src_ip`, `severity`, `country`, `created_at`.

### 4. Notificaciones — `backend/app/notifications/`

Routing por severidad en `dispatcher.py`:

```python
SEVERITY_CHANNELS = {
    "alta":  ("telegram", "email"),
    "media": ("telegram",),
    "baja":  (),
}
```

Disparo asíncrono (`threading.Thread` daemon) para no bloquear el path del paquete. Sin credenciales en `.env`, el canal es no-op silencioso. Templates separados para Telegram (Markdown) y Email (texto plano).

### 5. Dashboard — `SDAI/SDAI Dashboard.html`

Single-file HTML con:
- Tailwind CDN (utility CSS)
- Globe.gl 2.27 + Three.js 0.149 — globo 3D con texturas night + bump map relief, arcos animados attacker→sensor estilo Kaspersky Cybermap, rings pulsantes
- SSE EventSource consumiendo `/live/stream`
- Polling configurable: `/stats/summary` (3s), `/stats/pps` (1s), `/stats/trend` (15s), `/alerts` (30s), `/capture/status` (5s)
- Modales: investigar IP, ajustes, perfil, búsqueda overlay con Ctrl+F
- Fallback demo mode (mock data) cuando `/health` falla — útil para presentar sin servidor

Servido por FastAPI como `StaticFiles` mount + ruta `/dashboard`.

---

## Flujo de un paquete

```
1. Scapy AsyncSniffer captura paquete en NIC (Wi-Fi/Ethernet)
   │
   ▼
2. capture_controller._on_packet(pkt)
   │  - drop si paused
   ▼
3. capture/decoder.decode(pkt) → dict normalizado
   │
   ▼
4. POST http://localhost:8000/events/ingest (httpx sync, timeout 0.6s)
   │
   ▼
5. backend/app/routers/events.py :: ingest_event
   │  - INSERT en tabla events (Supabase), captura event_id
   │
   ▼
6. state_manager.process_packet(pkt, event_id)
   │  - refresh configs (cada 10s desde Supabase)
   │  - track timestamp global (PPS KPI)
   │  - corre los 4 detectores en secuencia
   │  - cooldown 30s por (src_ip, threat_type)
   │  - GeoIP enrichment via GeoLite2 mmdb
   │  - INSERT alerts (con country/city/lat/lon)
   │  - notify_alert(alert) → daemon thread → Telegram + Email
   │
   ▼
7. broadcast_packet(live_msg) → asyncio.Queue de cada listener SSE
   │
   ▼
8. EventSource del dashboard recibe JSON → render row + popup arc en globo
```

---

## Decisiones de diseño

### Por qué Scapy y no libpcap raw

Scapy abstrae cross-platform (Windows requiere Npcap, Linux usa AF_PACKET). El overhead es despreciable para los volúmenes esperados de una PyME (cientos de pps en pico). Para Sprint 7-8 evaluaremos batch INSERT + thread separado si el INSERT por paquete satura Supabase.

### Por qué Supabase y no Postgres directo

- Plan gratuito con RLS, dashboard, generación de API REST automática
- Permite que la PyME no administre infraestructura
- Backups y autenticación cubiertos
- Trade-off: latencia HTTP/2 → no es viable a >10k pps sin batching (Sprint 7-8)

### Por qué cooldown en memoria y no en DB

Cada query a Supabase por cada paquete sería prohibitivo. El cooldown vive en `DetectionStateManager.alert_cooldowns` (dict) — efímero, se pierde al reiniciar, lo cual es aceptable. La alerta sí queda persistida.

### Por qué notify_alert async daemon

`smtplib.SMTP.send_message` puede tardar 200ms-3s. Si bloqueamos en la ruta del paquete, los SSE listeners se atrasarían en cascada. Daemon thread per-alert es simple y aislado.

### Por qué Globe.gl en lugar de Leaflet

Globe.gl da 3D + arcos animados + texturas tipo "luz nocturna de la Tierra" gratis con muy poco código — réplica casi 1:1 del look de Kaspersky Cybermap. Leaflet 2D era más conservador pero menos vistoso para una demo académica/comercial.

### Por qué dashboard HTML single-file

Cero build step, cero npm, cero dependencias instaladas. La PyME ve un `.html` que se abre y funciona. El usuario administrador puede inspeccionarlo, modificar textos, hacer print → reporte. Ningún beneficio justificaría un toolchain Vite/Webpack en este sprint.

---

## Seguridad — gaps conocidos

Estos puntos están explícitamente fuera del MVP y deben atenderse antes de producción real:

| Gap | Mitigación pendiente |
|-----|---------------------|
| RLS anon write a alerts/events | Sprint hardening: service_role key + JWT |
| Sin auth en API | JWT con expiración + roles admin/viewer (slowapi + python-jose) |
| Sin rate-limit en endpoints públicos | `slowapi` por IP |
| Credenciales SMTP en `.env` plano | Vault / Doppler / Supabase Vault |
| Sin TLS local | `--ssl-keyfile --ssl-certfile` o reverse proxy nginx |
| Logs en stdout sin estructura | `structlog` o `loguru` JSON sink |

---

## Métricas internas para Sprint 7-8

- Tiempo medio detección → notificación: ~100ms (objetivo <500ms)
- INSERT events por segundo sostenible: ~150 pps (limit Supabase free tier)
- Cooldown collisions/min: medir antes de subir threshold
- False positive rate por detector: requiere baseline 7 días tráfico normal
