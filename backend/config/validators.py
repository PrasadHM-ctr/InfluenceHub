"""Shared upload validation.

Every uploaded file passes through these checks before it is stored (locally
or in S3). Dangerous or oversized files are rejected with clear messages.
"""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf"}
ALLOWED_DOCUMENT_CONTENT_TYPES = {"application/pdf"}


def validate_image_upload(file, *, max_bytes: int | None = None) -> None:
    """Allow only JPG/JPEG/PNG/WEBP images within the size limit."""
    _validate_upload(
        file,
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
        allowed_content_types=ALLOWED_IMAGE_CONTENT_TYPES,
        label="Images",
        max_bytes=max_bytes or settings.PROFILE_IMAGE_MAX_BYTES,
    )


def validate_document_upload(file, *, max_bytes: int | None = None) -> None:
    """Allow only PDF documents within the size limit."""
    _validate_upload(
        file,
        allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS,
        allowed_content_types=ALLOWED_DOCUMENT_CONTENT_TYPES,
        label="Documents",
        max_bytes=max_bytes or settings.CAMPAIGN_ATTACHMENT_MAX_BYTES,
    )


def validate_chat_file_upload(file, *, image: bool) -> None:
    if image:
        validate_image_upload(file, max_bytes=settings.CHAT_MAX_UPLOAD_BYTES)
    else:
        validate_document_upload(file, max_bytes=settings.CHAT_MAX_UPLOAD_BYTES)


def _validate_upload(
    file,
    *,
    allowed_extensions: set[str],
    allowed_content_types: set[str],
    label: str,
    max_bytes: int,
) -> None:
    if not file:
        return

    extension = Path(getattr(file, "name", "")).suffix.lower()
    if extension not in allowed_extensions:
        raise ValidationError(f"{label} must be one of: {', '.join(sorted(allowed_extensions))}.")

    content_type = getattr(file, "content_type", "") or ""
    if content_type and content_type not in allowed_content_types:
        raise ValidationError("That file type is not allowed.")

    if getattr(file, "size", 0) > max_bytes:
        limit_mb = round(max_bytes / (1024 * 1024))
        raise ValidationError(f"{label} must be {limit_mb} MB or smaller.")