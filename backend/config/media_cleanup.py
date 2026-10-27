"""Small helpers that keep stored-media footprint (and therefore S3 cost) low.

When a profile image / logo is replaced the previous object is removed from
storage so orphaned files never accumulate. Failures are swallowed: cleanup is
a cost optimisation and must never break a user request.
"""

import logging

logger = logging.getLogger(__name__)


def delete_replaced_file(*, old_name: str, new_name: str) -> None:
    """Delete the previous stored file after a successful replacement."""
    if not old_name or old_name == new_name:
        return
    delete_stored_file(old_name)


def delete_stored_file(file_name: str) -> None:
    """Delete a single stored media object (used on media-row removal)."""
    if not file_name:
        return
    from django.core.files.storage import default_storage

    try:
        default_storage.delete(file_name)
    except Exception:  # pragma: no cover - cleanup must never break requests
        logger.warning("Could not delete stored media object %s", file_name)
