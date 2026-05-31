"""Отправка email.

Если SMTP не сконфигурирован (smtp_host пуст) — письмо не уходит реально,
а печатается в лог (dev-режим). Это позволяет тестировать флоу подтверждения
без почтового сервера. Для реальной отправки заполните SMTP_* в .env.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("petpro.email")


def _send_smtp(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def send_email(to: str, subject: str, body: str) -> bool:
    """Вернёт True, если письмо реально отправлено по SMTP, иначе False (dev-режим)."""
    if not settings.smtp_enabled:
        logger.warning("SMTP не настроен — письмо для %s НЕ отправлено. Тема: %s\n%s", to, subject, body)
        return False
    try:
        _send_smtp(to, subject, body)
        logger.info("Письмо отправлено на %s", to)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Не удалось отправить письмо на %s: %s", to, exc)
        return False


def send_verification_code(to: str, code: str) -> bool:
    subject = "PetPro — код подтверждения"
    body = (
        f"Здравствуйте!\n\n"
        f"Ваш код подтверждения регистрации в PetPro: {code}\n\n"
        f"Код действует {settings.verification_code_ttl_minutes} минут. "
        f"Если вы не регистрировались — просто проигнорируйте это письмо.\n"
    )
    return send_email(to, subject, body)
