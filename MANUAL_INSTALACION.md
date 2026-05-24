# SDAI — Manual de Instalación y Operación

> **Sistema de Detección y Alertas de Intrusiones**
> Para PyMEs, estudiantes de redes/ciberseguridad y administradores noveles.

Este manual está pensado para que **cualquier persona**, aún sin experiencia previa en Docker, Linux o ciberseguridad, pueda **instalar, arrancar, configurar y operar** SDAI en su red.

---

## Índice

1. [¿Qué es SDAI?](#1-qué-es-sdai)
2. [Glosario rápido](#2-glosario-rápido-para-no-técnicos)
3. [Requisitos del equipo](#3-requisitos-del-equipo)
4. [Métodos de instalación](#4-métodos-de-instalación)
5. [Método A — Docker (recomendado)](#5-método-a--docker-pull-desde-github-recomendado)
6. [Método B — Linux desde código](#6-método-b--linux-desde-código-fuente)
7. [Método C — Windows desde código](#7-método-c--windows-desde-código-fuente)
8. [Crear cuenta Supabase + cargar schema](#8-crear-cuenta-supabase--cargar-schema)
9. [Configurar Telegram para alertas](#9-configurar-telegram-para-alertas)
10. [Configurar Gmail SMTP para alertas](#10-configurar-gmail-smtp-para-alertas)
10.5. [Configurar tutor IA (Groq / Gemini) — opcional pero recomendado](#105-configurar-tutor-ia-groq--gemini--opcional-pero-recomendado)
11. [Configurar el archivo .env completo](#11-configurar-el-archivo-env-completo)
12. [Primer arranque y verificación](#12-primer-arranque-y-verificación)
13. [Uso del dashboard SOC](#13-uso-del-dashboard-soc)
14. [Operación diaria](#14-operación-diaria)
15. [Pruebas — simular ataques](#15-pruebas--simular-ataques)
16. [Resolución de problemas](#16-resolución-de-problemas)
17. [Seguridad — buenas prácticas](#17-seguridad--buenas-prácticas)
18. [FAQ](#18-faq)

---

## 1. ¿Qué es SDAI?

SDAI es un **detector de intrusiones de red** (IDS, *Intrusion Detection System*). Funciona como una alarma de seguridad para tu red local: vigila todo el tráfico que pasa por la tarjeta de red de la computadora donde lo instales y avisa cuando detecta comportamientos sospechosos.

**Las 4 amenazas que detecta:**

| Amenaza | Qué significa | Ejemplo real |
|---------|---------------|--------------|
| **Port Scan** | Alguien está "tocando puertas" en muchos puertos buscando servicios | Un atacante intenta puertos 21, 22, 80, 443, 3306, 3389... uno tras otro |
| **Brute Force** | Intentos repetidos de adivinar contraseña | 500 intentos de login en SSH (puerto 22) en 1 minuto |
| **DoS** | Inundación de tráfico para tumbar un servicio | 50,000 paquetes/seg contra tu servidor web |
| **IP Maliciosa** | Una IP en lista negra te está contactando | Una IP conocida por enviar spam o ataques aparece en tu red |

**Cuándo aparece una alerta:**

```
1. Captura paquete → 2. Pasa por 4 detectores → 3. Si alguno se dispara:
                                                  ├─ Guarda alerta en base de datos
                                                  ├─ Resuelve geolocalización (país, ciudad)
                                                  ├─ Muestra en dashboard (globo 3D)
                                                  ├─ Envía mensaje Telegram
                                                  └─ Envía email
```

---

## 2. Glosario rápido (para no técnicos)

| Término | Significado |
|---------|-------------|
| **IP** | Dirección numérica de un dispositivo en una red. Ej: `192.168.1.10` (privada) o `8.8.8.8` (pública de Google) |
| **Puerto** | "Subdivisión" de una IP. Cada servicio usa un puerto fijo: 80=web, 443=web seguro, 22=SSH, 25=email |
| **Paquete** | Unidad mínima de información que viaja por una red |
| **TCP/UDP/ICMP** | Protocolos: TCP=conexión confiable (web), UDP=rápido sin garantía (DNS, video), ICMP=control (ping) |
| **NIC** | Network Interface Card. La tarjeta de red de tu computadora (Wi-Fi o Ethernet) |
| **Sniffer** | Programa que "escucha" todo el tráfico que pasa por la NIC |
| **Docker** | Tecnología que empaqueta una aplicación con todo lo que necesita para correr, sin instalar dependencias en tu sistema |
| **Contenedor** | Una instancia corriendo de una imagen Docker |
| **GHCR** | GitHub Container Registry. Servidor donde GitHub guarda imágenes Docker |
| **API** | Interfaz programática. Conjunto de URLs que recibe peticiones JSON |
| **Dashboard** | Página web con gráficos y métricas en vivo |
| **SOC** | Security Operations Center. Sala donde se monitorea seguridad. SDAI imita un mini-SOC |
| **Supabase** | Base de datos PostgreSQL en la nube, gratis hasta cierto tamaño |
| **SSE** | Server-Sent Events. Tecnología que permite al servidor empujar datos al navegador en vivo |
| **GeoIP** | Base de datos que traduce IP → país/ciudad/coordenadas |
| **Severidad** | Nivel de gravedad de una alerta: baja, media, alta |
| **Cooldown** | Tiempo de espera entre alertas iguales (evita spam) |

---

## 3. Requisitos del equipo

### Mínimos (cualquier método)

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 2 núcleos | 4 núcleos |
| RAM | 2 GB | 4 GB |
| Disco | 5 GB libres | 10 GB libres |
| Internet | Requerido para Supabase + GeoIP + GitHub | Banda ancha estable |
| Tarjeta de red | Cualquiera (Wi-Fi o Ethernet) | Ethernet (más estable) |

### Sistema operativo

| OS | Docker | Desde código |
|----|--------|--------------|
| **Linux** (Ubuntu 22.04+, Debian, Fedora) | ✅ Recomendado | ✅ Funciona |
| **Windows 10/11 Pro** | ⚠️ Requiere WSL2 + Docker Desktop | ✅ Funciona con Npcap |
| **macOS** | ⚠️ Funciona pero el sniffer no captura en `network_mode: host` | ⚠️ Limitado |
| **Raspberry Pi 4/5** (ARM64) | ✅ Excelente para producción | ✅ Funciona |

### Cuentas externas (gratis)

- **GitHub** — para clonar el repositorio
- **Supabase** — base de datos (https://supabase.com — plan free sobra)
- **MaxMind** — descargar `GeoLite2-City.mmdb` (https://www.maxmind.com — cuenta gratis)
- **Telegram** (opcional) — recibir alertas en celular
- **Gmail** (opcional) — recibir alertas por email

---

## 4. Métodos de instalación

Hay tres caminos, elige según tu caso:

| Método | Para quién | Tiempo | Dificultad |
|--------|-----------|--------|------------|
| **A. Docker pull desde GitHub** | Producción, PyMEs, demos rápidos. **No necesitas el código fuente** | 10 min | ⭐ Fácil |
| **B. Linux desde código fuente** | Estudiantes, desarrollo, modificar el código | 20 min | ⭐⭐ Media |
| **C. Windows desde código fuente** | Aprender en tu PC habitual | 30 min | ⭐⭐⭐ Difícil (Npcap, permisos admin) |

---

## 5. Método A — Docker pull desde GitHub (recomendado)

Este método **no requiere descargar el código**. Solo necesitas Docker. La imagen ya está publicada en GitHub Container Registry (GHCR).

### 5.1. Instalar Docker

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# Cerrar sesión y volver a abrir, o reiniciar
```

**Windows 10/11:**
- Descarga **Docker Desktop**: https://www.docker.com/products/docker-desktop
- Instálalo. Reinicia Windows.
- Abre Docker Desktop al menos una vez para inicializar WSL2.

**macOS:**
- Descarga **Docker Desktop for Mac**: https://www.docker.com/products/docker-desktop

**Verificar:**
```bash
docker --version
# Debe mostrar: Docker version 24.x o superior
docker compose version
# Debe mostrar: Docker Compose version v2.x
```

### 5.2. Crear carpeta de trabajo

```bash
mkdir ~/sdai
cd ~/sdai
```

### 5.3. Bajar imagen desde GHCR

```bash
docker pull ghcr.io/silvaisaac148/sdai-sensor:0.1.0
```

Espera 1-3 minutos según tu conexión.

### 5.4. Crear archivo `.env`

Crea un archivo llamado exactamente `.env` (con el punto al inicio) dentro de `~/sdai`:

```bash
nano .env       # Linux
notepad .env    # Windows (guardar como tipo "Todos los archivos")
```

Pega esto y rellena los valores reales (ver secciones 8–11 para obtener cada uno):

```env
# === Base de datos Supabase ===
SUPABASE_URL=https://tuproyecto.supabase.co
SUPABASE_KEY=eyJhbGciOi...tu_service_role_key...

# === API ===
API_HOST=0.0.0.0
API_PORT=8000

# === Captura ===
CAPTURE_INTERFACE=eth0
CAPTURE_COUNT=0

# === Telegram (opcional pero recomendado) ===
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# === Email Gmail (opcional) ===
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_SENDER=
SMTP_USE_TLS=true
EMAIL_RECIPIENTS=

# === IA (opcional — tutor explicativo en dashboard) ===
GEMINI_API_KEY=
GROQ_API_KEY=

# === Autenticación SOC ===
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ELIGE_UNA_CONTRASEÑA_FUERTE_AQUI
SESSION_SECRET_KEY=PEGA_AQUI_LA_CADENA_LARGA_QUE_GENERES
SESSION_COOKIE_SECURE=false

# === CORS ===
CORS_ALLOWED_ORIGINS=*

# === Logs ===
LOG_FORMAT=json
LOG_LEVEL=INFO
```

**Generar `SESSION_SECRET_KEY`** (corre uno y pega el resultado):
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
# o si no tienes Python instalado:
docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 5.5. Crear `docker-compose.yml`

```bash
nano docker-compose.yml
```

Pega:

```yaml
version: '3.8'

services:
  sdai-sensor:
    image: ghcr.io/silvaisaac148/sdai-sensor:0.1.0
    container_name: sdai_sensor
    restart: unless-stopped

    # Linux: comparte el stack de red del host → Scapy ve la NIC real
    network_mode: "host"

    cap_add:
      - NET_ADMIN
      - NET_RAW

    env_file:
      - .env

    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - LOG_FORMAT=json
      - LOG_LEVEL=INFO

    volumes:
      - ./db:/app/db:rw

    healthcheck:
      test: ["CMD", "curl", "--fail", "--silent", "http://127.0.0.1:8000/health"]
      interval: 30s
      timeout: 4s
      retries: 3
      start_period: 10s
```

**⚠️ En Windows/macOS:** `network_mode: "host"` NO funciona. Reemplaza por mapeo de puertos:

```yaml
    # network_mode: "host"        # ← coméntalo
    ports:
      - "8000:8000"                # ← añade esto
```

Limitación: en Windows el sniffer no verá tu NIC real desde el contenedor. Para análisis de tu red local en Windows usa Método C (código nativo con Npcap).

### 5.6. Crear schema en Supabase

Antes de arrancar necesitas las tablas. Ver [sección 8](#8-crear-cuenta-supabase--cargar-schema).

### 5.7. Arrancar

```bash
docker compose up -d
```

Verifica:
```bash
docker compose ps
docker compose logs -f sdai-sensor
# Ctrl+C para salir de los logs (el contenedor sigue corriendo)
```

### 5.8. Abrir el dashboard

Abre tu navegador en: **http://localhost:8000/dashboard**

Login: `admin` + la contraseña que pusiste en `ADMIN_PASSWORD`.

### 5.9. Detener / actualizar

```bash
# Detener
docker compose down

# Actualizar a una nueva versión publicada
docker pull ghcr.io/silvaisaac148/sdai-sensor:0.1.0   # o la versión nueva
docker compose up -d
```

---

## 6. Método B — Linux desde código fuente

Para estudiantes que quieren leer y modificar el código.

### 6.1. Instalar requisitos del sistema

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip git libpcap-dev tcpdump
```

### 6.2. Clonar repositorio

```bash
cd ~
git clone https://github.com/silvaisaac148/SDAI.git
cd SDAI
```

### 6.3. Crear entorno virtual + instalar dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6.4. Crear `.env`

```bash
cp .env.example .env
nano .env
```

Rellena los valores (ver secciones 8–11).

### 6.5. Cargar schema Supabase

Ver [sección 8](#8-crear-cuenta-supabase--cargar-schema).

### 6.6. Descargar GeoLite2 (opcional)

```bash
python scripts/download_geoip.py
# o copia manualmente tu GeoLite2-City.mmdb a db/
```

### 6.7. Verificar schema

```bash
python scripts/verify_schema.py
# Debe mostrar OK en las 3 tablas
```

### 6.8. Arrancar backend

```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

### 6.9. (Opcional) Arrancar sniffer CLI

En **otra terminal**:
```bash
source .venv/bin/activate

# Listar interfaces disponibles
ip link show

# Arrancar sniff continuo en la NIC correcta
sudo .venv/bin/python -m capture.sniffer -i eth0 -c 0 -f "ip"
```

`sudo` es obligatorio en Linux porque Scapy necesita modo promiscuo.

### 6.10. Tests

```bash
pytest -v
# 115/115 deben pasar
```

---

## 7. Método C — Windows desde código fuente

Más complejo por la dependencia de Npcap, pero útil para desarrollo y pruebas en tu PC habitual.

### 7.1. Instalar Python 3.12

- Descarga: https://www.python.org/downloads/
- Durante la instalación marca **"Add Python to PATH"**.

### 7.2. Instalar Git

- Descarga: https://git-scm.com/download/win
- Acepta las opciones por defecto.

### 7.3. Instalar Npcap (CRÍTICO para captura)

Sin esto Scapy no captura nada en Windows.

- Descarga: https://npcap.com/#download
- **MUY IMPORTANTE:** durante la instalación marca:
  - ☑ **"Install Npcap in WinPcap API-compatible Mode"**
  - ☑ **"Support raw 802.11 traffic"** (si quieres Wi-Fi monitor mode)

### 7.4. Clonar repositorio

Abre **PowerShell** (Win+X → Terminal):

```powershell
cd $env:USERPROFILE\Desktop
git clone https://github.com/silvaisaac148/SDAI.git
cd SDAI
```

### 7.5. Crear venv + dependencias

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Si PowerShell bloquea la activación:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

pip install --upgrade pip
pip install -r requirements.txt
```

### 7.6. Crear `.env`

```powershell
Copy-Item .env.example .env
notepad .env
```

Rellena los valores. En Windows el `CAPTURE_INTERFACE` se llama distinto:

```env
CAPTURE_INTERFACE=Wi-Fi
# o:
CAPTURE_INTERFACE=Ethernet
```

Para listar nombres exactos disponibles:
```powershell
Get-NetAdapter | Select-Object Name, InterfaceDescription, Status
```

### 7.7. Cargar schema + GeoLite2

Igual que Linux ([sección 8](#8-crear-cuenta-supabase--cargar-schema)).

```powershell
python scripts/download_geoip.py
python scripts/verify_schema.py
```

### 7.8. Arrancar backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### 7.9. Arrancar sniffer CLI (PowerShell **como Administrador**)

Botón Win → "PowerShell" → clic derecho → "Ejecutar como administrador":

```powershell
cd $env:USERPROFILE\Desktop\SDAI
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m capture.sniffer -i "Wi-Fi" -c 0 -f "ip"
```

### 7.10. Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

---

## 8. Crear cuenta Supabase + cargar schema

### 8.1. Crear cuenta

1. Ve a https://supabase.com → **Start your project** → registrarse con GitHub o email.
2. **New project**:
   - Name: `sdai-pyme`
   - Database password: genera una fuerte y **guárdala**.
   - Region: la más cercana (ej. `South America (São Paulo)`).
3. Espera 1-2 minutos a que se aprovisione.

### 8.2. Obtener credenciales

En el proyecto creado:

- **Project Settings** (engranaje izquierda) → **API**:
  - `Project URL` → eso va en `SUPABASE_URL`
  - `Project API keys` → copia **`service_role`** (NO la `anon`) → va en `SUPABASE_KEY`

> ⚠️ **`service_role` tiene acceso total.** Nunca la subas a un repo público ni la pongas en el navegador. Solo el backend la usa.

### 8.3. Cargar schema

1. En Supabase → **SQL Editor** (icono de base de datos) → **New query**.
2. Abre el archivo `db/schema.sql` del repositorio en tu editor de texto.
3. Copia **TODO** el contenido y pégalo en el SQL Editor de Supabase.
4. Clic en **RUN** (esquina inferior derecha).
5. Debe responder `Success`. Si da error, lee el mensaje — usualmente es porque las tablas ya existen.

### 8.4. Verificar

Local:
```bash
python scripts/verify_schema.py
```

En Supabase: **Table Editor** debe mostrar las 3 tablas: `events`, `alerts`, `configurations`.

---

## 9. Configurar Telegram para alertas

### 9.1. Crear un Bot

1. Abre Telegram en tu celular o PC.
2. Busca **@BotFather** (el oficial con la marca azul de verificación).
3. Envía `/newbot`.
4. BotFather pide:
   - **Nombre del bot** (lo que verás en chats): ej. `SDAI Alertas PyME`
   - **Username** (debe terminar en `bot`): ej. `sdai_pyme_alertas_bot`
5. BotFather responde con un **token** así:
   ```
   1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ-12345
   ```
6. **Cópialo** → eso va en `TELEGRAM_BOT_TOKEN`.

### 9.2. Obtener tu Chat ID

**Opción A — chat personal:**
1. Busca a tu bot recién creado en Telegram (por el username).
2. Envíale `/start` o cualquier mensaje (esto "abre" la conversación).
3. En tu navegador visita:
   ```
   https://api.telegram.org/bot<TU_TOKEN>/getUpdates
   ```
   Ej:
   ```
   https://api.telegram.org/bot1234567890:ABCdef.../getUpdates
   ```
4. Verás un JSON. Busca:
   ```json
   "chat":{"id":987654321,"first_name":"Tu Nombre",...}
   ```
5. Ese `987654321` es tu `TELEGRAM_CHAT_ID`.

**Opción B — grupo de equipo:**
1. Crea un grupo en Telegram, añade a tu bot como miembro.
2. **Hazlo administrador** del grupo.
3. Envía cualquier mensaje en el grupo.
4. Visita el mismo `getUpdates`. Busca el campo `chat.id` con valor **negativo** (ej. `-1001234567890`).
5. Ese número (con el signo `-`) va en `TELEGRAM_CHAT_ID`.

### 9.3. Probar

Una vez configurado en `.env`, reinicia SDAI. Lanza un ataque simulado (sección 15) y deberías recibir un mensaje así:

```
🚨 ALERTA SDAI

Tipo: Port Scan
Severidad: alta
Origen: 45.155.205.231 (Brandenburg, DE)
Destino: 192.168.1.10
Descripción: 35 puertos distintos en 60s
Hora: 2026-05-24 14:32:18 UTC
```

---

## 10. Configurar Gmail SMTP para alertas

Gmail no permite usar tu contraseña normal con SMTP — necesitas un **App Password**.

### 10.1. Activar verificación en dos pasos

Obligatorio para generar App Passwords.

1. Ve a https://myaccount.google.com/security
2. **Verificación en dos pasos** → activar (te pedirá SMS o app autenticadora).

### 10.2. Generar App Password

1. Ve a https://myaccount.google.com/apppasswords
2. Selecciona:
   - App: **Mail**
   - Device: **Other (Custom)** → escribe `SDAI`
3. Genera. Obtienes una contraseña de **16 caracteres** así:
   ```
   abcd efgh ijkl mnop
   ```
4. **Copia los 16 caracteres SIN ESPACIOS**: `abcdefghijklmnop`

### 10.3. Llenar `.env`

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tucorreo@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_SENDER=tucorreo@gmail.com
SMTP_USE_TLS=true
EMAIL_RECIPIENTS=admin@tupyme.com,gerente@tupyme.com,seguridad@tupyme.com
```

`EMAIL_RECIPIENTS` admite múltiples emails separados por coma — todos reciben las alertas de severidad **alta**.

### 10.4. Probar

Reinicia SDAI. Las alertas severidad alta llegarán también por email.

> **¿Por qué solo "alta" recibe email?** Política de ruteo: las alertas medias (Telegram) son frecuentes; las altas son críticas y merecen un segundo canal. Configurable en `backend/app/notifications/dispatcher.py`.

---

## 10.5. Configurar tutor IA (Groq / Gemini) — opcional pero recomendado

SDAI incluye un **tutor pedagógico de ciberseguridad** integrado en el dashboard. Te explica cada alerta en lenguaje simple, propone planes de mitigación didácticos y responde preguntas sobre redes/seguridad. Útil para administradores no expertos y para enseñanza.

### ⚠️ IMPORTANTE — Cada usuario debe usar su PROPIA API key

> **La imagen Docker que distribuimos en GHCR NO incluye ninguna API key.**
> Si activas el tutor IA, debes registrar **tu propia cuenta gratuita** en Groq o Google AI Studio y poner **tu propia key** en el `.env`. Esto es por dos razones:
>
> 1. **Costo:** las APIs IA cobran por uso (aunque tengan capa gratis). Si todos usan la misma key, esa cuota se agota en minutos y el servicio deja de funcionar para todos.
> 2. **Privacidad:** tu key te pertenece. No la compartas, no la subas a Git, no la pegues en chats.
>
> **Sin API key configurada:** el tutor IA cae a **modo heurístico local** — respuestas pre-escritas para los 4 ataques principales. Funciona pero es más limitado. **Suficiente para demo y uso básico.**

### Opción A — Groq (recomendado: gratis y rápido)

Groq tiene la **mejor capa gratuita actual** (miles de requests/día) y respuestas en <1 segundo gracias a sus LPUs.

**Pasos:**

1. Ve a https://console.groq.com
2. **Sign up** con Google o email (gratis, sin tarjeta de crédito).
3. Verifica tu email.
4. Una vez dentro: menú lateral → **API Keys** → **Create API Key**.
5. Nombre: `SDAI`. Clic crear.
6. **Copia la key inmediatamente** (formato: `gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx`). Solo se muestra una vez.
7. Pega en tu `.env`:
   ```env
   GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
8. Reinicia SDAI.

**Modelo usado:** `llama-3.3-70b-versatile` (configurado en `backend/app/routers/ai.py`).
**Quota gratis (al 2026):** ~14,400 requests/día, 30 req/min. Más que suficiente para una PyME 24/7.

### Opción B — Google Gemini (alternativa gratis)

Funciona igual de bien, ligeramente más lento.

**Pasos:**

1. Ve a https://aistudio.google.com/apikey
2. Inicia sesión con cuenta Google.
3. **Create API key** → selecciona o crea un proyecto Google Cloud (gratis).
4. Copia la key (formato: `AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXX`).
5. Pega en tu `.env`:
   ```env
   GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXX
   ```
6. Reinicia SDAI.

**Modelo usado:** `gemini-2.5-flash`.
**Quota gratis (al 2026):** 1,500 requests/día, 15 req/min en plan free.

### ¿Cuál elegir?

| Criterio | Groq | Gemini |
|----------|------|--------|
| Velocidad respuesta | ⚡ <1s | 2-4s |
| Quota diaria gratis | ~14,400 | 1,500 |
| Calidad explicaciones técnicas | Excelente (Llama 3.3 70B) | Excelente (Gemini 2.5) |
| Setup | Muy simple | Simple |
| Tarjeta crédito requerida | ❌ No | ❌ No (plan free) |

**Recomendación:** empieza con **Groq**. Si la quota no te alcanza, añade Gemini como fallback (SDAI intenta Groq primero, si falla intenta Gemini, si ambas fallan usa heurístico).

### Puedes tener ambas activas

SDAI prioriza en este orden:
1. **Groq** (si `GROQ_API_KEY` presente)
2. **Gemini** (si `GROQ_API_KEY` falla o vacía y `GEMINI_API_KEY` presente)
3. **Heurístico local** (siempre disponible, sin internet)

```env
# Ambas activas → más resiliente
GROQ_API_KEY=gsk_xxxxx
GEMINI_API_KEY=AIzaSy_xxxxx
```

### Verificar que funciona

Una vez configurada la key y reiniciado SDAI:
1. Abre el dashboard.
2. Encuentra una alerta y haz clic en **Explicar con IA** (botón en el panel de alertas).
3. Debe responder con un análisis didáctico ~1-3 segundos.

En la respuesta JSON del endpoint `/ai/explain/{ip}` verás el campo `"mode"`:
- `"groq"` → respondió Groq ✅
- `"gemini"` → respondió Gemini ✅
- `"heuristic"` → ninguna key funcionó, usó respuesta local ⚠️

### Costos reales esperados (PyME promedio)

- **Tutor en uso normal:** ~50-200 explicaciones/día → bien dentro de capa gratis
- **Cargas anormales:** si recibes 500+ alertas/día (DoS sostenido), considera bloquear primero a nivel firewall

**No hay riesgo de "factura sorpresa":** las cuentas free se desactivan al alcanzar el límite, no cobran nada.

### Buenas prácticas

| ✅ Hacer | ❌ No hacer |
|---------|-------------|
| Crear cuenta propia con tu email PyME | Usar la key de otra persona |
| Rotar la key cada 6 meses | Compartir la key por WhatsApp/email |
| Si filtras la key sin querer: revocar en consola de inmediato | Subir `.env` a Git/repositorios públicos |
| Monitorear uso en dashboard de Groq/Gemini | Asumir que la cuota es infinita |
| Activar alertas de quota en Google Cloud | Hardcodear la key en código fuente |

---

## 11. Configurar el archivo .env completo

Resumen de **todas las variables**:

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `SUPABASE_URL` | ✅ | URL del proyecto Supabase |
| `SUPABASE_KEY` | ✅ | `service_role` key de Supabase |
| `API_HOST` | ✅ | `0.0.0.0` para exponer en red, `127.0.0.1` solo local |
| `API_PORT` | ✅ | Puerto del backend (default 8000) |
| `CAPTURE_INTERFACE` | ✅ | Nombre de tu NIC (`eth0`, `Wi-Fi`, `wlan0`...) |
| `CAPTURE_COUNT` | ✅ | `0` = infinito, `N` = parar después de N paquetes |
| `TELEGRAM_BOT_TOKEN` | ❌ | Si vacío, no envía Telegram |
| `TELEGRAM_CHAT_ID` | ❌ | Chat/grupo destino |
| `SMTP_HOST` | ❌ | `smtp.gmail.com` u otro |
| `SMTP_PORT` | ❌ | `587` (TLS) o `465` (SSL) |
| `SMTP_USER` | ❌ | Tu email |
| `SMTP_PASSWORD` | ❌ | App password (16 chars) |
| `SMTP_SENDER` | ❌ | Email "From" |
| `SMTP_USE_TLS` | ❌ | `true` para puerto 587 |
| `EMAIL_RECIPIENTS` | ❌ | Lista separada por coma |
| `GEMINI_API_KEY` | ❌ | Para tutor IA en dashboard (Google Gemini) — **TU propia key gratis** desde https://aistudio.google.com/apikey. NO compartir. Ver sección 10.5. |
| `GROQ_API_KEY` | ❌ | Alternativa más rápida y mejor capa gratis — **TU propia key gratis** desde https://console.groq.com. Sección 10.5. |
| `ADMIN_USERNAME` | ✅ | Usuario login dashboard (default `admin`) |
| `ADMIN_PASSWORD` | ✅ | **CAMBIA SIEMPRE** la default |
| `SESSION_SECRET_KEY` | ✅ | Genera con `secrets.token_urlsafe(48)` |
| `SESSION_COOKIE_SECURE` | ✅ | `true` solo si tienes HTTPS, `false` para HTTP local |
| `CORS_ALLOWED_ORIGINS` | ✅ | `*` (dev) o lista con coma `https://soc.pyme.com,...` |
| `LOG_FORMAT` | ❌ | `json` (producción/Docker) o `console` (dev) |
| `LOG_LEVEL` | ❌ | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## 12. Primer arranque y verificación

### 12.1. Checklist pre-arranque

- [ ] Docker o Python 3.12 instalado
- [ ] `.env` creado y rellenado
- [ ] `SUPABASE_URL` + `SUPABASE_KEY` válidos
- [ ] Schema `db/schema.sql` ejecutado en Supabase
- [ ] `ADMIN_PASSWORD` cambiada de la default
- [ ] `SESSION_SECRET_KEY` generada (no la default)
- [ ] (Opcional) Telegram bot creado
- [ ] (Opcional) Gmail App Password creada

### 12.2. Arrancar

Docker:
```bash
docker compose up -d
docker compose logs -f
```

Código nativo:
```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

### 12.3. Verificar healthcheck

En otra terminal o navegador:
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 12.4. Abrir login

Navegador → http://localhost:8000/login

- Usuario: `admin`
- Contraseña: la que pusiste en `ADMIN_PASSWORD`

Debes llegar al dashboard con globo 3D.

### 12.5. Encender sniffer

En el dashboard, esquina superior derecha → botón **Encender** (icono play).

Si el sniffer no arranca:
- Linux: ¿corriste con `sudo` o como root dentro del contenedor?
- Windows: ¿Npcap instalado en modo WinPcap-compatible?

---

## 13. Uso del dashboard SOC

### 13.1. Vista general

| Zona | Qué muestra |
|------|-------------|
| **Topbar** | Búsqueda global (Ctrl+F) · Toggle dark mode · Perfil · Encender/Apagar sniffer |
| **KPIs** | Total paquetes · Alertas activas · PPS actual · Uptime |
| **Globo 3D** | Mapa mundial con arcos animados attacker → tu sensor |
| **Threat Distribution** | Donut con tipos de amenaza detectados |
| **Top Sources** | IPs más activas |
| **Trend** | Series temporales por severidad |
| **Live Packet Table** | Paquetes en vivo vía SSE |
| **Alertas** | Lista de alertas + botón resolver |

### 13.2. Investigar una IP

Clic en cualquier IP de la lista o tabla → **Modal de investigación**:
- Geo (país, ciudad, lat/lon)
- Total eventos + alertas
- Puertos más visitados
- Protocolos usados
- Si está en blacklist

### 13.3. Configurar umbrales en vivo

Engranaje → **Ajustes**:
- `port_scan_threshold` (puertos distintos)
- `brute_force_threshold` (intentos)
- `dos_threshold` (paquetes/seg)
- `blacklist_ips` (CSV de IPs)

Cambios se aplican en **≤10 segundos** sin reiniciar (hot-reload).

### 13.4. Exportar reportes

- **Exportar eventos CSV** — para auditoría
- **Exportar alertas CSV** — para reporte a gerencia

### 13.5. Reiniciar sensor

Engranaje → **Reset sensor** → vacía ventanas deslizantes + cooldowns en memoria (no borra DB).

### 13.6. Tutor IA (opcional)

Si configuraste `GEMINI_API_KEY` o `GROQ_API_KEY`, aparece un panel "Asistente IA" que explica las alertas en lenguaje simple para no-técnicos.

---

## 14. Operación diaria

### 14.1. Rutina recomendada

| Cuándo | Tarea |
|--------|-------|
| Cada mañana | Abrir dashboard, revisar alertas de la noche, marcar resueltas |
| Semanal | Exportar CSV de alertas → archivar para auditoría |
| Mensual | Revisar `blacklist_ips`, sumar IPs nuevas observadas en feeds de threat intelligence |
| Trimestral | Tunear thresholds según falsos positivos |
| Cuando llegue Telegram | Responder en ≤15 min si severidad alta |

### 14.2. Mantener actualizado

Docker:
```bash
docker compose pull
docker compose up -d
```

Código:
```bash
git pull origin main
pip install -r requirements.txt   # por si hay deps nuevas
# reinicia uvicorn
```

### 14.3. Logs

```bash
# Docker
docker compose logs -f sdai-sensor

# Nativo: uvicorn imprime a stdout
# Para guardar a archivo:
uvicorn app.main:app --app-dir backend --host 0.0.0.0 > sdai.log 2>&1
```

### 14.4. Backup de la base

Supabase hace backups automáticos en plan free. Para backup manual:
- Supabase → **Database** → **Backups** → Download.

---

## 15. Pruebas — simular ataques

Para verificar que las detecciones funcionan sin esperar tráfico real:

```bash
# Linux/macOS (con venv activo)
python scripts/simulate_attacks.py

# Windows
.\.venv\Scripts\python.exe scripts\simulate_attacks.py
```

Opciones:
```bash
python scripts/simulate_attacks.py --only port_scan
python scripts/simulate_attacks.py --only brute_force
python scripts/simulate_attacks.py --only dos
python scripts/simulate_attacks.py --only malicious_ip
python scripts/simulate_attacks.py --only baseline   # tráfico normal
python scripts/simulate_attacks.py --rate 50 --host http://127.0.0.1:8000
```

Verás aparecer alertas en el dashboard, en Telegram y email (si están configurados).

**Prueba de carga (10k pkt/min — Sprint 7-8):**
```bash
python scripts/load_test.py --rate 167 --duration 60 --concurrency 50
```

Debe terminar con `VEREDICTO: ✅ PASS`.

---

## 16. Resolución de problemas

### 16.1. "Connection refused" al abrir el dashboard

**Causa:** Backend no está corriendo o `API_HOST=127.0.0.1` y accedes desde otra máquina.

**Fix:**
```bash
# Verifica que el proceso está vivo
docker compose ps                    # Docker
ps aux | grep uvicorn                # Linux nativo

# Cambia .env: API_HOST=0.0.0.0
# Si usas Docker host networking, ya está bien
```

### 16.2. "Permission denied" al sniffear (Linux nativo)

**Causa:** Scapy necesita CAP_NET_RAW.

**Fix:**
```bash
# Opción A: correr con sudo
sudo .venv/bin/python -m capture.sniffer -i eth0

# Opción B: dar capacidades al binario Python (peligroso, solo dev)
sudo setcap cap_net_raw,cap_net_admin=eip $(readlink -f .venv/bin/python)
```

### 16.3. Sniffer en Windows no captura nada

**Causa:** Npcap no instalado o instalado sin "WinPcap API-compatible Mode".

**Fix:** Reinstala Npcap marcando la opción.

### 16.4. Telegram no envía mensaje

**Diagnóstico:**
```bash
# Reemplaza TOKEN y CHAT_ID
curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=test"
```

Errores comunes:
- `chat not found` → no enviaste `/start` al bot, o el grupo no tiene al bot como admin.
- `Unauthorized` → token mal copiado.

### 16.5. Gmail rechaza login

- ¿Tienes verificación en dos pasos activa?
- ¿Usaste la App Password de 16 chars, no tu contraseña normal?
- ¿Quitaste los espacios de la App Password?
- ¿Puerto 587 con `SMTP_USE_TLS=true`?

### 16.6. "relation events does not exist"

Schema no cargado en Supabase. Vuelve a [sección 8.3](#83-cargar-schema).

### 16.7. Docker dice "port 8000 is already allocated"

```bash
# Linux/macOS
sudo lsof -ti:8000 | xargs -r sudo kill -9

# Windows PowerShell (admin)
Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess | Stop-Process -Force
```

### 16.8. El globo 3D no carga (pantalla negra)

Es por bloqueo del CDN (Globe.gl + Three.js). Si tu red filtra `unpkg.com` / `cdn.jsdelivr.net`, descárgalos local o usa otra red.

### 16.9. Las alertas no aparecen aunque hay tráfico

- ¿El sniffer está ENCENDIDO (botón en dashboard)?
- ¿Hay paquetes contando en KPI "Paquetes" / "PPS actual"?
- Si hay paquetes pero no alertas: thresholds están altos. Baja con simulator: `--rate 100`.

---

## 17. Seguridad — buenas prácticas

| Recomendación | Por qué |
|---------------|---------|
| Cambia `ADMIN_PASSWORD` antes de exponer el dashboard | La default es pública (`admin123`) |
| Genera `SESSION_SECRET_KEY` aleatoria fuerte | Si no, atacantes pueden forjar sesiones |
| Pon `CORS_ALLOWED_ORIGINS` específico en producción | `*` permite que cualquier sitio web invoque tu API |
| Sirve el dashboard sobre HTTPS (nginx reverse proxy) + `SESSION_COOKIE_SECURE=true` | Cookie va en claro en HTTP |
| No subas `.env` a Git | Ya está en `.gitignore`, no lo cambies |
| Restringe el puerto 8000 al LAN, no abras al internet | Es API administrativa |
| Usa `service_role` key SOLO en backend | `anon` key es para frontend, `service_role` salta RLS |
| Backups semanales de Supabase | Para no perder histórico de alertas |
| Audita `EMAIL_RECIPIENTS` cuando rote personal | Ex-empleados no deben seguir recibiendo alertas |
| Cambia GeoLite2 mensualmente | MaxMind actualiza la DB |

---

## 18. FAQ

**¿Funciona sin internet?**
Parcialmente. El backend y sniffer corren sin internet, pero pierdes: Supabase (DB), GeoIP enrichment, Telegram, Gmail, Globe.gl CDN. Para uso 100% offline necesitas una instancia local de Postgres + tile servers propios — fuera del MVP.

**¿Qué pasa con el tráfico cifrado (HTTPS)?**
SDAI analiza **metadatos** (IP origen, IP destino, puerto, protocolo, longitud), no el contenido. Detecta amenazas basadas en patrón de tráfico, no payload. Por eso funciona contra TLS sin necesidad de descifrado.

**¿Cuántos paquetes por segundo soporta?**
Probado a 167 pkt/s (10,000/min) sostenido en hardware modesto con batch INSERT. Para volumen mayor: aumentar `batch_size` en `EventBatchWriter` o usar plan Supabase pago.

**¿Puedo monitorear más de una red?**
Sí: levanta un contenedor SDAI por sensor. Apuntan al mismo Supabase. El dashboard suma alertas de todos.

**¿Puedo ponerlo en una Raspberry Pi?**
Sí. Imagen Docker es multi-arch (incluye ARM64). Pi 4 maneja redes PyME sin problema.

**¿El sistema bloquea ataques?**
No, solo **detecta y alerta**. SDAI es IDS, no IPS. Para bloqueo añade reglas iptables/firewall basadas en las alertas (fuera del MVP).

**¿Cuál es la diferencia con Wireshark?**
Wireshark es inspector manual: tú miras paquetes uno por uno. SDAI es vigilante automatizado: detecta patrones de ataque en background, te avisa, mantiene histórico, genera reportes.

**¿Puedo integrarlo con SIEM (Splunk, ELK)?**
Sí, vía `GET /alerts` (JSON) o `GET /alerts/export` (CSV). Polling o webhook custom.

**¿Cuántas alertas falsas tendré?**
Depende de tu red. Tras 1 semana ajustando thresholds, esperable ≤5% FP. El cooldown 30s y el detector brute_force discriminando TCP SYN ya bajan ruido típico.

**¿Cómo borro datos antiguos de Supabase?**
SQL Editor:
```sql
DELETE FROM events WHERE timestamp < NOW() - INTERVAL '30 days';
DELETE FROM alerts WHERE created_at < NOW() - INTERVAL '90 days';
```

**¿Existe app móvil?**
No nativa. El dashboard es responsive, funciona en navegador móvil. Las alertas Telegram llegan al celular.

**¿Equipo del proyecto?**
Isaac Silva, Carlos Herrera, Ángel Ramos. PyMEs Estado Barinas, Venezuela.

---

## Soporte y contribuciones

- **Bugs / preguntas:** abrir issue en https://github.com/silvaisaac148/SDAI/issues
- **Contribuir:** ver `CONTRIBUTING.md`
- **Licencia:** MIT (`LICENSE`)
- **Arquitectura técnica:** `ARCHITECTURE.md`
- **API reference:** `API_REFERENCE.md`
- **Bitácora sprints:** `PROGRESO.md`
