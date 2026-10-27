"""SES delivery probe: attempts ONE transactional send with USE_SES=true.

Run with:  $env:USE_SES='True'; python aws_ses_probe.py
Reports the exact AWS rejection reason (identity unverified / sandbox etc.)
so nothing is bypassed or guessed.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["USE_SES"] = "True"

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.core.mail import send_mail  # noqa: E402

print("EMAIL_BACKEND =", settings.EMAIL_BACKEND)
print("SES region    =", settings.AWS_SES_REGION_NAME)
print("From address  =", settings.DEFAULT_FROM_EMAIL)

try:
    message_id = send_mail(
        subject="InfluenceHub SES connectivity test",
        message="One-off transactional email test from the InfluenceHub backend.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.DEFAULT_FROM_EMAIL or "no-reply@example.com"],
        fail_silently=False,
    )
    print("SEND_OK message_id=", message_id)
except Exception as error:  # noqa: BLE001
    name = type(error).__name__
    code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
    print(f"SEND_BLOCKED {name} code={code}")
    print("reason:", str(error).splitlines()[0][:300])
