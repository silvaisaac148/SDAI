# SDAI — Sistema de Detección y Alertas de Intrusiones

MVP académico para PyMEs del Estado Barinas, Venezuela. Captura tráfico de red en vivo, detecta cuatro tipos de amenazas (port scan, brute force, IPs maliciosas, DoS), enriquece cada alerta con geolocalización real (GeoLite2) y la envía por Telegram + Email. Expone API REST y un dashboard estilo SOC con globo 3D estilo Kaspersky Cybermap.

**Equipo:** Isaac Silva · Carlos Herrera · Ángel Ramos
**Stack:** Python 3.12 · Scapy 2.6 · FastAPI 0.115 · Supabase (PostgreSQL) · Tailwind + Globe.gl (Three.js)

---

## Estado del proyecto

| Sprint | Alcance | Estado |
|--------|---------|--------|
| 1-2 | Setup Scapy + FastAPI + Supabase schema + decoder TCP/UDP/ICMP | ✅ |
| 3-4 | Motor detección 4 amenazas + GeoIP + dashboard live + SSE | ✅ |
| 5-6 | Notificaciones Telegram + Email + routing por severidad | ✅ |
| Extras | Botones dashboard funcionales · globo 3D · control sniffer remoto | ✅ |
| 7-8 | Carga 10k pkt/min · async queue · batch INSERT · logging estructurado | ✅ |
| 9 | Manual PyME + arquitectura + API ref + presentación + prompt video | ✅ |

**Tests:** 115/115 pytest pass.
**Imagen Docker:** `ghcr.io/silvaisaac148/sdai-sensor:0.1.0`
**Docs entrega:** [`MANUAL_INSTALACION.md`](./MANUAL_INSTALACION.md) · [`API_REFERENCE.md`](./API_REFERENCE.md) · [`PRESENTACION.md`](./PRESENTACION.md) · [`GEMINI_VIDEO_PROMPT.md`](./GEMINI_VIDEO_PROMPT.md)

---

## Arquitectura

```
                  ┌────────────────────────────────────────────────┐
                  │  Dashboard (SDAI/SDAI Dashboard.html)          │
                  │  Tailwind · Globe.gl · SSE                     │
                  └────────────┬────────────────────────▲──────────┘
                               │ fetch + EventSource     │ SSE push
                               ▼                         │
   POST /capture/start ┌────────────────────────────────┴──────────┐
   POST /capture/stop  │              FastAPI :8000               │
   POST /events/ingest │   routers/  events · alerts · stats ·    │
   GET  /alerts        │             config · capture · live      │
   GET  /stats/*       └─┬──────────────────────────┬─────────────┘
   GET  /events/export   │ in-process               │ supabase-py
   GET  /events/         ▼                          ▼
       investigate/{ip}  capture/state.py        Supabase PostgreSQL
                         │  · DetectionStateManager   tablas:
                         │  · 4 detectores (sliding   - events
                         │    windows + thresholds)   - alerts
                         │  · cooldown anti-spam      - configurations
                         │  · GeoIPResolver (mmdb)
                         │  · notify_alert (async)
                         ▼
                   app/notifications/
                   · telegram.py   (Markdown)
                   · email_smtp.py (TLS)
                   · dispatcher.py (routing severidad)

   Scapy AsyncSniffer  ──►  /events/ingest  ──►  state_manager  ──►  SSE broadcast
   (controlable desde dashboard via /capture/*)
```

Detalle completo en [`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## Requisitos

- **Python 3.12+** (probado 3.12.10)
- **Npcap** en Windows — https://npcap.com/#download (marcar "WinPcap API-compatible Mode")
- **Cuenta Supabase** — https://supabase.com (plan gratuito sobra)
- **GeoLite2-City.mmdb** — descarga gratuita en https://www.maxmind.com (necesita cuenta gratis)

---

## Instalación rápida

```bash
git clone <repo> proyecto_franklin
cd proyecto_franklin

# venv
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux/Mac

pip install -r requirements.txt

# Configuración
cp .env.example .env               # rellenar SUPABASE_URL, SUPABASE_KEY, opcional TELEGRAM/SMTP

# GeoLite2 (opcional pero recomendado para geolocalización real)
python scripts/download_geoip.py   # o copiar tu propio GeoLite2-City.mmdb a db/

# Schema Supabase: pegar db/schema.sql en el SQL Editor del proyecto
# Verificar:
python scripts/verify_schema.py
```

---

## Ejecutar

### Backend + dashboard

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Endpoints disponibles:

| Endpoint | Descripción |
|----------|-------------|
| `GET /dashboard` | UI completa (Globe.gl + SSE en vivo) |
| `GET /docs` | Swagger UI |
| `GET /health` | healthcheck |
| `GET /stats/sensor` | metadata sensor + estado canales notificación |
| `GET /stats/summary` | KPIs + threat distribution + top sources |
| `GET /stats/pps` | packets-per-second + history sparkline |
| `GET /stats/trend?minutes=&buckets=` | severidad stacked en ventana |
| `GET /events` | listado con filtros (`protocol`, `src_ip`, `since`) |
| `GET /events/export` | CSV |
| `GET /events/investigate/{src_ip}` | agregado por IP (eventos+alertas+geo+ports) |
| `GET /alerts` | listado con filtros (`severity`, `resolved`, `since`) |
| `GET /alerts/export` | CSV |
| `PATCH /alerts/{id}/resolve` | marcar como atendida |
| `GET /config` / `POST /config` | umbrales runtime + blacklist |
| `POST /capture/start` / `/stop` / `/pause` / `/resume` | control sniffer |
| `GET /capture/status` | estado capturador |
| `POST /stats/reset` | wipe sliding windows + cooldowns |
| `GET /live/stream` | SSE event+alerts |

### Sniffer en vivo

Dos opciones:

**A) Desde el dashboard** — botón **Encender** en el topbar (requiere Npcap + privilegios admin).

**B) CLI directo** (útil para depurar):
```bash
.venv\Scripts\python.exe -m capture.sniffer -i "Wi-Fi" -c 0 -f "ip"
```

### Demo sin Npcap — simulador de ataques

Útil para grabar video demo o probar el dashboard en cualquier máquina:

```bash
python scripts/simulate_attacks.py                       # todos los escenarios
python scripts/simulate_attacks.py --only port_scan      # solo escaneo
python scripts/simulate_attacks.py --only brute_force
python scripts/simulate_attacks.py --only dos
python scripts/simulate_attacks.py --only malicious_ip
python scripts/simulate_attacks.py --rate 30 --host http://127.0.0.1:8000
```

Las IPs usadas son **públicas reales** (Brandenburg DE, San Petersburgo RU, Moscú RU, etc.) — al pasar por GeoLite2 producen coordenadas reales y aparecen en el globo.

---

## Detectores

Cada detector vive en `capture/detectors/`, recibe un paquete decodificado + estado en memoria + threshold, y retorna `dict | None`.

| Detector | Trigger | Severidad |
|----------|---------|-----------|
| `port_scan` | N puertos distintos por src_ip en 60s | media (≥20) / alta (>30) |
| `brute_force` | N TCP SYN a puerto {22, 21, 23, 3389} en 60s | media (≥5) / alta (>15) |
| `malicious_ip` | src_ip o dst_ip en `configurations.blacklist_ips` | alta |
| `dos` | packets/seg > umbral (default 500) | alta |

Umbrales configurables en vivo desde el dashboard (sliders) → `POST /config`. State manager refresca configs cada 10s. Cooldown 30s por (src_ip, threat_type) evita spam.

---

## Notificaciones

Routing por severidad (configurable en `app/notifications/dispatcher.py`):

| Severidad | Canales |
|-----------|---------|
| alta | Telegram + Email |
| media | Telegram |
| baja | ninguno |

Sin credenciales = no-op silencioso. Para activar:

```env
TELEGRAM_BOT_TOKEN=123456:ABC...           # https://core.telegram.org/bots#how-do-i-create-a-bot
TELEGRAM_CHAT_ID=-1001234567890

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=app_password                  # NO la contraseña real — un app password
SMTP_SENDER=tu_correo@gmail.com
EMAIL_RECIPIENTS=admin@pyme.com,seguridad@pyme.com
```

---

## Tests

```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

Cobertura actual (58 tests):
- `test_sprint1.py` — endpoints base + decoder
- `test_sprint3.py` — detectores + state manager + endpoints stats/events/alerts + investigate + export + reset
- `test_geoip.py` — GeoIPResolver con mock + DB
- `test_notifications.py` — dispatcher por severidad + formatters
- `test_capture_controller.py` — sniffer remoto + callback

---

## Estructura del proyecto

```
proyecto_franklin/
├── backend/app/
│   ├── main.py                       # FastAPI entrypoint
│   ├── config.py                     # Settings (lee .env)
│   ├── services.py                   # singleton state_manager
│   ├── capture_controller.py         # AsyncSniffer remoto
│   ├── notifications/                # Telegram + SMTP dispatcher
│   ├── routers/                      # health, config, events, alerts, stats, live, capture
│   ├── models/schemas.py
│   └── db/supabase_client.py
├── capture/
│   ├── sniffer.py                    # CLI Scapy
│   ├── decoder.py                    # IP/TCP/UDP/ICMP → dict
│   ├── geoip_resolver.py             # GeoLite2 + mock fallback
│   ├── state.py                      # DetectionStateManager
│   └── detectors/                    # port_scan, brute_force, malicious_ip, dos
├── db/
│   ├── schema.sql                    # Supabase setup completo
│   └── migration_geoip.sql           # solo cols geoip si schema base ya existe
├── scripts/
│   ├── verify_schema.py              # chequea tablas + cols GeoIP
│   ├── simulate_attacks.py           # 4 escenarios sin Npcap
│   └── download_geoip.py             # GeoLite2 mmdb downloader
├── tests/                            # pytest, 58 tests
├── SDAI/SDAI Dashboard.html          # UI completa standalone
├── PROGRESO.md                       # bitácora sprints
├── IDEAS_FUTURAS.md                  # roadmap extendido
├── ARCHITECTURE.md                   # diagrama componentes
├── README.md                         # este archivo
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Roadmap

Todos los sprints planificados (1-9) están **completados**. Roadmap post-MVP en [`IDEAS_FUTURAS.md`](./IDEAS_FUTURAS.md):
- Modo IPS (bloqueo iptables auto-generado a partir de alertas)
- Anomaly detection con ML (Isolation Forest sobre baseline 7 días)
- Integración threat intelligence feeds (AbuseIPDB, Spamhaus)
- App móvil nativa (Flutter)
- Multi-tenant SaaS

---

## Licencia

MIT. Ver [`LICENSE`](./LICENSE).
