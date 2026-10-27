"""Local zero-AWS mode probe: run with USE_S3/USE_SES explicitly False."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["USE_S3"] = "False"
os.environ["USE_SES"] = "False"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from django.core.files.storage import default_storage  # noqa: E402

backend = "localmedia" if hasattr(settings, "STORAGES") and "FileSystem" in settings.STORAGES["default"]["BACKEND"] else type(default_storage).__name__
path = default_storage.save("localmode/probe.txt", ContentFile(b"hi"))
ok = default_storage.exists(path)
default_storage.delete(path)
gone = not default_storage.exists(path)

print("USE_S3 =", settings.USE_S3, "| USE_SES =", settings.USE_SES)
print("storage backend =", backend)
print("email backend   =", settings.EMAIL_BACKEND)
print("save/read/delete on LOCAL disk:", ok and gone)
