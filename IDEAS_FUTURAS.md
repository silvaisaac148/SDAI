# Ideas y Roadmap Extendido — SDAI

> Ideas discutidas durante el desarrollo del proyecto. No son compromisos del MVP, sino features candidatas para sprints avanzados o para post-entrega académica.

---

## 1. Simulaciones de ataque para validación

### 1.1 Misma Wi-Fi (sprint 3-4, demo principal)
- Teléfono y laptop en mismo router doméstico
- Teléfono ve laptop en `192.168.1.x` directamente
- App **Termux** (Android, gratis F-Droid o Play Store)
- Instalar herramientas:
  ```bash
  pkg update && pkg install nmap hping3 hydra
  ```
- Comandos para disparar cada detector:
  - **Port scan** → `nmap -sS 192.168.1.5 -p 1-1000`
  - **DoS / flood** → `hping3 -S --flood 192.168.1.5 -p 80`
  - **Brute force SSH** → `hydra -l admin -P passwords.txt ssh://192.168.1.5`
- Ventaja: no requiere exponer red a internet, ideal demostración aula

### 1.2 Hotspot 4G distinto (sprint 7-8, demo extendida)
- Teléfono usa datos móviles (otra IP pública, otra red)
- Reto técnico: laptop detrás NAT del router → no alcanzable directo
- Soluciones:
  - **ngrok TCP tunnel** — `ngrok tcp 22` expone puerto SSH a `tcp://X.ngrok.io:Y`
  - **Port forward router** — config panel router (ej. `192.168.1.1`) abrir puerto externo → IP interna
  - **Cloudflare Tunnel** — gratis, similar ngrok
- ⚠ Una vez expuesto a internet, bots Shodan/Censys escanean automáticamente — útil para datos reales pero **cerrar después de demo**

### 1.3 VPS cloud como objetivo (post-MVP)
- Deploy SDAI en VPS DigitalOcean/AWS Lightsail (~$4/mes o free tier)
- Atacas IP pública del VPS desde teléfono o cualquier red
- Más realista (entorno producción), gasta tiempo deploy + costo
- Considerar para defensa académica con énfasis "producto comercial viable"

---

## 2. Visualización en vivo (estilo Wireshark)

### 2.1 Dashboard live SSE (Sprint 3-4 prioridad)
- Backend: endpoint FastAPI `GET /live/stream` mantiene conexión abierta, push paquetes como Server-Sent Events
- Frontend: `new EventSource('/live/stream')` recibe en tiempo real
- Tabla auto-scroll últimos 100 paquetes
- Color por severidad: verde normal, amarillo medio, rojo alta
- Click fila → modal con detalle completo + raw_data JSON
- Filtros vivos: solo TCP, solo IP X, solo amenazas
- Stats laterales: pkt/seg actual, top 5 IPs, distribución protocolos

### 2.2 Alternativa WebSocket
- Bidireccional (cliente puede enviar comandos: pausar, filtrar, exportar)
- Más complejo que SSE
- Considerar si dashboard necesita interactividad avanzada

### 2.3 Descripciones educativas en alertas
Cada alert guardará campo `description` interpretativo:
```json
{
  "threat_type": "port_scan",
  "severity": "alta",
  "description": "Host 1.2.3.4 escaneó 25 puertos distintos en 47s. Patrón típico nmap SYN scan. Probable reconocimiento previo a ataque.",
  "evidence": {
    "ports_scanned": [22, 23, 80, 443, 3389, ...],
    "duration_seconds": 47,
    "first_seen": "...",
    "last_seen": "..."
  }
}
```
Usuario aprende qué pasó + por qué es amenaza.

---

## 3. GeoIP (Sprint 5-6, alta prioridad)

### Opciones gratuitas comparadas

| Servicio | Gratis | Límite | Notas |
|----------|--------|--------|-------|
| **MaxMind GeoLite2** ⭐ | Sí | DB local, sin límite | Mejor opción, signup + descarga `.mmdb` mensual |
| ip-api.com | Sí | 45 req/min | Sin signup, HTTP GET |
| ipinfo.io | Sí | 50k req/mes | Token registro, incluye ASN/org |
| ipapi.co | Sí | 1k req/día | Sin signup |

### Setup MaxMind recomendado
```bash
pip install geoip2
# Signup en maxmind.com → descarga GeoLite2-City.mmdb
```
```python
import geoip2.database
reader = geoip2.database.Reader('GeoLite2-City.mmdb')
r = reader.city('89.38.97.196')
print(r.country.name, r.city.name, r.location.latitude, r.location.longitude)
# 'Romania', 'Bucharest', 44.43, 26.10
```

### Visualización: mapa mundi
- Lib **Leaflet.js** (gratis, OpenStreetMap)
- Puntos rojos donde origen ataques
- Tamaño punto proporcional severidad
- Click marker → ver alertas de esa ubicación
- Muy vistoso defensa académica

---

## 4. Reputación IP automática

- Integración **AbuseIPDB API** (gratis 1k checks/día)
- Cada src_ip nueva → query AbuseIPDB → si reportada > N veces → auto-añadir a `configurations.blacklist_ips`
- Cron job diario refresca scores
- Alternativas: **AlienVault OTX**, **GreyNoise**, **Shodan**

---

## 5. Histórico exportable

- Endpoint `GET /events/export?format=csv` → descarga CSV
- Endpoint `GET /events/export?format=pcap` → archivo Wireshark-compatible (lib `scapy.utils.wrpcap`)
- Útil para análisis forense post-incidente

---

## 6. Reglas Snort/Suricata

- Parser que importa reglas estándar industria (formato `.rules`)
- Detección por firmas conocidas además del análisis comportamental
- Comunidad enorme reglas pre-hechas (Emerging Threats gratis)

---

## 7. ML detección anomalías

- Modelo **Isolation Forest** o **Autoencoder** sklearn
- Aprende baseline tu red durante 1-2 semanas (qué es "normal")
- Alerta desviaciones estadísticas (más allá reglas fijas)
- Útil contra ataques zero-day no cubiertos por firmas
- Lib: `scikit-learn`, sin GPU necesaria

---

## 8. Integración firewall (auto-respuesta)

- Alerta crítica → script auto-bloquea IP atacante
- Windows: `netsh advfirewall firewall add rule name="block_X" dir=in action=block remoteip=X`
- Linux: `iptables -A INPUT -s X -j DROP`
- ⚠ Cuidado falsos positivos → bloquear admin propio. Implementar whitelist.
- Modo "sugerencia" en dashboard antes de auto-acción

---

## 9. Mejoras backend / arquitectura

### 9.1 Async/queue Sprint 7-8
- Sniff Scapy en thread separado (no bloquea API)
- Queue intermedia (`asyncio.Queue` o Redis)
- Worker batch INSERT cada 100 eventos (reduce IO Supabase)

### 9.2 Auth real
- JWT con expiración + refresh tokens
- Roles: admin (CRUD configs), viewer (solo lectura)
- Pydantic dependencies en endpoints

### 9.3 Rate limiting API
- Lib `slowapi` (FastAPI compatible)
- Proteger endpoints contra abuso

### 9.4 Logging estructurado
- Lib `structlog` o `loguru`
- JSON logs → fácil parsing en herramientas (ELK, Grafana Loki)

---

## 10. Distribución / despliegue

- **Docker Compose** — un comando levanta todo (backend + frontend)
- **Instalador Windows** PyInstaller `.exe` (PyME no técnica)
- **Raspberry Pi** edition — SDAI corre 24/7 en RPi conectada al switch (consumo bajo, ~$50 hardware)
- **Modo cloud SaaS** — múltiples PyMEs gestionadas desde panel central (futuro comercial)

---

## 11. Otros ataques a detectar (extensión Sprint 3-4 o post-MVP)

- **DNS tunneling** — exfiltración datos vía consultas DNS anómalas
- **ARP spoofing / MITM** — atacante intercepta tráfico LAN
- **DHCP starvation** — agota pool de IPs del router
- **Beaconing C2** — malware llama "casa" a intervalos regulares (patrón temporal)
- **SQL injection en URLs** — patrones en queries HTTP capturadas (requiere DPI)

---

## 12. Documentación / educativo

- **Wiki interna proyecto** — explicación cada amenaza con ejemplos reales
- **Modo tutorial dashboard** — al detectar primera amenaza tipo X, mostrar popup explicativo "Esto es port scan, así funciona, así te proteges"
- **Reportes PDF semanales** — auto-genera resumen ejecutivo para gerencia PyME (no técnica)

---

## Prioridad sugerida orden de implementación post Sprint 1-2

1. ⭐ Sprint 3-4 plan original — motor detección 4 amenazas + dashboard básico
2. ⭐ Dashboard live SSE (estilo Wireshark) — alta valor demo
3. ⭐ Sprint 5-6 plan original — Telegram + Email + Chart.js
4. GeoIP + mapa Leaflet
5. Simulación Termux misma Wi-Fi (validación funcional)
6. Reputación AbuseIPDB
7. Sprint 7-8 plan original — async, optimización, hardening
8. Histórico exportable PCAP
9. Sprint 9 plan original — docs + video demo
10. Post-MVP: ML, firewall auto, Docker, Raspberry Pi edition
