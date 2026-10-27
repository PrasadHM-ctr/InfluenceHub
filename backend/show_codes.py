"""Show recent signups & unconsumed verification codes (admin visibility)."""

import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from accounts.models import EmailVerificationCode  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402

print("=== last 8 accounts ===")
for user in User.objects.order_by("-id")[:8]:
    print(f"  id={user.id} username={user.username!r} active={user.is_active} joined={user.date_joined:%m-%d %H:%M}")

print("=== unconsumed verification codes ===")
codes = EmailVerificationCode.objects.filter(consumed_at__isnull=True).order_by("-created_at")[:8]
if not codes:
    print("  (none - no pending unverified accounts)")
for code in codes:
    expired = "EXPIRED" if code.is_expired else "valid"
    print(f"  {code.user.username!r} <{code.user.email}> CODE={code.code} [{expired}]")
