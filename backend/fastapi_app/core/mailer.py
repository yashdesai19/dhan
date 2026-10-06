"""Outgoing email. Pluggable: development logs messages; production wires a real provider here."""

import logging

from fastapi_app.core.config import settings

logger = logging.getLogger("fastapi_app.mailer")


def send_password_reset(email: str, token: str) -> None:
    """Delivers a reset code. Until an email provider is configured, development logs it so the
    flow can be completed locally; production logs only that a message was due (never the code)."""
    if settings.is_production:
        logger.warning("Password reset requested but no email provider is configured")
        return
    logger.info("[dev mailer] Password reset code for %s: %s", email, token)
