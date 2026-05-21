"""Notification dispatcher — routes alerts to Telegram + Email per severity policy.

Channels are enabled by the presence of valid credentials in `Settings`. Missing
credentials make the channel a silent no-op so dev environments don't have to
configure anything.

Severity policy (default):
- alta:  Telegram + Email
- media: Telegram only
- baja:  none
"""
from __future__ import annotations

import sys
import threading
from typing import Iterable

from app.config import settings
from app.notifications.email_smtp import format_alert_text, send_email
from app.notifications.telegram import format_alert_markdown, send_telegram

# Severity routing — keep tunable from a single place.
SEVERITY_CHANNELS = {
    "alta": ("telegram", "email"),
    "media": ("telegram",),
    "baja": (),
}


class NotificationDispatcher:
    """Thread-pooled dispatcher so SSE/HTTP latency isn't blocked on SMTP."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    # ---------- channel availability ----------

    def telegram_enabled(self) -> bool:
        return bool(getattr(settings, "TELEGRAM_BOT_TOKEN", "")) and bool(getattr(settings, "TELEGRAM_CHAT_ID", ""))

    def email_enabled(self) -> bool:
        return all(
            getattr(settings, k, "")
            for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_RECIPIENTS")
        )

    # ---------- public API ----------

    def dispatch(self, alert: dict) -> dict:
        """Send an alert through the channels mandated by its severity.

        Returns a dict of channel -> bool (True if delivered) for observability.
        """
        sev = (alert.get("severity") or "baja").lower()
        channels = SEVERITY_CHANNELS.get(sev, ())
        results: dict[str, bool] = {}

        if "telegram" in channels and self.telegram_enabled():
            results["telegram"] = send_telegram(
                token=settings.TELEGRAM_BOT_TOKEN,
                chat_id=settings.TELEGRAM_CHAT_ID,
                text=format_alert_markdown(alert),
            )
        if "email" in channels and self.email_enabled():
            recipients = _parse_recipients(settings.EMAIL_RECIPIENTS)
            subject, body = format_alert_text(alert)
            results["email"] = send_email(
                host=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                sender=getattr(settings, "SMTP_SENDER", "") or settings.SMTP_USER,
                recipients=recipients,
                subject=subject,
                body=body,
                use_tls=getattr(settings, "SMTP_USE_TLS", True),
            )
        return results

    def dispatch_async(self, alert: dict) -> None:
        """Fire-and-forget dispatch in a daemon thread. Errors are logged, not raised."""
        if not self._any_channel_relevant(alert):
            return
        t = threading.Thread(target=self._safe_dispatch, args=(alert,), daemon=True)
        t.start()

    # ---------- internals ----------

    def _any_channel_relevant(self, alert: dict) -> bool:
        sev = (alert.get("severity") or "baja").lower()
        channels = SEVERITY_CHANNELS.get(sev, ())
        if not channels:
            return False
        if "telegram" in channels and self.telegram_enabled():
            return True
        if "email" in channels and self.email_enabled():
            return True
        return False

    def _safe_dispatch(self, alert: dict) -> None:
        try:
            self.dispatch(alert)
        except Exception as e:
            print(f"[notifications] dispatch failed: {e}", file=sys.stderr)


def _parse_recipients(raw: str | Iterable[str]) -> list[str]:
    if isinstance(raw, (list, tuple)):
        return [r.strip() for r in raw if r.strip()]
    if not raw:
        return []
    return [p.strip() for p in str(raw).split(",") if p.strip()]


dispatcher = NotificationDispatcher()


def notify_alert(alert: dict) -> None:
    """Shorthand used by the state manager."""
    dispatcher.dispatch_async(alert)
