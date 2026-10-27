"""Notification creation helpers used across apps.

`notify()` is intentionally tolerant: a notification failure must never break
the primary operation (campaign accept, message send, …).
"""

import logging

from django.contrib.auth.models import User

from .models import Notification

logger = logging.getLogger(__name__)


def notify(
    *,
    recipient: User,
    notification_type: str,
    title: str,
    message: str,
    link: str = "",
) -> Notification | None:
    if recipient is None:
        return None
    try:
        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title[:200],
            message=message,
            link=link or "",
        )
    except Exception:  # pragma: no cover - never break the caller
        logger.exception("Failed to create notification for user %s", recipient.pk)
        return None


def notify_many(*, recipients, **kwargs) -> None:
    for recipient in recipients:
        if recipient is not None:
            notify(recipient=recipient, **kwargs)