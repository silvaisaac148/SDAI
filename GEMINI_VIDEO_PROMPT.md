# SDAI — Prompt Gemini Veo para Video Demo (5-7 min)

> Prompts diseñados para **Google Gemini Veo / Veo 3** (modelo video). Genera escenas de 8s cada una; se ensamblan en post-producción a un video continuo de 5-7 min.

**Importante:** Veo genera clips de hasta 8 segundos. Para un video largo se generan ~40-50 clips, se editan en CapCut / DaVinci Resolve / Premiere y se añade voiceover.

---

## Estructura del video (6:00 min total)

| Sección | Duración | Escenas Veo | Voiceover |
|---------|----------|-------------|-----------|
| 1. Hook + problema | 0:00–0:45 | 5-6 clips de 8s | Sí |
| 2. Presentación SDAI | 0:45–1:30 | 5 clips | Sí |
| 3. Arquitectura visual | 1:30–2:15 | 5 clips animados | Sí |
| 4. Demo dashboard | 2:15–4:30 | 12-15 clips | Sí |
| 5. Resultados | 4:30–5:15 | 5 clips | Sí |
| 6. Cierre + CTA | 5:15–6:00 | 5 clips | Sí |

---

## PROMPT MAESTRO (sistema)

Pega esto **al inicio** de cualquier sesión Veo para mantener consistencia visual:

```
STYLE GUIDE FOR ALL SCENES:
- Cinematic, dark-mode aesthetic with cyan and teal accent lights
- 1080p resolution, 24fps, anamorphic lens look
- Color palette: deep blue (#0a1929), cyan (#00bfff), dark teal (#0f4c5c), white (#ffffff)
- Lighting: soft rim light from cyan monitors, atmospheric haze
- Typography overlays use modern sans-serif (Inter / IBM Plex Sans) in white or cyan
- Aesthetic: blend of cybersecurity SOC operations center + tech startup product video
- Camera: smooth dolly movements, no jump cuts, subtle parallax
- Avoid: stock-footage clichés, dramatic zooms, lens flares, anime style, cartoon style
- Mood: confident, professional, slightly mysterious, never scary
```

---

## SECCIÓN 1 — Hook + Problema (0:00–0:45)

### Scene 1.1 (0:00–0:08)
```
A wide aerial cinematic shot at dusk over a small Latin American town with terracotta rooftops and palm trees (Barinas, Venezuela). Slow drone descent towards a modest two-story commercial building with a small "PyME" storefront sign visible. Warm sunset lighting. 24fps, anamorphic, cinematic color grading.
```

### Scene 1.2 (0:08–0:16)
```
Interior of a small business office at night, viewed through the window from outside. A single laptop screen glows in the dark, unattended. Power cables run across the floor. Atmospheric, slightly ominous mood. Soft rim lighting in cyan from the screen. No people visible. 24fps, anamorphic.
```

### Scene 1.3 (0:16–0:24)
```
Macro close-up of a router LED panel blinking rapidly with intense activity, much faster than normal. Red and green lights flashing erratically. Shallow depth of field. Cinematic, dramatic but not scary. 24fps.
```

### Scene 1.4 (0:24–0:32)
```
Animated text overlay on a dark blue background: large bold white text reads "El 60% de las PyMEs que sufren un ciberataque cierran en 6 meses". Text fades in word by word with subtle particle effects. Sober, documentary style. Cyan underline grows under the "60%". 24fps.
```

### Scene 1.5 (0:32–0:40)
```
Split-screen comparison: left side shows a sleek enterprise SOC with multiple monitors and analysts (price tag "$50,000/year" overlay in red). Right side shows an empty small business office with just one router (price tag "$0/year" overlay in red, with sad face icon). Clear contrast. 24fps, cinematic.
```

### Scene 1.6 (0:40–0:45)
```
Text card on black background: cyan glowing text "¿Y si hubiera una alternativa accesible?" appears with subtle pulse. Minimalist. 5 seconds. 24fps.
```

**Voiceover sección 1:**
> "En el Estado Barinas, miles de pequeñas y medianas empresas operan sin ninguna protección contra ciberataques. Las soluciones empresariales cuestan decenas de miles de dólares. Las soluciones open-source requieren personal especializado que estas empresas no tienen. El resultado: operan ciegas. Hasta hoy."

---

## SECCIÓN 2 — Presentación SDAI (0:45–1:30)

### Scene 2.1 (0:45–0:53)
```
Logo reveal: large "SDAI" letters in glowing cyan emerge from a dark blue background. Particles converge to form the letters. Subtitle appears below: "Sistema de Detección y Alertas de Intrusiones". Modern tech intro style, no anime, no cheesy effects. 24fps.
```

### Scene 2.2 (0:53–1:01)
```
Aesthetic shot of a Raspberry Pi 4 sitting on a wooden desk next to a small business router, both connected with an ethernet cable. Cyan LED glowing on the Pi. Shallow depth of field, warm ambient light. Photo-realistic, product video style. 24fps.
```

### Scene 2.3 (1:01–1:09)
```
Hand opens a laptop on a desk in a quiet small office. Laptop boots up and screen lights up showing a dark cybersecurity dashboard with a 3D rotating Earth globe in the center, glowing cyan arcs flowing between countries. Cinematic over-the-shoulder shot. 24fps.
```

### Scene 2.4 (1:09–1:17)
```
Close-up of a smartphone on a wooden table. The screen lights up with a Telegram notification: "🚨 ALERTA SDAI — Port Scan detectado desde Alemania". Soft cyan glow from the phone illuminates the table. 24fps, macro lens, cinematic.
```

### Scene 2.5 (1:17–1:25)
```
Animated text on dark background: six benefit cards appear sequentially with icons:
- "Gratis y open-source" (heart icon)
- "Instalación en 10 minutos" (clock icon)
- "Dashboard SOC profesional" (monitor icon)
- "Alertas Telegram + Email" (bell icon)
- "Geolocalización 3D real" (globe icon)
- "Sin curva de aprendizaje" (graduation cap icon)
Each card appears with subtle slide-up animation in cyan border style. 24fps.
```

### Scene 2.6 (1:25–1:30)
```
Closing tagline appears: "Ciberseguridad accesible. Para todos." in elegant white serif typography on dark background. Subtle cyan particles drift across. 5 seconds. 24fps.
```

**Voiceover sección 2:**
> "Presentamos SDAI. Un sistema de detección de intrusiones diseñado desde cero pensando en quienes no son expertos en ciberseguridad. Gratis, código abierto, y desplegable en menos de diez minutos. Funciona en una laptop, un Raspberry Pi, o cualquier servidor Linux."

---

## SECCIÓN 3 — Arquitectura (1:30–2:15)

### Scene 3.1 (1:30–1:38)
```
Animated diagram on dark blue background: a network packet visualized as a glowing cyan cube enters from the left side, representing a NIC card with rotating Wi-Fi waves. The cube travels along an animated path. Minimalist, technical infographic style. Smooth motion graphics. 24fps.
```

### Scene 3.2 (1:38–1:46)
```
Continuation of the animated diagram: the glowing cube passes through a stylized funnel labeled "Scapy Decoder" which transforms it into a structured JSON object. The JSON keys (src_ip, dst_ip, protocol, port) appear in cyan monospace text. Tech motion graphics style. 24fps.
```

### Scene 3.3 (1:46–1:54)
```
Animated diagram: four detector boxes labeled "Port Scan", "Brute Force", "DoS", "Malicious IP" appear in a row, each pulsing with cyan light. The JSON object from previous scene flows through all four detectors. One box (Port Scan) suddenly flashes red and emits a glowing alert icon. Motion graphics. 24fps.
```

### Scene 3.4 (1:54–2:02)
```
Animated diagram: the red alert icon travels along three glowing paths simultaneously to three destinations: a database icon (labeled "Supabase"), a phone icon (labeled "Telegram"), and an envelope icon (labeled "Email"). Triple branching animation. Tech infographic. 24fps.
```

### Scene 3.5 (2:02–2:15)
```
Wide shot of a transparent 3D representation of the SDAI system: a holographic stack of layers labeled bottom to top: "Sniffer", "API", "Detectors", "Database", "Dashboard". Each layer rotates slowly. Glowing cyan edges. Sci-fi tech aesthetic without being campy. 24fps, slow camera orbit.
```

**Voiceover sección 3:**
> "El sistema funciona en cinco capas. Captura paquetes con Scapy. Los analiza con cuatro detectores en memoria. Persiste en una base de datos en la nube. Notifica por Telegram y email. Y todo se visualiza en un dashboard estilo centro de operaciones de seguridad."

---

## SECCIÓN 4 — Demo Dashboard (2:15–4:30)

> Para esta sección, **MEZCLA Veo + screen recordings reales**. Veo da el envoltorio cinematográfico; las capturas reales muestran el producto.

### Scene 4.1 (2:15–2:23) — Veo
```
Cinematic over-the-shoulder shot of a young Latin American IT professional (woman or man, 25-30 years old) sitting in a modest office, typing on a laptop. The laptop screen is visible at an angle. Soft warm window light + cyan glow from screen. 24fps, shallow DOF.
```

### Scene 4.2 (2:23–2:31) — SCREEN RECORDING REAL
> Captura real: login page → enter credenciales → dashboard carga
**Voiceover:** "Iniciamos sesión con nuestro usuario administrador..."

### Scene 4.3 (2:31–2:39) — SCREEN RECORDING REAL
> Captura real: dashboard completo cargado, globo girando, KPIs visibles
**Voiceover:** "Esto es el dashboard SOC. Globo 3D mostrando actividad global. KPIs en tiempo real. Lista de paquetes en vivo. Y panel de alertas."

### Scene 4.4 (2:39–2:47) — Veo
```
Macro close-up of a finger hovering over a laptop trackpad, about to click. Soft cyan reflection on the fingertip. Shallow DOF. Anticipation mood. 24fps.
```

### Scene 4.5 (2:47–2:55) — SCREEN RECORDING REAL
> Captura real: encender botón sniffer en topbar, badge cambia a "RUNNING"
**Voiceover:** "Encendemos el sniffer con un solo clic."

### Scene 4.6 (2:55–3:03) — Veo
```
Split screen: left half shows a hand typing in a terminal, right half shows a dashboard. The terminal command "python scripts/simulate_attacks.py" is visible. Cyan terminal text on black background. Cinematic. 24fps.
```

### Scene 4.7 (3:03–3:11) — SCREEN RECORDING REAL
> Captura real: terminal corriendo simulate_attacks.py + dashboard mostrando packets count subiendo en KPI
**Voiceover:** "Para demostrar las detecciones, lanzamos un simulador de ataques. Vamos a inundar el sistema con paquetes sospechosos."

### Scene 4.8 (3:11–3:19) — SCREEN RECORDING REAL
> Captura real: PPS sube, paquetes aparecen en live table, primer arco rojo en globo
**Voiceover:** "Inmediatamente el globo dibuja un arco desde el origen del atacante hasta nuestro sensor."

### Scene 4.9 (3:19–3:27) — SCREEN RECORDING REAL
> Captura real: primera alerta aparece en panel de alertas con badge severidad alta
**Voiceover:** "Y se dispara la primera alerta: Port Scan severidad alta desde Brandenburg, Alemania."

### Scene 4.10 (3:27–3:35) — Veo
```
Close-up of a smartphone screen on a desk receiving a Telegram message in real-time. Notification preview visible: "🚨 ALERTA SDAI Port Scan...". Phone glows cyan. Shallow DOF, cinematic. 24fps.
```

### Scene 4.11 (3:35–3:43) — SCREEN RECORDING REAL
> Captura real: clic en una alerta → modal Investigate IP abre con geo + ports + protocols
**Voiceover:** "Con un clic abrimos el modal de investigación: vemos la ubicación geográfica del atacante, qué puertos tocó, y todo el historial relacionado."

### Scene 4.12 (3:43–3:51) — SCREEN RECORDING REAL
> Captura real: scroll por las múltiples alertas de los 4 tipos
**Voiceover:** "El sistema detecta cuatro tipos de amenazas: escaneos de puertos, fuerza bruta, denegación de servicio, y conexiones desde IPs maliciosas conocidas."

### Scene 4.13 (3:51–3:59) — SCREEN RECORDING REAL
> Captura real: dashboard ajustes — sliders bajando port_scan_threshold
**Voiceover:** "Los umbrales se ajustan en vivo desde el panel de configuración. Sin reiniciar nada."

### Scene 4.14 (3:59–4:07) — SCREEN RECORDING REAL
> Captura real: clic export CSV, archivo descarga
**Voiceover:** "Para auditorías, exportamos reportes en CSV con un clic."

### Scene 4.15 (4:07–4:15) — SCREEN RECORDING REAL
> Captura real: bandeja Gmail recibiendo email de alerta alta
**Voiceover:** "Las alertas de severidad alta también llegan por email, con todo el contexto necesario para responder."

### Scene 4.16 (4:15–4:23) — Veo
```
Aesthetic shot of a Telegram group chat on a phone with three SDAI alert messages stacked, each showing different threat icons. Phone is held by a hand against a blurred office background. Cinematic, shallow DOF. 24fps.
```

### Scene 4.17 (4:23–4:30) — SCREEN RECORDING REAL
> Captura real: clic resolver alerta → desaparece del panel activo
**Voiceover:** "Una vez atendida, marcamos la alerta como resuelta y queda archivada para reportes futuros."

---

## SECCIÓN 5 — Resultados (4:30–5:15)

### Scene 5.1 (4:30–4:38) — Veo
```
Animated infographic: bar chart appearing dynamically. Bars labeled "Throughput: 9,800 pkt/min", "Latencia p95: 180ms", "Tasa error: 0%". Bars fill up in cyan color. White text on dark blue background. Tech infographic style. 24fps.
```

### Scene 5.2 (4:38–4:46) — SCREEN RECORDING REAL
> Captura real: terminal corriendo `python scripts/load_test.py` mostrando VEREDICTO ✅ PASS
**Voiceover:** "En pruebas de carga, el sistema sostiene 10 mil paquetes por minuto con latencia bajo 200 milisegundos y cero pérdidas."

### Scene 5.3 (4:46–4:54) — Veo
```
Clean text card: "115/115 tests pass" in large cyan numbers on dark background. Subtle checkmark animation. Minimalist documentary style. 24fps.
```

### Scene 5.4 (4:54–5:02) — Veo
```
Animated stacked donut chart appearing: showing detection accuracy percentages for the 4 detector types. All segments in cyan/teal palette. Smooth animation. Tech infographic style on dark background. 24fps.
```

### Scene 5.5 (5:02–5:15) — Veo
```
Wide shot: a Raspberry Pi running SDAI sits next to a small business router on a desk. A laptop nearby shows the SDAI dashboard. The smartphone shows Telegram alerts. All three glowing softly with cyan accents. Pull-back camera reveals the entire setup. Cinematic. 24fps.
```

**Voiceover sección 5:**
> "Resultados validados: sostiene diez mil paquetes por minuto, ciento quince tests automatizados pasando, detección efectiva de las cuatro categorías de amenazas. Todo corriendo en hardware modesto."

---

## SECCIÓN 6 — Cierre + CTA (5:15–6:00)

### Scene 6.1 (5:15–5:23) — Veo
```
Slow aerial shot at dawn over the same Latin American town from Scene 1.1, now with warm sunrise light. The small business buildings are illuminated. Hopeful, optimistic mood. Drone moves smoothly. 24fps, cinematic.
```

### Scene 6.2 (5:23–5:31) — Veo
```
Text card on dark blue background: large white text "SDAI" with subtitle "Sistema de Detección y Alertas de Intrusiones para PyMEs del Estado Barinas". Minimalist, modern typography. 24fps.
```

### Scene 6.3 (5:31–5:39) — Veo
```
Three names appear elegantly on a dark background with subtle cyan particles: "Isaac Silva · Carlos Herrera · Ángel Ramos". Below: "Universidad [nombre]". Documentary credit style. 24fps.
```

### Scene 6.4 (5:39–5:47) — Veo
```
Animated text appears: "docker pull ghcr.io/silvaisaac148/sdai-sensor:0.1.0" in monospace cyan text on dark background, like a terminal command. Cursor blinks at end. Subtitle below: "Disponible ahora · Gratis · Open Source MIT". 24fps.
```

### Scene 6.5 (5:47–6:00) — Veo
```
Final shot: the SDAI logo emerges large on a dark background. Slowly rotating 3D globe behind it (semi-transparent). Tagline below: "github.com/silvaisaac148/SDAI". Holds for 5 seconds. Cinematic outro. 24fps.
```

**Voiceover sección 6:**
> "SDAI está disponible hoy. Gratis. Open source. Listo para proteger tu PyME en menos de diez minutos. Repositorio en GitHub: silvaisaac148 barra SDAI. Gracias por ver."

---

## Música y audio

### Música de fondo (royalty-free, sugerencias)
- **Hook (0:00-0:45):** "Cyber Tech" o "Tension Build" — Epidemic Sound / Artlist
- **Presentación (0:45-1:30):** "Inspiring Tech Discovery" — sutil, ascendente
- **Arquitectura (1:30-2:15):** "Minimal Tech Pulse" — electrónica minimalista
- **Demo (2:15-4:30):** "Focused Productivity" — beats sutiles tipo lo-fi tech
- **Resultados (4:30-5:15):** "Achievement Reveal" — ascendente, motivador
- **Cierre (5:15-6:00):** "Hopeful Tech Outro" — emotivo, sin ser cursi

### Voiceover
- Tono: claro, profesional, ritmo medio (no apurado)
- Acento: español neutro latinoamericano (Venezuela/Colombia)
- Edad voz: 25-40
- Género: indistinto (probar ambos)
- **Tools:** ElevenLabs (mejor calidad), Google TTS, o grabación humana real (preferible si tienen micrófono decente)

### SFX puntuales
- Click suave en cada transición de slide
- Notification "ding" cuando aparece alerta Telegram en pantalla
- Whoosh sutil en transiciones de escenas

---

## Workflow de producción

### 1. Generar clips Veo (1-2 días)
- Sesión Veo: copia el STYLE GUIDE primero
- Genera cada escena con su prompt textual
- Si una escena no queda bien, refina el prompt (añade "no humans", "no faces visible", "minimalist", según necesidad)
- Guarda con nombres: `01_01_intro.mp4`, `01_02_office.mp4`, etc.

### 2. Capturar screen recordings reales (1 hora)
- Setup local: backend corriendo + simulator listo + Telegram visible + Gmail visible
- Tool: OBS Studio (gratis) o ShareX o macOS QuickTime
- Resolución: 1920×1080 mínimo, 60fps si pueden
- Pre-grabar la simulación 2-3 veces para tener takes alternativos

### 3. Grabar voiceover (1 hora)
- Si humana: micrófono USB (Blue Yeti / Samson Q2U), ambiente silencioso, post en Audacity (noise reduction + compresión)
- Si IA: ElevenLabs voz "Domi" o "Bella" en español
- Script: arriba en cada sección

### 4. Editar (1-2 días)
- Software: DaVinci Resolve (gratis, profesional), CapCut Desktop (gratis, fácil)
- Importar todos los clips Veo + screen recordings + voiceover + música
- Cortar a tiempos del esquema
- Color grading consistente (LUT cyan/teal)
- Transiciones: cross-fade 0.3s entre escenas (nunca cuts duros entre Veo y screen recording)
- Bajar música a -18dB cuando hay voiceover

### 5. Exportar
- Format: MP4 H.264, 1080p, 8-10 Mbps bitrate
- Audio: AAC 192kbps stereo
- Subtítulos: generar con Whisper auto-translate, revisar manualmente

### 6. Publicar
- YouTube unlisted primero → compartir con jurado/profesor
- Backup en Google Drive o WeTransfer
- Link en `README.md` + `PRESENTACION.md`

---

## Tips para que Veo no falle

**Hace bien:**
- Tomas wide-shot, paisajes, oficinas vacías
- Objetos en primer plano (laptop, router, smartphone)
- Texto animado en background plano
- Pantallas con UI ficticia genérica

**Hace mal:**
- Personas con caras claras (deforma, distorsiona)
- Texto específico en pantallas (lo escribe mal o lo distorsiona) → **SIEMPRE usar screen recording real para mostrar el dashboard**
- Manos escribiendo en teclado (puede salir 6 dedos)
- Logos específicos (los inventa parecidos)

**Workaround para caras:**
- "no faces visible"
- "back to camera"
- "from behind"
- "silhouette only"
- "hands only, no face"

**Workaround para texto:**
- "minimal background text"
- "abstract symbols only"
- Para texto específico → screen recording real, no Veo

---

## Prompt extra: thumbnail YouTube

```
A striking thumbnail for a cybersecurity product video. Center: a 3D Earth globe with multiple bright cyan glowing arcs flowing between countries (like Kaspersky Cybermap). Background: dark navy blue with subtle data flow particles. Top-left: large white text "SDAI" in modern sans-serif. Bottom: smaller cyan text "Detección de Intrusiones para PyMEs". Right side: small icon of a smartphone showing a Telegram alert notification. Cinematic, high-contrast, eye-catching. 16:9 ratio, 1920×1080. No watermarks. Professional product video thumbnail style.
```

---

## Checklist final

- [ ] STYLE GUIDE pegado al inicio de sesión Veo
- [ ] 30+ clips Veo generados (8s cada uno)
- [ ] 8-10 screen recordings reales de SDAI (1080p)
- [ ] Voiceover grabado completo (6 secciones)
- [ ] Música elegida y descargada (royalty-free)
- [ ] Editado en DaVinci/CapCut con transiciones suaves
- [ ] Subtítulos en español + inglés
- [ ] Exportado MP4 1080p
- [ ] Thumbnail generado
- [ ] Subido a YouTube unlisted
- [ ] Link añadido a README.md y PRESENTACION.md
