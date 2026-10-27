"""Check one email's account + pending code. Usage: python check_account.py <email>"""

import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from accounts.models import EmailVerificationCode  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402

email = sys.argv[1]
user = User.objects.filter(email__iexact=email).first()
if not user:
    print(f"NO ACCOUNT exists for {email} — signup never completed.")
else:
    print(f"account: {user.username!r} | active(verified): {user.is_active}")
    codes = EmailVerificationCode.objects.filter(user=user).order_by("-created_at")[:3]
    for code in codes:
        state = "EXPIRED" if code.is_expired else ("used" if code.is_consumed else "VALID")
        print(f"  code {code.code} [{state}] created {code.created_at:%H:%M}")
