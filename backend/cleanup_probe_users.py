"""Remove self-created probe users (axprobe*/phototest* only)."""

import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402

count, _ = User.objects.filter(username__startswith="axprobe").delete()
count2, _ = User.objects.filter(username__startswith="phototest").delete()
print(f"cleaned {count + count2} probe-user cascade rows")
