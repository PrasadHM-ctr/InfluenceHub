"""Resend a fresh verification code for the given email, then print it."""

import json
import sys
import urllib.request

email = sys.argv[1] if len(sys.argv) > 1 else "prasadhm439@gmail.com"

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/resend-verification/",
    data=json.dumps({"email": email}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        print("resend status:", response.status)
except urllib.error.HTTPError as error:
    print("resend FAILED:", error.code)
    body = error.read().decode(errors="replace")
    # DEBUG=True pages embed the exception; pull out the useful line
    for marker in ("Exception Value", "Exception Type", "<pre class=\"exception_value\">"):
        if marker in body:
            start = body.find(marker)
            print(body[start : start + 300].replace("\n", " ")[:300])
            break
    else:
        print(body[:300])


sys.path.insert(0, ".")
os = __import__("os")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from accounts.models import EmailVerificationCode  # noqa: E402

code = (
    EmailVerificationCode.objects.filter(user__email=email, consumed_at__isnull=True)
    .order_by("-created_at")
    .first()
)
if code:
    state = "EXPIRED" if code.is_expired else "VALID"
    print(f"FRESH CODE for {email}: {code.code} [{state}]")
else:
    print("no code found")
