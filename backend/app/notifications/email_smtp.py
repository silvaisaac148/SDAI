"""SMTP email notifier (TLS) — single-recipient simple text message."""
from __future__ import annotations

import smtplib
import sys
from email.message import EmailMessage
from typing import Iterable


def send_email(
    host: str,
    port: int,
    username: str,
    password: str,
    sender: str,
    recipients: Iterable[str],
    subject: str,
    body: str,
    use_tls: bool = True,
    timeout: float = 6.0,
) -> bool:
    """Send a plain-text email via SMTP. Returns True on success."""
    if not host or not username or not password or not recipients:
        return False

    msg = EmailMessage()
    msg["From"] = sender or username
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            smtp.ehlo()
            if use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as e:
        print(f"[email] SMTP error: {e}", file=sys.stderr)
        return False


def format_alert_text(alert: dict) -> tuple[str, str]:
    """Return (subject, body) plain text for an alert."""
    threat = (alert.get("threat_type") or "?").upper()
    sev = (alert.get("severity") or "?").upper()
    src = alert.get("src_ip") or "?"
    desc = alert.get("description") or "(sin descripción)"
    country = alert.get("country") or "Desconocido"
    city = alert.get("city") or "Desconocido"
    subject = f"[SDAI] {sev} · {threat} desde {src}"
    body = (
        f"Sistema de Detección de Intrusiones (SDAI) — Alerta {sev}\n"
        f"-------------------------------------------------------\n\n"
        f"Tipo de amenaza : {threat}\n"
        f"Origen          : {src}  ({city}, {country})\n"
        f"Severidad       : {sev}\n\n"
        f"Descripción:\n  {desc}\n\n"
        f"Detalles técnicos:\n  {alert.get('details') or {}}\n\n"
        f"-- SDAI Sensor automático\n"
    )
    return subject, body
