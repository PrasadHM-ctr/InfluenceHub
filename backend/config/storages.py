"""S3 media storage used when USE_S3=true.

All uploads flow through Django (validated, permission-checked) and land in
dedicated S3 folders. PostgreSQL stores only the object key/URL reference —
never binary data. The bucket itself must never be publicly writable; objects
are written by the backend using server-side credentials loaded from env vars.
"""

from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """Default media storage: profiles/, business-logos/, campaigns/, chat/, documents/."""

    location = ""
    file_overwrite = False
    default_acl = None