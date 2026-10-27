"""Probe live login + photo-upload behaviour (creates & cleans own data)."""

import io
import json
import sys
import uuid

import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"


def request_json(path, payload, method="POST", token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(payload).encode(), headers=headers, method=method)
    return _send(req)


def _send(req):
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read().decode()[:8000]
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:400]


sys.path.insert(0, ".")
import os  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from accounts.models import EmailVerificationCode  # noqa: E402

RUN = uuid.uuid4().hex[:8]
username = f"phototest{RUN}"

status_code, body = request_json(
    "/influencer/register/",
    {
        "username": username,
        "email": f"{username}@example.com",
        "password": "safe-password-123",
        "full_name": "Photo Test",
        "category": "QA",
        "language": "English",
        "followers": 10,
        "city": "Pune",
        "state": "Maharashtra",
    },
)
print("register:", status_code)

code = (
    EmailVerificationCode.objects.filter(user__email=f"{username}@example.com", consumed_at__isnull=True)
    .order_by("-created_at")
    .first()
    .code
)
print("verify:", request_json("/verify-email/", {"email": f"{username}@example.com", "code": code}))
status_code, body = request_json("/login/", {"username": username, "password": "safe-password-123"})
print("login:", status_code)
token = json.loads(body)["access"]

# --- valid PNG upload -------------------------------------------------------
from PIL import Image  # noqa: E402

buffer = io.BytesIO()
Image.new("RGB", (4, 4), (120, 60, 200)).save(buffer, format="PNG")
png = buffer.getvalue()

boundary = "----probe123"
parts = []
parts.append(
    f'--{boundary}\r\nContent-Disposition: form-data; name="profile_image"; filename="test.png"\r\n'
    f"Content-Type: image/png\r\n\r\n".encode()
    + png
    + b"\r\n"
)
parts.append(f"--{boundary}--\r\n".encode())
multipart = b"".join(parts)

req = urllib.request.Request(
    f"{BASE}/influencer/profile/",
    data=multipart,
    method="PATCH",
    headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": f"Bearer {token}",
    },
)
print("valid PNG upload ->", _send(req))

# --- oversized PNG (>5MB) ---------------------------------------------------
big = Image.new("RGB", (1400, 1400), (10, 10, 10))
buf2 = io.BytesIO()
big.save(buf2, format="PNG")
noise = buf2.getvalue() + b"0" * (6 * 1024 * 1024)  # pad past 5 MB
parts2 = [
    f'--{boundary}\r\nContent-Disposition: form-data; name="profile_image"; filename="big.png"\r\n'
    f"Content-Type: image/png\r\n\r\n".encode()
    + noise
    + f"\r\n--{boundary}--\r\n".encode()
]
req2 = urllib.request.Request(
    f"{BASE}/influencer/profile/",
    data=b"".join(parts2),
    method="PATCH",
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Authorization": f"Bearer {token}"},
)
print("oversized upload ->", _send(req2))

# --- cleanup ----------------------------------------------------------------
from django.contrib.auth.models import User  # noqa: E402

User.objects.filter(username=username).delete()
print("cleanup done")

