# SDAI — Guía de despliegue para el equipo

> Para Carlos Herrera, Ángel Ramos y futuros colaboradores que quieran correr SDAI en su propia máquina/red.

Esta guía explica cómo cada miembro del equipo puede:
- Correr **su propio sensor SDAI** desde su laptop/PC
- Detectar tráfico real de **su propia tarjeta de red**
- Compartir las alertas en el **mismo dashboard Supabase del equipo**
- Acceder a través de **URL pública** (Cloudflare Tunnel)

---

## 🧭 Dos modelos posibles

### Modelo A — Cada uno corre su propia instancia (independiente)
```
[Carlos laptop] ──► sensor Carlos ──► Supabase Carlos (cuenta propia)
[Angel laptop]  ──► sensor Angel  ──► Supabase Angel  (cuenta propia)
[Isaac laptop]  ──► sensor Isaac  ──► Supabase Isaac  (cuenta propia)
```
**Cuándo:** prácticas individuales, aprender, tests aislados.
**Pro:** cero conflicto. Cada uno experimenta sin afectar a otros.
**Contra:** no se ven entre sí.

### Modelo B — Todos comparten Supabase (multi-sensor) ⭐
```
[Carlos laptop] ──► sensor Carlos ──┐
[Angel laptop]  ──► sensor Angel  ──┤──► Supabase compartido ──► Dashboard único
[Isaac laptop]  ──► sensor Isaac  ──┘                              (todos ven todo)
```
**Cuándo:** demo equipo, defensa académica, simular PyME con varias sedes.
**Pro:** dashboard agregado, datos reales de 3 redes, más impactante.
**Contra:** un error de un sensor afecta a todos. Necesitas coordinarse.

**Recomendado para la defensa:** Modelo B durante la demo + Modelo A para pruebas personales.

---

## 🚀 Setup paso a paso (para cada compañero)

### Paso 1 — Clonar repositorio

```bash
git clone https://github.com/silvaisaac148/SDAI.git
cd SDAI
```

### Paso 2 — Elegir método de instalación

| Método | Para quién |
|--------|-----------|
| **A) Docker** (recomendado) | Ubuntu/Linux/Mac. 10 min. |
| **B) Código nativo Windows** | Sin Docker. Requiere Npcap. 30 min. |
| **C) Imagen Docker pre-construida** | Forma más rápida en cualquier OS con Docker. 5 min. |

Detalles completos en [`MANUAL_INSTALACION.md`](./MANUAL_INSTALACION.md) secciones 5-7.

### Paso 3 — Configurar `.env`

Copia el template:
```bash
cp .env.example .env
```

Edita `.env` con tus valores. Para **Modelo B (compartido)**, Isaac te pasará:
- `SUPABASE_URL` (mismo para los 3)
- `SUPABASE_KEY` (mismo para los 3)
- `SESSION_SECRET_KEY` (mismo si quieres compartir sesiones, o propio si no)

**Tu password personal (Carlos / Ángel)** te la dará Isaac por canal privado.

Variables que cambias **tú** según tu máquina:
```env
CAPTURE_INTERFACE=Wi-Fi        # Windows: "Wi-Fi" o "Ethernet"
                               # Linux: "wlan0", "eth0", "enp0s3"
                               # Mac: "en0"

ADMIN_USERNAME=carlos_herrera  # o angel_ramos
ADMIN_PASSWORD=<la que te dio Isaac>

# AI (opcional, registra TU propia key gratis):
GROQ_API_KEY=<la tuya desde https://console.groq.com>

# Si quieres usar tu propio Telegram personal:
TELEGRAM_BOT_TOKEN=<tu bot, opcional>
TELEGRAM_CHAT_ID=<tu chat>
```

### Paso 4 — Listar tu interfaz de red

**Windows PowerShell:**
```powershell
Get-NetAdapter | Select-Object Name, Status, MacAddress
```

**Linux:**
```bash
ip link show
# o
ifconfig
```

**Mac:**
```bash
networksetup -listallhardwareports
```

Pon el nombre exacto en `CAPTURE_INTERFACE` del `.env`.

### Paso 5 — Arrancar SDAI

**Con Docker:**
```bash
docker compose up -d
docker compose logs -f
```

**Con código nativo Windows:**
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

**Con código nativo Linux:**
```bash
source .venv/bin/activate
sudo .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
`sudo` es necesario en Linux para que Scapy capture.

### Paso 6 — Encender el sniffer

Abre http://localhost:8000/dashboard → login → botón **Encender** en topbar.

A partir de aquí, **tu tarjeta de red está siendo monitoreada**. Cualquier paquete que pase por ella alimenta al sistema.

### Paso 7 — Verificar funciona

Lanza un ataque simulado contra ti mismo:
```bash
python scripts/simulate_attacks.py --only port_scan --rate 30
```

En el dashboard debes ver:
- KPI "Paquetes" sube
- Aparece alerta `port_scan` en el panel
- Globo dibuja arco hacia tu sensor

---

## 🌐 Acceder vía URL pública (Cloudflare Tunnel)

### Por qué

Sin tunnel:
- Solo accedes desde tu laptop (`http://localhost:8000`)
- Tus compañeros no pueden ver tu dashboard
- Profesor no puede revisar desde su PC

Con tunnel:
- URL `https://xxxxx.trycloudflare.com` accesible desde cualquier red mundial
- HTTPS automático
- Cero config de router/firewall

### Setup automatizado (script)

Ejecuta una sola vez:
```powershell
# Windows PowerShell
.\scripts\deploy_tunnel.ps1
```

Output esperado:
```
════════════════════════════════════════════════════════════════
  SDAI EN PRODUCCION
════════════════════════════════════════════════════════════════

  URL publica (comparte con quien debas):
    https://random-words-12345.trycloudflare.com

  Dashboard:
    https://random-words-12345.trycloudflare.com/dashboard

  Procesos activos:
    backend PID 12345
    tunnel  PID 67890
```

URL ya copiada en tu portapapeles → pégala donde la necesites.

### Para detener todo:
```powershell
.\scripts\deploy_tunnel.ps1 -Stop
```

### Para Linux/Mac (equivalente)
```bash
# 1. Descargar cloudflared
curl -L -o cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
chmod +x cloudflared

# 2. Arrancar backend en una terminal
docker compose up

# 3. Arrancar tunnel en otra terminal
./cloudflared tunnel --url http://localhost:8000
```

---

## 👥 Pasar credenciales al equipo

Isaac maneja la creación de usuarios. Si Carlos o Ángel necesitan acceso:

```bash
# Isaac corre:
python scripts/create_user.py nombre_nuevo --role admin --insert
# Password: (escribe una temporal)
# Confirm:  (repite)

# Comparte con el compañero por canal seguro (NO email, mejor Telegram secret chat o WhatsApp):
#   Usuario: nombre_nuevo
#   Password: <temporal>
#   URL: https://xxxxx.trycloudflare.com
```

El compañero al loguearse por primera vez **debería** cambiar su password. Como SDAI no tiene endpoint `PATCH /auth/me/password` aún (roadmap), el cambio se hace re-corriendo `create_user.py` con el mismo username.

---

## 🔄 Sincronizar cambios de Isaac

Cuando Isaac haga `git push` con mejoras, los compañeros bajan:
```bash
cd SDAI
git pull origin main

# Si hay deps nuevas:
pip install -r requirements.txt
# o
docker compose pull && docker compose up -d
```

---

## 📡 Modelo B: configurar multi-sensor compartido

Si los 3 corren al mismo tiempo apuntando al mismo Supabase, las alertas se acumulan en la misma tabla. El dashboard muestra el agregado.

**Para distinguir qué sensor disparó cada alerta** (no implementado actualmente, gap conocido), añadir en futuro:
- Campo `sensor_id` en `events` y `alerts`
- Pasarlo en `POST /events/ingest` como header `X-Sensor-Id`
- Dashboard filtra por sensor

**Workaround actual:** cada sensor tiene `CAPTURE_INTERFACE` y red distinta → IPs origen serán diferentes → se puede inferir por geo.

---

## 🛡️ Buenas prácticas equipo

| Hacer | No hacer |
|-------|----------|
| Comunicar antes de hacer `docker compose down` si están en demo | Resetear DB Supabase sin avisar |
| Pulir thresholds en local antes de pushear `configurations` | Subir credenciales al `.env.example` |
| Crear branch propio para experimentos: `git checkout -b carlos/feature-x` | Pushear directo a main sin revisar |
| Compartir password via canal cifrado (Signal, Telegram secret) | Pegar passwords en grupos abiertos |
| Verificar tests pasan antes de push: `pytest` | Saltarse tests "porque demora" |

---

## ❓ Problemas comunes equipo

**P: "Cuando hago `git pull` me dice conflicto con .env"**
R: `.env` está en `.gitignore`, no debería estar tracked. Si lo está, sácalo: `git rm --cached .env`. Cada uno tiene su `.env` local.

**P: "Mi dashboard no muestra alertas de Carlos"**
R: Verifica que ambos `.env` apuntan al MISMO `SUPABASE_URL`. Si no, están en bases separadas (Modelo A).

**P: "El tunnel se cae cuando suspendo mi laptop"**
R: Es esperado. Cloudflare Tunnel quick URL es efímera. Para defensa: NO suspender. Para producción real: usar VPS (no laptop).

**P: "Como sabemos qué sensor disparo qué alerta?"**
R: Mira el campo `src_ip` y `geo`. Los 3 estarán en redes distintas → IPs y países diferentes. Roadmap futuro: campo `sensor_id` explícito.

**P: "Puedo usar mi propio Telegram y email en vez de los de Isaac?"**
R: Sí. Cada `.env` tiene sus propias notificaciones. Sería bueno que cada uno tenga su bot Telegram personal para no spammear el de Isaac.

---

## 🎯 Workflow día de la defensa

```
30 min antes:
  [Isaac]  cd SDAI && .\scripts\deploy_tunnel.ps1
           → copia URL pública
           → envía al profesor por WhatsApp/email

10 min antes:
  [Isaac]  Verifica URL abre dashboard en otro dispositivo
  [Carlos] Tiene su laptop encendida, sensor corriendo local (no tunnel)
  [Ángel]  Tiene su laptop encendida, sensor corriendo local (no tunnel)

Durante defensa:
  [Isaac]  Comparte pantalla → demo en vivo simulator
  [Carlos] Si Isaac queda corto, lanza simulator desde su laptop
  [Ángel]  Si red Isaac falla, tiene backup local con misma demo

Al terminar:
  [Isaac]  .\scripts\deploy_tunnel.ps1 -Stop
           → cierra tunnel + backend
```

---

## 🚨 Plan B si tunnel falla

Si Cloudflare está caído o tu red lo bloquea:

**Opción 1: ngrok**
```powershell
# Descargar: https://ngrok.com/download
ngrok http 8000
# URL temporal random 1h sesión gratis
```

**Opción 2: presentar local**
- Llevar laptop al aula
- Conectar a proyector/HDMI
- Profesor ve directamente
- Sin URL pública necesaria

**Opción 3: video pregrabado**
- Tener listo el video de `GEMINI_VIDEO_PROMPT.md` ya generado
- Reproducirlo en vez de demo en vivo

---

## 📚 Referencias

- [`MANUAL_INSTALACION.md`](./MANUAL_INSTALACION.md) — instalación detallada cada OS
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — cómo funciona internamente
- [`API_REFERENCE.md`](./API_REFERENCE.md) — endpoints HTTP
- [`PRESENTACION.md`](./PRESENTACION.md) — slides defensa
