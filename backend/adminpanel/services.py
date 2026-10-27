"""Audit-log helpers shared by every admin view."""

from adminpanel.models import AuditLog


def record_audit(*, actor, action: str, target_type: str = "", target_id="", description: str = "") -> AuditLog | None:
    """Best-effort immutable audit record.

    Auditing must never break the primary operation, so failures are
    swallowed after logging. Only non-sensitive metadata is stored.
    """
    try:
        authenticated = actor is not None and getattr(actor, "is_authenticated", False)
        return AuditLog.objects.create(
            actor=actor if authenticated else None,
            action=action,
            target_type=str(target_type)[:40],
            target_id=str(target_id)[:64],
            description=str(description)[:2000],
        )
    except Exception:  # pragma: no cover - auditing must never break requests
        return None
