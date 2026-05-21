"""Telegram Bot API notifier — sync HTTP POST, fire-and-log on error."""
from __future__ import annotations

import sys
from typing import Optional

import httpx

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram(token: str, chat_id: str, text: str, timeout: float = 4.0) -> bool:
    """Send a Telegram message. Returns True on HTTP 200, False otherwise."""
    if not token or not chat_id or not text:
        return False
    url = TELEGRAM_API.format(token=token)
    try:
        r = httpx.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=timeout,
        )
        if r.status_code == 200:
            return True
        print(f"[telegram] non-200 response: {r.status_code} {r.text[:200]}", file=sys.stderr)
        return False
    except httpx.HTTPError as e:
        print(f"[telegram] HTTP error: {e}", file=sys.stderr)
        return False


def format_alert_markdown(alert: dict) -> str:
    """Compose a Markdown message body from a triggered alert dict."""
    threat = (alert.get("threat_type") or "?").upper()
    sev = (alert.get("severity") or "?").upper()
    src = alert.get("src_ip") or "?"
    desc = alert.get("description") or "(sin descripción)"
    country = alert.get("country") or "—"
    city = alert.get("city") or "—"
    return (
        f"🚨 *SDAI · Alerta {sev}*\n"
        f"*Tipo:* `{threat}`\n"
        f"*Origen:* `{src}` ({city}, {country})\n"
        f"*Detalle:* {desc}"
    )
