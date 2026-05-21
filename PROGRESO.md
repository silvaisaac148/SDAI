# Progreso del Proyecto SDAI

> Sistema de Detección y Alertas de Intrusiones — PyMEs Estado Barinas
> Equipo: Isaac Silva · Carlos Herrera · Ángel Ramos

---

## Sprint 1-2 — COMPLETADO ✅
**Fecha:** 2026-05-04
**Objetivo:** Infraestructura técnica funcional (captura + API + DB)

### Entregables verificados

| Capa | Tecnología | Estado | Verificación |
|------|-----------|--------|-------------|
| 1. Captura | Scapy 2.6.1 + Npcap | ✅ | Sniff real Wi-Fi y ProtonVPN, decoder TCP/UDP/ICMP |
| 2. Análisis | (placeholder) | ⏳ Sprint 3-4 | — |
| 3. Persistencia | Supabase PostgreSQL | ✅ | 3 tablas + RLS policies + 4 configs seed + INSERT real |
| 4. Notificaciones | (placeholder) | ⏳ Sprint 5-6 | — |
| 5. Interfaz | FastAPI 0.115 + Uvicorn | ✅ | Endpoints `/`, `/health`, `/config` GET/POST + Swagger |

### Tests
- 8/8 pytest pass (`tests/test_sprint1.py`)
- Cubre: endpoints + decoder TCP/UDP/ICMP + caso no-IP

### Pipeline end-to-end probado
```
Red Wi-Fi → Scapy sniff → decoder.py → Supabase INSERT → SELECT verifica
```

### Stack instalado
- Python 3.12.10
- venv en `.venv/`
- 30+ paquetes (FastAPI, Scapy, Supabase, pytest, pydantic, uvicorn, etc.)

### Estructura final del proyecto
```
proyecto_franklin/
├── backend/app/
│   ├── main.py                  # FastAPI app
│   ├── config.py                # Settings (lee .env desde raíz)
│   ├── routers/
│   │   ├── health.py            # GET /health
│   │   └── config.py            # GET/POST /config (in-memory fallback + Supabase)
│   ├── models/schemas.py        # Pydantic
│   └── db/supabase_client.py    # Lazy singleton
├── capture/
│   ├── sniffer.py               # CLI: python -m capture.sniffer -i Wi-Fi -c 100
│   └── decoder.py               # Extrae IP/TCP/UDP/ICMP a dict
├── db/
│   └── schema.sql               # 3 tablas + RLS + seed
├── tests/
│   ├── conftest.py
│   └── test_sprint1.py
├── especificaciones del proyecto/  # Docs originales (PDF/DOCX)
├── imagenes de dudas/              # Screenshots de bloqueos
├── .env                            # Credenciales (gitignored)
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── PROGRESO.md                     # Este archivo
```

### Configuración Supabase aplicada
- Proyecto y URL en `.env` local (gitignored).
- Tablas: `events`, `alerts`, `configurations`
- RLS habilitado con policies anon (SELECT/INSERT/UPDATE) — modo dev
- Seed configs: port_scan_threshold, brute_force_threshold, dos_threshold, blacklist_ips

### Bloqueos resueltos durante Sprint 1-2
1. **Npcap requerido** Windows para Scapy → usuario instaló manual
2. **`.env` no encontrado desde `backend/`** → fix `Path(__file__).resolve().parents[2]` apunta raíz
3. **`utcnow()` deprecation warning** → cambiado a `datetime.now(timezone.utc)`
4. **RLS bloqueaba lectura anon Supabase** → añadidas policies SELECT/INSERT/UPDATE en schema

### Aprendizajes técnicos (sesión usuario)
- **TCP vs UDP:** TCP orientado conexión (handshake SYN/ACK), UDP sin estado
- **Tráfico real propio:** ProtonVPN encripta todo en WireGuard:51820 → IDS solo ve container UDP
- **Interfaz VPN (`ProtonVPN`):** muestra tráfico ya descifrado dentro túnel (HTTPS Google/Cloudflare)
- **IPs públicas:** rangos identifican proveedor (Google AS15169, Cloudflare AS13335)
- **Puertos efímeros:** clientes usan src_port aleatorio >49152, dst_port = servicio (443=HTTPS)
- **HTTPS sobre TCP y UDP:** UDP/443 = QUIC/HTTP3 (Google usa masivo)
- **DNS interno VPN:** 10.2.0.1 sirve resolución sin fuga al ISP

---

## Sprint 3-4 — COMPLETADO ✅
**Fecha:** 2026-05-21
**Objetivo:** Motor de detección de 4 amenazas + dashboard web

### Entregables verificados

| Componente | Estado | Detalle |
|------------|--------|---------|
| Detector `port_scan.py` | ✅ | N puertos distintos / 60s, severidad media/alta |
| Detector `brute_force.py` | ✅ | TCP SYN a puertos auth (22/21/23/3389) — fix falsos positivos UDP |
| Detector `dos.py` | ✅ | Packets/seg sliding window, severidad alta |
| Detector `malicious_ip.py` | ✅ | Match blacklist src/dst con dirección entrada/salida |
| `GeoIPResolver` | ✅ | MaxMind GeoLite2 local + mock fallback + private-IP detection |
| `DetectionStateManager` | ✅ | Orquesta detectores, cooldown 30s/IP+tipo, hot-config 10s |
| 6 routers API | ✅ | events, alerts, stats, config, health, live SSE |
| Stats nuevos | ✅ | `/stats/pps`, `/stats/uptime`, `/stats/trend` |
| Schema Supabase | ✅ | Columns GeoIP en `alerts` + verificador `scripts/verify_schema.py` |
| Dashboard conectado | ✅ | Reemplazos: mock → fetch real, rand() trend → `/stats/trend`, hack PPS → `/stats/pps` |
| SSE live stream | ✅ | `/live/stream` con event + alerts enriquecidos (src_ip, id, geoip) |
| Simulador ataques | ✅ | `scripts/simulate_attacks.py` sin Npcap |

### Tests
- 44/44 pytest pass (sprint1 + sprint3 + geoip + notifications)

### Pipeline end-to-end probado
```
sniffer → /events/ingest → DetectionStateManager → 4 detectores → Supabase
                                                 → notify_alert (Telegram/Email)
                                                 → broadcast_packet → SSE → Dashboard
```
Simulación: 667 paquetes → 11 alertas (real 76 acumuladas) → 4/4 tipos detectados.

### Endpoints expuestos
- `POST /events/ingest` — sniffer push (interno)
- `GET /events?limit=&offset=&protocol=&src_ip=&since=`
- `GET /alerts?severity=&resolved=&since=&limit=`
- `PATCH /alerts/{id}/resolve`
- `GET /config` / `GET /config/{key}` / `POST /config`
- `GET /stats/summary` — KPIs + threat distribution + top sources + uptime + current_pps
- `GET /stats/pps?history_buckets=&bucket_seconds=` — sparkline data
- `GET /stats/uptime`
- `GET /stats/trend?minutes=&buckets=` — stacked severity buckets
- `GET /live/stream` — SSE event+alerts
- `GET /dashboard` — sirve `SDAI/SDAI Dashboard.html`

---

## Sprint 5-6 — COMPLETADO ✅ (Notificaciones)
**Fecha:** 2026-05-21

### Entregables verificados

| Módulo | Estado | Notas |
|--------|--------|-------|
| `app/notifications/telegram.py` | ✅ | sendMessage HTTPS, Markdown |
| `app/notifications/email_smtp.py` | ✅ | SMTP TLS, multi-recipient |
| `app/notifications/dispatcher.py` | ✅ | Routing por severidad (alta=T+E, media=T, baja=∅), async daemon thread |
| Settings `.env` | ✅ | TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SMTP_* añadidos |
| Hook desde `state.py` | ✅ | `notify_alert(alert)` post-INSERT |
| Tests `test_notifications.py` | ✅ | 8/8 pass — routing, format, mocked send |

### Pendiente (post-MVP)
- Templates HTML para emails (actualmente texto plano)
- Gráficas Chart.js (la SVG actual del dashboard cubre KPIs/trend; añadir donuts/bar charts si se requiere)
- Rate-limit notifications (1 cada X min por src_ip+tipo, similar al cooldown ya implementado)

---

## Extras Sprint 3-4 — COMPLETADO ✅ (2026-05-21)
**Objetivo:** Botones dashboard funcionales + mapa global real

### Entregables verificados

| Componente | Estado | Detalle |
|------------|--------|---------|
| Búsqueda global (top bar) | ✅ | Overlay filtra packet table en vivo · Ctrl+F |
| Exportar reporte CSV | ✅ | `/alerts/export` + `/events/export` → blob download |
| Modal Ajustes | ✅ | Sliders refresh intervals + buffer size + reset sensor |
| Dropdown Perfil | ✅ | Info sensor (interfaz/Supabase/Telegram/Email) + Reiniciar |
| Modal Investigar IP | ✅ | `/events/investigate/{ip}` → eventos+alertas+geo+puertos+protocolos |
| Drawer: Seguir flujo + Copiar JSON + Hex dump + Capas | ✅ | Tabs JSON/Hex/Capas funcionales |
| Filter DNS (UDP/53) | ✅ | classifyProto helper |
| Sensor interface dinámica | ✅ | Reemplaza texto fijo "eth0" por settings.CAPTURE_INTERFACE |
| Mapa global Leaflet → Globe.gl 3D | ✅ | Globo Three.js estilo Kaspersky con arcos animados attacker→sensor, rings pulsantes, auto-rotate |
| Control sniffer remoto | ✅ | Botones Encender/Apagar + Pausa/Reanudar via `/capture/{start,stop,pause,resume,status}` con AsyncSniffer |

### Endpoints añadidos
- `GET /events/export` · `GET /events/investigate/{src_ip}`
- `GET /alerts/export`
- `GET /stats/sensor` · `POST /stats/reset`
- `POST /capture/start /stop /pause /resume` · `GET /capture/status`

### Tests
- 58/58 pytest pass (+14 nuevos: export, sensor, reset, investigate, capture controller)

---

## Pre-release — Docs para GitHub (2026-05-21)
- `README.md` reescrito con arquitectura, instalación, endpoints completos, demo simulator, notificaciones, estructura
- `ARCHITECTURE.md` nuevo: visión + componentes + flujo paquete + decisiones de diseño + gaps seguridad conocidos
- `CONTRIBUTING.md` nuevo: setup dev, conventional commits, áreas de contribución
- `LICENSE` MIT
- `.gitignore` actualizado: añadidos `*.mmdb`, `*.zip`, `*.jsonl`, `imagenes de dudas/`, `supabase/.temp/`
- Repo git inicializado localmente en `proyecto_franklin/.git/` (antes apuntaba accidentalmente a `C:\.git/`)
- IPs públicas reales en `simulate_attacks.py` para que GeoLite2 resuelva coords reales

### Sprint 7-8 — Optimización
- Pruebas carga 10k pkt/min
- Async/queue Scapy → DB (evita bloqueo)
- Batch INSERT (cada 100 eventos en lugar de 1 a 1)
- Logging estructurado
- Manejo errores robusto
- Refactor

### Sprint 9 — Documentación + entrega
- Manual instalación PyME (paso a paso, no técnico)
- Documentación arquitectura + APIs
- Video demo 5-7 min (simulación ataque + detección + alerta)
- Presentación académica
