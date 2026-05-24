# 🛡️ Proyecto SDAI — Informe Técnico Académico
> **Sistema de Detección y Alertas de Intrusiones para PyMEs**  
> **Integrantes:** Isaac Silva · Carlos Herrera · Ángel Ramos  
> **Universidad/Institución:** Estado Barinas, Venezuela  
> **Stack Tecnológico:** Python 3.12 · Scapy 2.6 · FastAPI 0.115 · Supabase (PostgreSQL) · Tailwind CSS + Globe.gl (Three.js 3D)

---

## 1. Introducción y Propósito del Sistema

El **Sistema de Detección y Alertas de Intrusiones (SDAI)** es una solución de ciberseguridad defensiva diseñada específicamente para Pequeñas y Medianas Empresas (PyMEs) en el Estado Barinas que carecen de presupuestos para soluciones propietarias de gran escala (SIEM/IDS comerciales) y de personal de TI especializado en seguridad informática.

### 🔴 Problemas Clave que Soluciona
1. **Monitoreo Inexistente en PyMEs:** La mayoría de las pequeñas empresas no inspeccionan su tráfico de red, lo que permite que intrusiones pasen desapercibidas por meses.
2. **Complejidad de Herramientas Tradicionales:** Soluciones como Snort o Suricata requieren una empinada curva de aprendizaje y configuración de firmas mediante consola de comandos. SDAI centraliza todo en un panel visual e intuitivo en 3D.
3. **Notificación en Tiempo Real:** El software no se limita a guardar logs pasivos; alerta activamente a los administradores mediante canales de mensajería cotidianos (Telegram y Correo Electrónico) en el instante exacto del incidente.
4. **Falta de Contexto Geográfico de las Amenazas:** Tradicionalmente, identificar el origen geográfico de una IP sospechosa requiere análisis externos. SDAI integra una base de datos local MaxMind GeoLite2 para geodecorar y mapear los ataques en tiempo real.

---

## 2. Arquitectura de Software y Pipeline de Datos

El sistema se estructura en capas desacopladas, lo que garantiza modularidad y resiliencia:

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
```

---

## 3. Detalle de Módulos y Funcionalidades

### A. Capa de Captura y Decodificación (`capture/`)

* **Decodificador de Paquetes (`decoder.py`):**
  * *Cómo funciona:* Recibe el paquete crudo de Scapy y, mediante condicionales rápidos en capas IP, TCP, UDP e ICMP, extrae de forma segura direcciones IP, puertos de origen/destino, banderas de control (TCP flags), tamaño de paquete y marca de tiempo.
  * *Propósito:* Estandariza la información de bajo nivel de red a un formato de diccionario simple (JSON-compatible) para facilitar su transmisión HTTP.

* **Geolocalización Local (`geoip_resolver.py`):**
  * *Cómo funciona:* Identifica si una IP es de rango privado (RFC 1918). Si es privada, la etiqueta como `"Red Local"`. Si es pública, consulta localmente la base de datos `GeoLite2-City.mmdb` para extraer país, ciudad, latitud y longitud. 
  * *Mock de Fallback:* Si la base de datos mmdb no está disponible, calcula de forma determinista un hash MD5 de la IP para asignarle coordenadas consistentes, garantizando que el sistema sea inmune a caídas de servicio.

* **Gestor de Estado del Sensor (`state.py` / `DetectionStateManager`):**
  * *Cómo funciona:* Mantiene las ventanas deslizantes de tráfico en memoria para alimentar los detectores.
  * *Hot-Reloading:* Cada 10 segundos, consulta a Supabase la tabla de configuraciones para actualizar los límites (umbrales de alerta) en caliente, sin necesidad de apagar el sensor.
  * *Cooldown (Anti-Spam):* Bloquea alertas repetitivas de un mismo origen y amenaza durante 30 segundos, protegiendo las cuotas de mensajes en Telegram y correos.

---

### B. Motor de Detección de Amenazas (`capture/detectors/`)

El sistema evalúa cada paquete capturado a través de cuatro filtros heurísticos independientes:

| Detector | Mapeo de Archivo | Lógica de Detección | Severidad |
| :--- | :--- | :--- | :--- |
| **Escaneo de Puertos** | `port_scan.py` | Monitorea si una IP origen contacta a $N$ puertos diferentes de destino en una ventana de 60 segundos. | **Media** (≥20 puertos) / **Alta** (>30 puertos) |
| **Fuerza Bruta** | `brute_force.py` | Detecta ráfagas de paquetes TCP `SYN` dirigidos a puertos críticos de autenticación (`21: FTP`, `22: SSH`, `23: Telnet`, `3389: RDP`) en una ventana de 60s. Evita falsos positivos en protocolos sin conexión (UDP). | **Media** (≥5 intentos) / **Alta** (>15 intentos) |
| **Denegación de Servicio (DoS)** | `dos.py` | Evalúa si los paquetes provenientes de una misma IP exceden un umbral masivo de PPS (paquetes por segundo) en un intervalo estricto de 1.0 segundo. | **Alta** |
| **IP Maliciosa** | `malicious_ip.py` | Compara las IPs de entrada y salida contra una lista negra de reputación alojada y editable desde Supabase PostgreSQL. | **Alta** |

---

### C. Capa de API y Orquestación Controlada (`backend/app/`)

* **FastAPI Web Server (`main.py`):** Expone endpoints RESTful documentados automáticamente bajo el estándar OpenAPI (Swagger UI).
* **Controlador de Captura Remota (`capture_controller.py`):**
  * Encapsula un objeto `AsyncSniffer` de Scapy, permitiendo encender, apagar, pausar o reanudar el sniffer de la tarjeta de red mediante simples llamadas HTTP (`POST /capture/start`, `/capture/stop`, etc.).
* **Server-Sent Events (`routers/live.py`):**
  * Implementa una cola de eventos asíncronos (`asyncio.Queue`) que mantiene una conexión persistente bidireccional (SSE) en `/live/stream`, empujando cada paquete decodificado y alerta de forma inmediata al navegador.
* **Módulo de Investigación Avanzada (`routers/events.py`):**
  * El endpoint `/events/investigate/{src_ip}` agrupa de forma inteligente todo el expediente de seguridad de una dirección IP (historial de eventos, conteo de alertas, distribución de puertos atacados y geolocalización) para facilitar el análisis forense.

---

### D. Sistema de Notificaciones Asíncronas Multihilo (`notifications/`)

* **Despachador Inteligente (`dispatcher.py`):**
  * *Funcionamiento:* Para evitar bloquear el pipeline de detección de paquetes (el envío de correos SMTP y llamadas HTTPS a la API de Telegram demora entre 0.5s a 3s), el despachador encapsula cada envío dentro de un hilo demonio secundario (`threading.Thread`).
  * *Enrutamiento por Severidad:*
    * **Alta:** Se notifica simultáneamente por Telegram (Markdown estructurado) y por Correo SMTP (TLS seguro).
    * **Media:** Se despacha exclusivamente por canal de Telegram.
    * **Baja:** Únicamente se persiste el registro histórico en Supabase.

---

### E. Base de Datos en la Nube (`db/schema.sql`)

El motor de datos se hospeda en un PostgreSQL de Supabase en la nube con 3 tablas clave optimizadas mediante índices:
1. `events`: Guarda la traza del paquete con estructura optimizada para tipos de datos de red (`INET`) y un dump JSON del payload.
2. `alerts`: Registra las alertas generadas por el motor con sus campos geográficos de latitud/longitud y ciudad.
3. `configurations`: Guarda los umbrales configurables por el administrador del sistema en caliente.

---

### F. Dashboard SOC Premium en 3D (`SDAI/SDAI Dashboard.html`)

* **Tecnología Visual:** Construido usando Vanilla HTML, Tailwind CSS para el estilado, y **Globe.gl / Three.js** para renderizar un impresionante globo terráqueo tridimensional interactivo con texturas de relieve terrestre de alta fidelidad.
* **Interactividad Dinámica:**
  * **Arcos de Ataque:** Al recibir una alerta vía SSE, traza en vivo un arco luminoso y animado desde la ubicación IP del atacante hacia la ubicación del sensor, con anillos pulsantes (hotspots) sobre las coordenadas geográficas.
  * **Drawer de Inspección:** Permite desglosar un paquete al darle clic, exponiendo su visualización por capas, volcado hexadecimal y datos crudos estructurados en JSON.
  * **Modo Demostración Offline:** Si detecta que no hay conexión con el backend de FastAPI, activa de forma automática una simulación interna con datos ficticios realistas para poder presentarlo ante una audiencia sin necesidad de encender el servidor.

---

## 4. Garantía de Calidad y Pruebas Unitarias

El software está respaldado por **58 pruebas automatizadas** desarrolladas bajo la librería `pytest` que verifican la integridad lógica antes de realizar liberaciones del código:
* **Pruebas de Decodificación:** Validan que el conversor asocie correctamente las banderas TCP y puertos.
* **Pruebas de Motor de Detección:** Simulan patrones de ataque controlados (DoS, escaneos de red, fuerza bruta) para constatar que el motor dispare las alertas bajo los umbrales correctos.
* **Pruebas de Despacho:** Aseguran que el despachador asíncrono no lance excepciones y maneje correctamente las prioridades por severidad.
