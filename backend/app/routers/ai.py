"""Defensive and pedagogical AI endpoints using Gemini and Windows/Linux local firewalls."""
from datetime import datetime, timezone
import ipaddress
import platform
import subprocess
import sys
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from app.config import settings
from app.db.supabase_client import get_client, execute_with_retry
from app.routers.events import investigate_ip

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None


class BlockResponse(BaseModel):
    status: str
    src_ip: str
    os: str
    firewall_command: str
    firewall_status: str
    blacklist_status: str
    explanation: str


def _call_groq_api(system_prompt: str, user_prompt: str) -> Optional[str]:
    """Call Groq API using Llama 3.3 70B model."""
    key = settings.GROQ_API_KEY
    if not key:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }
    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=12.0)
        if r.status_code == 200:
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            return text
        else:
            print(f"[AI] Groq API error {r.status_code}: {r.text}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"[AI] Error calling Groq API: {e}", file=sys.stderr)
        return None


def _call_gemini_api(prompt: str) -> Optional[str]:
    """Call Google Gemini API using httpx directly."""
    key = settings.GEMINI_API_KEY
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=12.0)
        if r.status_code == 200:
            data = r.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text
        else:
            print(f"[AI] Gemini API error {r.status_code}: {r.text}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"[AI] Error calling Gemini API: {e}", file=sys.stderr)
        return None


@router.post("/chat", response_model=dict)
async def ai_chat(body: ChatRequest):
    """Pedagogical Cybersecurity tutor chat interface."""
    user_msg = body.message.strip()
    history = body.history or []
    
    # Construct chat context
    history_context = ""
    for h in history[-6:]:
        role = "Estudiante" if h.get("sender") == "user" else "Tutor SDAI"
        history_context += f"{role}: {h.get('text')}\n"
        
    system_prompt = """
Eres el Tutor de Ciberseguridad de SDAI (Sistema de Detección y Alerta de Intrusiones).
Tu misión es responder preguntas de estudiantes y profesores de manera muy didáctica, educativa, amable y con terminología comprensible sobre ciberseguridad, protocolos de red (TCP, UDP, ICMP), captura de paquetes con Scapy, escaneo de puertos, denegación de servicio (DoS), ataques de fuerza bruta SSH, uso de adaptadores de red inalámbricos como el Archer T3U AC1300, modo promiscuo, modo monitor, y defensa activa mediante firewalls.
Intenta usar ejemplos prácticos o analogías simples cuando expliques conceptos complejos (ej. comparar puertos con puertas de un edificio, comparar paquetes con cartas postales).
Responde siempre en español y mantén un formato Markdown limpio con negritas y listas.
"""

    # 1. Try Groq
    if settings.GROQ_API_KEY:
        user_prompt = f"Historial de conversación reciente:\n{history_context}\nEstudiante: {user_msg}\nTutor SDAI:"
        reply = _call_groq_api(system_prompt, user_prompt)
        if reply:
            return {"reply": reply, "mode": "groq"}
            
    # 2. Try Gemini
    if settings.GEMINI_API_KEY:
        gemini_prompt = f"{system_prompt}\n\nHistorial de conversación reciente:\n{history_context}\nEstudiante: {user_msg}\nTutor SDAI:"
        reply = _call_gemini_api(gemini_prompt)
        if reply:
            return {"reply": reply, "mode": "gemini"}
            
    # 3. Heuristic Fallback
    msg_lower = user_msg.lower()
    reply = ""
    if "port scan" in msg_lower or "escaneo" in msg_lower or "puerto" in msg_lower:
        reply = """
### 🔍 Escaneo de Puertos (Port Scan)
**Explicación Didáctica:** Piensa en un ladrón que camina por un pasillo de un hotel y va probando las manijas de cada puerta una por una para ver cuál está abierta. Eso es un escaneo de puertos. El atacante envía paquetes TCP SYN (sincronización) de forma secuencial a muchos puertos para ver qué servicios (puerta 80 para HTTP, puerta 22 para SSH, etc.) están listos para recibir conexiones.

**Cómo lo detecta SDAI:**
Utilizamos Scapy en Python para contar cuántos puertos destino únicos está sondeando una misma IP de origen en una ventana deslizante de 60 segundos. Si supera el umbral configurado (ej. 20 puertos), se genera una alerta.

¿Quieres saber cómo defendernos o simular este ataque en el laboratorio?
"""
    elif "dos" in msg_lower or "ddos" in msg_lower or "denegacion" in msg_lower or "saturacion" in msg_lower:
        reply = """
### 🌊 Denegación de Servicio (DoS / DDoS)
**Explicación Didáctica:** Imagina que tienes una heladería muy pequeña y, de repente, entran 1,000 personas al mismo tiempo pidiendo un vaso de agua gratis. No puedes atender a tus verdaderos clientes de helados porque estás completamente saturado. Eso es un ataque DoS. El atacante inunda tu sistema con miles de paquetes por segundo (PPS) para agotar tu ancho de banda y procesamiento.

**Cómo lo detecta SDAI:**
Monitoreamos en tiempo real la tasa de paquetes por segundo (PPS) del tráfico entrante. Si una sola IP excede el umbral de seguridad (ej. 1200 paquetes/s), el sistema clasifica de inmediato el evento como una anomalía masiva y emite una alerta crítica.

¿Te gustaría aprender sobre cómo mitigar esto o ver los comandos para simularlo?
"""
    elif "brute force" in msg_lower or "fuerza bruta" in msg_lower or "ssh" in msg_lower or "contraseña" in msg_lower:
        reply = """
### 🔑 Ataques de Fuerza Bruta
**Explicación Didáctica:** Imagina que alguien intenta entrar a tu casa trayendo una maleta gigante con 10,000 llaves diferentes y empieza a probar una por una en tu cerradura a toda velocidad. Eso es fuerza bruta. Consiste en probar sistemáticamente combinaciones de nombres de usuario y contraseñas de forma automatizada.

**Cómo lo detecta SDAI:**
Olfateamos las peticiones repetidas al puerto 22 (SSH) o similares en menos de un minuto. Si registramos múltiples conexiones consecutivas fallidas en un breve periodo, el State Manager bloquea temporalmente al atacante en la visualización y levanta una alerta.
"""
    elif "ac1300" in msg_lower or "tarjeta" in msg_lower or "archer" in msg_lower or "adaptador" in msg_lower:
        reply = """
### 📡 El Adaptador Archer T3U AC1300
**Explicación Didáctica:** Los adaptadores Wi-Fi integrados de las laptops están diseñados únicamente para enviar y recibir su propio tráfico de datos. En cambio, una tarjeta externa como el **Archer T3U AC1300** cuenta con un chipset de doble banda potente que puede ser configurado en **Modo Promiscuo** o **Modo Monitor**.

Esto permite que la tarjeta "escuche en el aire" y capture absolutamente todos los paquetes de datos que vuelan por la red local, incluso los que no van dirigidos a tu laptop, permitiendo un monitoreo defensivo y transparente a nivel empresarial.
"""
    else:
        reply = """
👋 ¡Hola! Soy tu **Tutor Pedagógico de Ciberseguridad de SDAI**. 

Estoy listo para enseñarte sobre redes y seguridad de forma muy didáctica. Actualmente opero en **Modo Offline Heurístico** (puedes activar la API de Groq o Google Gemini en el `.env` para tener respuestas de IA avanzadas en tiempo real).

Dime qué concepto te gustaría explorar hoy de manera didáctica:
1. 🔍 **Escaneo de Puertos** (Port Scan)
2. 🌊 **Denegación de Servicio** (DoS)
3. 🔑 **Fuerza Bruta**
4. 📡 **Adaptador AC1300 y Sniffing con Scapy**

¡Pregúntame lo que quieras y lo analizamos con analogías sencillas!
"""
    
    return {"reply": reply, "mode": "heuristic"}


@router.get("/explain/{src_ip}", response_model=dict)
async def ai_explain_ip(src_ip: str):
    """Analyze all traffic of an IP and generate an educational and defensive diagnostic report."""
    try:
        ip_details = await investigate_ip(src_ip)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to gather IP details: {e}")
        
    summary = ip_details.get("summary", {})
    geo = ip_details.get("geo") or {}
    ports = list(ip_details.get("ports", {}).keys())
    protocols = list(ip_details.get("protocols", {}).keys())
    alerts = ip_details.get("alerts", [])
    
    system_prompt = "Actúa como un Analista de Ciberseguridad Pedagógico y Defensivo del sistema SDAI de detección de intrusiones."
    user_prompt = f"""
Analiza el siguiente reporte forense de la IP sospechosa '{src_ip}':
- Total eventos de red detectados: {summary.get('events_count', 0)}
- Alertas de intrusión disparadas: {summary.get('alerts_count', 0)}
- Alertas de severidad alta: {summary.get('high_severity_count', 0)}
- Puertos destino contactados: {ports}
- Protocolos de comunicación: {protocols}
- Geolocalización: Ciudad de {geo.get('city', 'Desconocida')}, País {geo.get('country', 'Desconocido')}
- Últimas alertas descriptivas: {[a.get('description') for a in alerts[:3]]}

Genera un reporte analítico y didáctico en español estructurado exactamente en los siguientes puntos (usa formato Markdown con negritas y listas limpias):

1. **Diagnóstico Didáctico:** Explica con analogías simples de la vida real qué tipo de ataque intentó realizar esta IP y qué conceptos de red (como puertos, protocolos o paquetes) están implicados. Explica por qué es peligroso para una pequeña o mediana empresa.
2. **¿Cómo lo detectó el Sensor SDAI?:** Describe de forma educativa cómo nuestro sensor Scapy y la ventana de tiempo deslizante en Python detectaron este comportamiento anormal basándose en los datos analizados.
3. **Plan de Mitigación Defensivo:** Da 3 recomendaciones prácticas y sencillas (por ejemplo, deshabilitar puertos, robustecer contraseñas, etc.) para que una pyme pueda protegerse en el mundo real.
4. **Acción de Bloqueo Activo:** Justifica técnicamente por qué bloquear a nivel de kernel (Firewall de Windows Defender o iptables) es la mejor respuesta defensiva inmediata para neutralizar al atacante.
"""

    # 1. Try Groq
    if settings.GROQ_API_KEY:
        analysis = _call_groq_api(system_prompt, user_prompt)
        if analysis:
            return {"analysis": analysis, "mode": "groq"}
            
    # 2. Try Gemini
    if settings.GEMINI_API_KEY:
        gemini_prompt = f"{system_prompt}\n\n{user_prompt}"
        analysis = _call_gemini_api(gemini_prompt)
        if analysis:
            return {"analysis": analysis, "mode": "gemini"}
            
    # 3. Local Heuristic Fallback
    threats = [a.get("threat_type") for a in alerts]
    
    intro = f"""### 🛡️ Reporte Didáctico de Seguridad (Modo Local Heurístico)
Hemos analizado la actividad de la dirección IP **{src_ip}** ubicada geográficamente en **{geo.get('city', '—')}, {geo.get('country', 'Sin Datos')}**. 
El sistema ha registrado un total de **{summary.get('events_count', 0)} eventos** y **{summary.get('alerts_count', 0)} alertas**.
"""

    diag = ""
    detect = ""
    mitig = ""
    
    if "port_scan" in threats:
        diag = f"""
1. **Diagnóstico Didáctico:**
   - **Qué está pasando:** Se identificó un **Escaneo de Puertos**. En el mundo real, es el equivalente a que un intruso camine por un edificio probando cada ventana y puerta para ver cuál no tiene seguro. 
   - **Técnicamente:** Esta IP envió ráfagas de paquetes TCP SYN a tus puertos `{ports}`. Al sondear múltiples puertos secuenciales en milisegundos, busca servicios activos (como un servidor web o base de datos) para explotar vulnerabilidades conocidas.
"""
        detect = """
2. **¿Cómo lo detectó el Sensor SDAI?:**
   - El capturador en vivo ( Scapy ) leyó las tramas inalámbricas a través del adaptador AC1300 y el módulo `DetectionStateManager` agrupó los destinos en ventanas deslizantes. Al verificar que una sola IP de origen consultó más de 20 puertos en menos de un minuto, se activó la alerta automática.
"""
        mitig = """
3. **Plan de Mitigación Defensivo:**
   - **Ajustar Firewalls:** Habilitar reglas para que no respondan a escaneos rápidos (modo sigiloso/stealth).
   - **Cerrar Puertos:** Desactivar servicios no indispensables que escuchen en puertos públicos.
   - **Monitoreo Continuo:** Mantener el adaptador AC1300 vigilando tramas Wi-Fi no autorizadas.
"""
    elif "dos" in threats:
        diag = f"""
1. **Diagnóstico Didáctico:**
   - **Qué está pasando:** Se identificó un ataque de **Denegación de Servicio (DoS)**. Es como si miles de personas falsas saturaran la entrada de una pequeña oficina impidiendo el paso a los verdaderos clientes.
   - **Técnicamente:** La IP atacante envió una inundación masiva de paquetes ({protocols}) dirigida a tus servidores locales para congestionar el tráfico de red de tu pyme.
"""
        detect = f"""
2. **¿Cómo lo detectó el Sensor SDAI?:**
   - El sensor analizó la métrica PPS (Paquetes por Segundo). Al ver un incremento anormal superando los 500 PPS provenientes de la IP {src_ip}, el detector de DoS generó una alerta crítica de severidad alta de inmediato.
"""
        mitig = """
3. **Plan de Mitigación Defensivo:**
   - **Rate Limiting:** Configurar límites de velocidad de paquetes en el enrutador principal de la red.
   - **Bloqueo Perimetral:** Solicitar al Proveedor de Internet (ISP) que filter el tráfico de este origen.
   - **Firewall Activo:** Bloquear la dirección IP a nivel de kernel para que la laptop descarte sus paquetes sin procesarlos.
"""
    else:
        diag = f"""
1. **Diagnóstico Didáctico:**
   - **Qué está pasando:** Se observa actividad inusual pero moderada en protocolos `{protocols}`. Es el equivalente a un merodeador sospechoso en la periferia de tu negocio que ha disparado alertas de seguridad preventivas.
"""
        detect = """
2. **¿Cómo lo detectó el Sensor SDAI?:**
   - SDAI interceptó los paquetes a través del Archer T3U, extrayendo metadatos como flags TCP, puertos y volumen, cruzándolos con nuestras firmas estáticas y la lista negra local.
"""
        mitig = """
3. **Plan de Mitigación Defensivo:**
   - **Inspección de Tráfico:** Filtrar los paquetes de esta IP para analizar la carga útil (payload).
   - **Bloqueo preventivo:** Colocar la IP en lista negra preventiva para evitar sondeos mayores.
   - **Seguridad Física:** Asegurar que solo dispositivos corporativos tengan acceso a la red inalámbrica.
"""

    rule_just = """
4. **Acción de Bloqueo Activo:**
   - Aplicar un bloqueo de Firewall a nivel de kernel es la medida más efectiva. Esto hace que el hardware de red y el sistema operativo de tu laptop rechacen cualquier paquete del atacante al instante, ahorrando CPU y ancho de banda, logrando neutralizar la amenaza por completo de manera pasiva.
"""
    
    analysis = intro + diag + detect + mitig + rule_just
    return {"analysis": analysis, "mode": "heuristic"}


@router.post("/block/{src_ip}", response_model=BlockResponse)
async def ai_block_ip(src_ip: str):
    """Threat mitigation endpoint. Blocks IP in Windows Defender Firewall or Linux iptables, and adds to local blacklist."""
    # Strict IP validation — src_ip is interpolated into shell/iptables commands
    try:
        ipaddress.ip_address(src_ip)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid IP address: {src_ip!r}")

    system_os = platform.system()
    firewall_command = ""
    firewall_status = "Skipped (Unknown OS)"
    
    # 1. Apply OS Firewall Block (Requires Admin privileges on FastAPI process)
    if system_os == "Windows":
        rule_name = f"SDAI Bloqueo IA - {src_ip}"
        # PowerShell command to block IP in Windows Firewall
        firewall_command = f"New-NetFirewallRule -DisplayName '{rule_name}' -Direction Inbound -Action Block -RemoteAddress '{src_ip}'"
        
        cmd = [
            "powershell",
            "-Command",
            f"New-NetFirewallRule -DisplayName '{rule_name}' -Direction Inbound -Action Block -RemoteAddress '{src_ip}'"
        ]
        try:
            # First, check if the rule already exists to avoid duplicate errors
            chk_cmd = ["powershell", "-Command", f"Get-NetFirewallRule -DisplayName '{rule_name}'"]
            chk = subprocess.run(chk_cmd, capture_output=True, text=True, check=False)
            
            if chk.returncode == 0:
                firewall_status = "Active (Rule already exists)"
            else:
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    firewall_status = "Success (Rule created)"
                else:
                    err = res.stderr.strip()
                    if "AccessIsDenied" in err or "permission" in err.lower():
                        firewall_status = "Error: Acceso denegado (Requiere PowerShell como Administrador)"
                    else:
                        firewall_status = f"Failed: {err[:80]}"
        except Exception as e:
            firewall_status = f"Error: {e}"
            
    elif system_os == "Linux":
        firewall_command = f"iptables -A INPUT -s {src_ip} -j DROP"
        cmd = ["sudo", "iptables", "-A", "INPUT", "-s", src_ip, "-j", "DROP"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                firewall_status = "Success (iptables rule added)"
            else:
                firewall_status = f"Failed: {res.stderr.strip()}"
        except Exception as e:
            firewall_status = f"Error: {e}"
            
    # 2. Add to Supabase Blacklist Configurations table
    blacklist_status = "No-Op (Supabase disconnected)"
    client = get_client()
    if client is not None:
        try:
            # Fetch current blacklist_ips config
            res = execute_with_retry(lambda c: c.table("configurations").select("*").eq("key", "blacklist_ips").single())
            current_blacklist = res.data.get("value", []) if res.data else []
        except Exception:
            current_blacklist = []
            
        if src_ip not in current_blacklist:
            current_blacklist.append(src_ip)
            # Update cache in global state manager
            from app.services import state_manager
            state_manager.configs["blacklist_ips"] = current_blacklist
            
            try:
                # Save updated blacklist back to Supabase
                payload = {
                    "key": "blacklist_ips",
                    "value": current_blacklist,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                execute_with_retry(lambda c: c.table("configurations").upsert(payload))
                blacklist_status = "Success (Added to database blacklist)"
            except Exception as e:
                blacklist_status = f"Failed database update: {e}"
        else:
            blacklist_status = "Success (Already in database blacklist)"
    else:
        # Fallback to local memory update
        from app.services import state_manager
        current_blacklist = state_manager.configs.get("blacklist_ips", [])
        if src_ip not in current_blacklist:
            current_blacklist.append(src_ip)
            state_manager.configs["blacklist_ips"] = current_blacklist
            blacklist_status = "Success (Added to local memory blacklist)"
        else:
            blacklist_status = "Success (Already in local memory blacklist)"

    # 3. Create educational defense explanation
    explanation = f"""
🛡️ **Bloqueo Defensivo Activo Completado:**
- **Acción del Firewall:** {firewall_status}.
- **Acción de la Base de Datos:** {blacklist_status}.

**¿Qué significa esto didácticamente?:**
Al añadir esta regla al Firewall de tu sistema ({system_os}), le hemos dicho al kernel del sistema operativo que descarte inmediatamente cualquier paquete proveniente de la IP **{src_ip}** antes de procesarla. Además, al agregarla a la **Blacklist** local, el Dashboard coloreará y aislará todo su tráfico previo para evitar falsos positivos y proteger la red. ¡La amenaza ha sido mitigada de forma activa y segura!
"""

    return BlockResponse(
        status="blocked",
        src_ip=src_ip,
        os=system_os,
        firewall_command=firewall_command,
        firewall_status=firewall_status,
        blacklist_status=blacklist_status,
        explanation=explanation
    )
