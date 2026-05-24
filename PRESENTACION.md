# SDAI — Presentación Académica

> Estructura completa de slides para defensa del proyecto.
> Duración estimada: **18-22 minutos** (12-15 slides + Q&A 5 min).

**Equipo:** Isaac Silva · Carlos Herrera · Ángel Ramos
**Institución:** [Universidad/Instituto]
**Materia:** [Materia]
**Año:** 2026

---

## Estructura general

| # | Slide | Tiempo | Quién habla |
|---|-------|--------|-------------|
| 1 | Portada | 30s | Isaac |
| 2 | Problema | 1.5 min | Isaac |
| 3 | Contexto local — PyMEs Barinas | 1 min | Carlos |
| 4 | Estado del arte | 1.5 min | Carlos |
| 5 | Propuesta SDAI | 1 min | Ángel |
| 6 | Arquitectura | 2 min | Ángel |
| 7 | Stack tecnológico | 1 min | Isaac |
| 8 | Pipeline de detección | 2 min | Isaac |
| 9 | Detectores implementados | 1.5 min | Carlos |
| 10 | Dashboard SOC live (demo en vivo o video) | 3 min | Ángel |
| 11 | Resultados — pruebas de carga | 1.5 min | Isaac |
| 12 | Pruebas de detección (simulator) | 1.5 min | Carlos |
| 13 | Limitaciones y gaps conocidos | 1 min | Ángel |
| 14 | Trabajo futuro | 1 min | Isaac |
| 15 | Conclusiones + agradecimientos | 1 min | Todos |
| – | Preguntas | 5 min | Todos |

---

## Slide 1 — Portada

**Contenido visual:**
- Título grande: **SDAI**
- Subtítulo: *Sistema de Detección y Alertas de Intrusiones*
- Tagline: "Ciberseguridad accesible para PyMEs del Estado Barinas"
- Logo / globo 3D del dashboard como background
- Nombres + cédulas del equipo
- Fecha + institución

**Speaker notes:**
> Buenos días/tardes. Somos Isaac, Carlos y Ángel. Vamos a presentar SDAI, un sistema de detección de intrusiones diseñado específicamente para PyMEs que no pueden permitirse un SOC corporativo.

---

## Slide 2 — Problema

**Título:** El 60% de las PyMEs que sufren un ciberataque cierran en 6 meses

**Bullets:**
- Las PyMEs venezolanas son blanco creciente: ransomware, robo de credenciales, ataques DoS
- Soluciones comerciales (Splunk, Darktrace, IBM QRadar) cuestan **$30K-$500K/año**
- Soluciones open-source (Snort, Suricata, Wazuh) requieren personal especializado que las PyMEs no tienen
- Resultado: la mayoría de PyMEs **opera ciega** — descubre el incidente cuando ya es tarde

**Visual:** estadística con icono + comparación de precios (chart bars)

**Speaker notes:**
> Una PyME promedio en Barinas no tiene presupuesto para Splunk ni personal certificado para Suricata. Existe un vacío entre "no tener nada" y "soluciones empresariales". SDAI ataca ese vacío.

---

## Slide 3 — Contexto local: PyMEs en Barinas

**Bullets:**
- Encuesta informal: 12 PyMEs locales (comercio, salud, agroindustria)
  - 11/12 sin IDS de ningún tipo
  - 9/12 desconocen qué es un IDS
  - 12/12 quisieran "saber cuándo algo raro pasa en su red"
- Infraestructura típica: 1 router ISP + 5-20 dispositivos + Wi-Fi
- Personal IT: 0-1 persona (a tiempo parcial)

**Visual:** mapa Barinas + iconos PyMEs + barra "PyMEs sin IDS"

---

## Slide 4 — Estado del arte

| Solución | Precio/año | Curva aprendizaje | Apto PyME |
|----------|-----------|-------------------|-----------|
| Splunk Enterprise | $30K-150K | Alta | ❌ |
| Darktrace | $50K+ | Media | ❌ |
| Suricata + ELK | Gratis | **Muy alta** | ❌ |
| Snort | Gratis | Alta | ❌ |
| Wazuh | Gratis | Alta | ❌ |
| Security Onion | Gratis | Muy alta | ❌ |
| **SDAI (nuestra propuesta)** | **Gratis** | **Baja** | **✅** |

**Speaker notes:**
> Lo gratis existe pero exige perfil técnico. Lo accesible cuesta una fortuna. Vimos hueco entre ambas categorías.

---

## Slide 5 — Propuesta SDAI

**Título:** "Una alarma de seguridad para tu red — instalable en 10 minutos"

**Pilares:**
1. **Open-source y gratis** (MIT)
2. **Instalable con un comando** Docker
3. **Dashboard estilo SOC** sin curva de aprendizaje
4. **Alertas multicanal** (Telegram + email) → llegan donde sea que estés
5. **Geolocalización real** de atacantes → contexto visual inmediato
6. **Pensado para no-técnicos** → vocabulario simple en interfaz

**Visual:** los 6 pilares como iconos circulares

---

## Slide 6 — Arquitectura

**Diagrama** (usar mismo de `ARCHITECTURE.md` README):

```
┌────────────────────────────────────────────────┐
│  Dashboard SOC (HTML + Globe.gl + SSE)        │
└────────────┬────────────────────────▲──────────┘
             │ fetch + EventSource     │ SSE push
             ▼                         │
   ┌────────────────────────────────────────────┐
   │            FastAPI (Python 3.12)           │
   │  routers: events alerts stats config       │
   │           live capture auth ai             │
   └─┬──────────────────────────┬───────────────┘
     │ in-process              │ supabase-py
     ▼                         ▼
   capture/state.py        Supabase PostgreSQL
   · 4 detectores            (events, alerts,
   · cooldown                 configurations)
   · GeoIP enrichment
   · notify_alert (async)
     │
     ▼
   notifications/
   · Telegram (Markdown)
   · Email SMTP (TLS)
   · dispatcher por severidad

   Scapy AsyncSniffer ──► /events/ingest ──► state_manager ──► SSE broadcast
```

**Speaker notes:**
> 5 capas: captura, análisis, persistencia, notificación, presentación. Cada capa intercambiable. El sniffer puede ser Scapy hoy y Suricata mañana sin tocar el resto.

---

## Slide 7 — Stack tecnológico

**Layout 2 columnas:**

**Backend / Lógica:**
- Python 3.12
- FastAPI 0.115 (async HTTP)
- Scapy 2.6 (packet sniffing cross-platform)
- Pydantic 2.9 (validación)
- bcrypt (passwords)
- pytest 8.3 (testing)

**Datos / Infra:**
- Supabase (PostgreSQL managed + RLS)
- MaxMind GeoLite2 (geolocalización)
- Docker + Docker Compose
- GitHub Container Registry (distribución)

**Frontend:**
- HTML5 single-file
- Tailwind CSS (utility CDN)
- Globe.gl + Three.js (3D)
- Server-Sent Events (live)

**Notificaciones:**
- Telegram Bot API
- SMTP (Gmail App Passwords)

**Speaker notes:**
> Stack 100% gratis. Cero licencias. Cero vendor lock-in.

---

## Slide 8 — Pipeline de detección

**Diagrama secuencial:**

```
1. Paquete entra por NIC
        ↓
2. Scapy decodifica → dict
        ↓
3. POST /events/ingest
        ↓
4. ¿Es amenaza? ──── NO ───► Batch INSERT (100 eventos por vez)
        │ SÍ
        ↓
5. GeoIP enrichment (país, ciudad, lat, lon)
        ↓
6. INSERT alert + event
        ↓
7. Dispatch async: Telegram + Email
        ↓
8. SSE push → dashboard renderiza arc en globo 3D
```

**Tiempo total <500ms desde captura → notificación.**

---

## Slide 9 — Detectores implementados

| Detector | Trigger | Severidad |
|----------|---------|-----------|
| **Port Scan** | N puertos distintos por src_ip en 60s | media (≥20) / alta (>30) |
| **Brute Force** | N TCP SYN a puerto auth (22, 21, 23, 3389) en 60s | media (≥5) / alta (>15) |
| **Malicious IP** | IP en `configurations.blacklist_ips` | alta |
| **DoS** | Packets/seg por src_ip > umbral (default 500) | alta |

**Sliding windows en memoria** + **cooldown 30s** por (ip, threat_type) → anti-spam.
**Thresholds editables en vivo** desde dashboard (sliders).

**Speaker notes:**
> Brute force solo cuenta TCP SYN — descarta UDP y HTTP. Esto eliminó 90% de falsos positivos contra streaming y video calls.

---

## Slide 10 — DEMO EN VIVO

> ⚠️ **Esto es demo en vivo** o video pregrabado de 90 segundos.

**Guion demo:**

1. **Login** (5s): `admin` + password → dashboard
2. **Estado base** (10s): globo girando, 0 alertas, sensor encendido
3. **Lanzar simulator** (5s):
   ```bash
   python scripts/simulate_attacks.py --rate 50
   ```
4. **Esperar 30s**: aparecen alertas en cascada
5. **Globo 3D** (15s): arcos animados attacker → sensor con países reales (DE, RU, US)
6. **Modal investigar IP** (15s): clic en una alerta → modal con geo + ports + protocolos
7. **Telegram en celular** (10s): mostrar pantalla del celular con mensajes llegando
8. **Email** (5s): bandeja de entrada con alerta severidad alta
9. **Resolver alerta** (5s): clic resolver → desaparece de la lista activa

**Plan B si la red de demo falla:** video pregrabado 90s.

---

## Slide 11 — Resultados: pruebas de carga

**Objetivo Sprint 7-8:** sostener **10,000 paquetes/min** sin pérdida ni saturación.

**Setup prueba:**
- Hardware: laptop modesta (i5, 8GB RAM)
- Tool: `scripts/load_test.py` (async httpx)
- Duración: 60s sostenidos
- Concurrencia: 50 workers
- Target: 167 pkt/s

**Resultados:**

| Métrica | Objetivo | Real | Estado |
|---------|----------|------|--------|
| Throughput | ≥9,500 pkt/min | ~9,800 pkt/min | ✅ |
| Tasa error | <1% | 0.0% | ✅ |
| Latencia p50 | <100ms | ~45ms | ✅ |
| Latencia p95 | <500ms | ~180ms | ✅ |
| Latencia p99 | <1000ms | ~320ms | ✅ |
| Batch INSERTs ejecutados | — | ~95 (100 events c/u) | — |

**Optimizaciones clave:**
- `asyncio.Queue` desacopla sniffer de DB
- Batch INSERT 100 eventos → 100× menos roundtrips
- Logging JSON estructurado (parseable por ELK/Loki)

---

## Slide 12 — Pruebas de detección

**Setup:** `python scripts/simulate_attacks.py` (todos los escenarios)

| Escenario | Paquetes enviados | Alertas esperadas | Alertas detectadas |
|-----------|-------------------|-------------------|---------------------|
| Baseline normal | 100 | 0 | 0 ✅ |
| Port scan | 80 | 1-2 (port_scan) | 1 ✅ |
| Brute force SSH | 50 | 1 (brute_force) | 1 ✅ |
| DoS flood | 500 | 1 (dos) | 1 ✅ |
| Malicious IP | 10 | varias (malicious_ip) | 8 ✅ |
| **Total** | **740** | **>11** | **11 ✅** |

**Cobertura test suite:** 115/115 pytest pass.

---

## Slide 13 — Limitaciones y gaps conocidos

**Honestidad académica:**

| Gap | Por qué quedó fuera | Mitigación pendiente |
|-----|---------------------|-----------------------|
| Sin TLS local | Fuera del MVP | Reverse proxy nginx + Let's Encrypt |
| No bloquea ataques (IDS, no IPS) | Decisión: detección primero | Integrar reglas iptables basadas en alertas |
| Plan free Supabase: ~150 INSERT/s limit | Hardware/presupuesto | Self-host Postgres si la PyME crece |
| Detección basada en thresholds (no ML) | Costo computacional + dataset | Sprint futuro: anomaly detection (Isolation Forest) |
| Tráfico cifrado: solo metadata, no payload | Limitación física de TLS | No mitigable sin MITM |
| Sin app móvil nativa | Tiempo limitado | Dashboard responsive + Telegram cubren caso de uso |

---

## Slide 14 — Trabajo futuro

**Roadmap propuesto:**

**Corto plazo (3 meses):**
- Modo IPS: reglas iptables auto-generadas
- Detector de exfiltración (volumen anómalo de tráfico saliente)
- Templates HTML para emails

**Medio plazo (6-12 meses):**
- Anomaly detection con ML (PyOD, Isolation Forest)
- Integración con threat intelligence feeds (AbuseIPDB, Spamhaus)
- Multi-tenant: un dashboard, múltiples PyMEs

**Largo plazo:**
- SaaS: SDAI Cloud para PyMEs que no quieran autohospedar
- Federación de threat intelligence entre PyMEs Barinas
- App móvil nativa (Flutter)

---

## Slide 15 — Conclusiones

**Logros:**
- ✅ MVP funcional end-to-end (captura → análisis → notificación → dashboard)
- ✅ 4 detectores con precisión validada
- ✅ Dashboard SOC profesional sin requerir personal especializado
- ✅ Distribución vía Docker GHCR (`docker pull` y a correr)
- ✅ 115/115 tests pass + carga 10k pkt/min sostenida
- ✅ Documentación completa para usuarios no técnicos

**Impacto esperado:**
- Una PyME puede empezar a "ver" su red en menos de 1 hora
- Costo total: **$0**
- Reduce ventana de detección de "días" a "segundos"

**Agradecimientos:**
- [Profesor/tutor]
- PyMEs piloto que prestaron sus redes para pruebas
- Comunidades open-source: Scapy, FastAPI, Supabase, Globe.gl, MaxMind

---

## Q&A — Anticipadas

**P: ¿Por qué no usaron Snort/Suricata directamente?**
R: Esos son IDS de motor profundo (pattern matching DPI). Requieren mantener reglas, parsear PCAPs, calibrar. SDAI hace análisis de comportamiento sobre metadatos — es complementario, no competencia. Para una PyME sin equipo de seguridad, calibrar Snort es prohibitivo.

**P: ¿Qué pasa si el atacante es interno?**
R: SDAI detecta cualquier IP que cumpla los patrones — internas también disparan alertas. Detectores de port_scan y brute_force funcionan igual contra `192.168.x.x`.

**P: ¿Cómo evitan falsos positivos?**
R: Tres capas: (1) thresholds calibrados por tipo de tráfico, (2) cooldown 30s anti-spam, (3) brute_force solo cuenta TCP SYN a puertos auth. En pruebas con tráfico normal de oficina, 0 falsos positivos en 1h.

**P: ¿Y si la PyME no tiene internet?**
R: Requisito mínimo: internet para Supabase + GeoIP + notificaciones. Versión offline (self-hosted Postgres + tile server local) está en roadmap.

**P: ¿Cumple con normativas (GDPR/Ley Especial Datos)?**
R: Diseño: no almacena payloads (contenido), solo metadatos (IPs, puertos). Política de retención configurable (default 30 días eventos, 90 días alertas). Logs de auditoría disponibles.

**P: ¿Escalabilidad?**
R: Probado a 10k pkt/min. Para escalar más: aumentar `batch_size`, migrar a plan Supabase pago o self-hosted, sharding por sensor.

**P: ¿Por qué Python y no Go/Rust?**
R: Productividad del equipo + ecosistema Scapy. El cuello de botella es la DB, no el lenguaje. Si fuera necesario, el sniffer se puede reescribir en Go independientemente.

**P: ¿Quién mantiene el proyecto después de entregar?**
R: Repositorio público en GitHub. Licencia MIT. Equipo se compromete a mantener 6 meses post-entrega.

---

## Recursos para acompañar la presentación

- Repositorio: https://github.com/silvaisaac148/SDAI
- Imagen Docker: `ghcr.io/silvaisaac148/sdai-sensor:0.1.0`
- Manual: `MANUAL_INSTALACION.md`
- Arquitectura: `ARCHITECTURE.md`
- API Reference: `API_REFERENCE.md`
- Video demo: [link YouTube/Drive cuando esté grabado]

---

## Notas de producción

**Para slides reales (Canva / PowerPoint / Keynote / Marp):**
- Paleta: dark mode con acentos cian (matching dashboard SDAI)
- Tipografía: Inter / IBM Plex Sans
- Cada slide: 1 idea principal, ≤5 bullets, 1 visual
- Capturas reales del dashboard, no mockups
- Logo SDAI en esquina inferior derecha (consistencia)

**Para defensa oral:**
- Ensayar timing con cronómetro (objetivo: terminar en 18min, dejar 4min buffer)
- Demo en vivo: tener video pregrabado de respaldo
- Imprimir 3 copias del documento por si falla proyector
- Llevar laptop con backend ya levantado + Telegram celular en silencio activo
