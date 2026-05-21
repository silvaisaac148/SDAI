"""Tests Sprint 5-6: dispatcher de notificaciones (Telegram / Email)."""
from unittest.mock import patch, MagicMock

from app.notifications.dispatcher import (
    NotificationDispatcher,
    SEVERITY_CHANNELS,
    _parse_recipients,
)
from app.notifications.telegram import format_alert_markdown
from app.notifications.email_smtp import format_alert_text


SAMPLE_ALERT = {
    "threat_type": "port_scan",
    "severity": "alta",
    "src_ip": "1.2.3.4",
    "description": "IP 1.2.3.4 escaneó 25 puertos",
    "country": "Estados Unidos",
    "city": "Mountain View",
    "details": {"ports_scanned": [22, 80, 443]},
}


def test_severity_routing_alta_uses_both():
    assert set(SEVERITY_CHANNELS["alta"]) == {"telegram", "email"}


def test_severity_routing_baja_uses_none():
    assert SEVERITY_CHANNELS["baja"] == ()


def test_dispatcher_no_credentials_skips_silently():
    d = NotificationDispatcher()
    with patch.object(d, "telegram_enabled", return_value=False), \
         patch.object(d, "email_enabled", return_value=False):
        result = d.dispatch(SAMPLE_ALERT)
    assert result == {}


def test_dispatcher_routes_alta_to_both_when_enabled():
    d = NotificationDispatcher()
    with patch.object(d, "telegram_enabled", return_value=True), \
         patch.object(d, "email_enabled", return_value=True), \
         patch("app.notifications.dispatcher.send_telegram", return_value=True) as mt, \
         patch("app.notifications.dispatcher.send_email", return_value=True) as me, \
         patch("app.notifications.dispatcher.settings") as mock_settings:
        mock_settings.TELEGRAM_BOT_TOKEN = "x"
        mock_settings.TELEGRAM_CHAT_ID = "y"
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "u"
        mock_settings.SMTP_PASSWORD = "p"
        mock_settings.SMTP_SENDER = "u"
        mock_settings.SMTP_USE_TLS = True
        mock_settings.EMAIL_RECIPIENTS = "a@b.com,c@d.com"
        result = d.dispatch(SAMPLE_ALERT)
    assert result == {"telegram": True, "email": True}
    mt.assert_called_once()
    me.assert_called_once()
    assert me.call_args.kwargs["recipients"] == ["a@b.com", "c@d.com"]


def test_dispatcher_media_uses_only_telegram():
    d = NotificationDispatcher()
    alert = {**SAMPLE_ALERT, "severity": "media"}
    with patch.object(d, "telegram_enabled", return_value=True), \
         patch.object(d, "email_enabled", return_value=True), \
         patch("app.notifications.dispatcher.send_telegram", return_value=True) as mt, \
         patch("app.notifications.dispatcher.send_email", return_value=True) as me, \
         patch("app.notifications.dispatcher.settings"):
        result = d.dispatch(alert)
    assert "telegram" in result and "email" not in result
    mt.assert_called_once()
    me.assert_not_called()


def test_format_telegram_markdown_contains_key_fields():
    md = format_alert_markdown(SAMPLE_ALERT)
    assert "PORT_SCAN" in md
    assert "1.2.3.4" in md
    assert "Mountain View" in md
    assert "ALTA" in md


def test_format_email_text_returns_subject_and_body():
    subj, body = format_alert_text(SAMPLE_ALERT)
    assert "[SDAI]" in subj
    assert "PORT_SCAN" in subj
    assert "Estados Unidos" in body
    assert "1.2.3.4" in body


def test_parse_recipients_handles_str_and_list():
    assert _parse_recipients("a@b.com, c@d.com") == ["a@b.com", "c@d.com"]
    assert _parse_recipients(["a@b.com", "c@d.com"]) == ["a@b.com", "c@d.com"]
    assert _parse_recipients("") == []
    assert _parse_recipients(None) == []
