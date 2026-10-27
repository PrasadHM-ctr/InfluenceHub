"""Create a verified test influencer and print a JWT for node probes."""

import os
import sys
import uuid

sys.path.insert(0, ".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

import json  # noqa: E402

from accounts.models import EmailVerificationCode  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from influencers.serializers import InfluencerRegisterSerializer  # noqa: E402
from rest_framework_simplejwt.tokens import RefreshToken  # noqa: E402

RUN = uuid.uuid4().hex[:8]
username = f"axprobe{RUN}"
payload = {
    "username": username,
    "email": f"{username}@example.com",
    "password": "safe-password-123",
    "full_name": "Axios Probe",
    "category": "QA",
    "language": "English",
    "followers": 5,
    "city": "Pune",
    "state": "Maharashtra",
}
serializer = InfluencerRegisterSerializer(data=payload)
serializer.is_valid(raise_exception=True)
serializer.save()

code = EmailVerificationCode.objects.filter(user__email=payload["email"]).order_by("-created_at").first()
user = User.objects.get(username=username)
code.consume if hasattr(code, "consume") else None
from accounts.services import confirm_email_with_code  # noqa: E402

confirm_email_with_code(user=user, code=code.code)

token = str(RefreshToken.for_user(user).access_token)
with open("node_token.txt", "w") as handle:
    handle.write(json.dumps({"token": token, "username": username}))

# Valid PNG on disk for the node probe (Pillow guarantees a real image).
from PIL import Image  # noqa: E402

image_path = os.path.join("..", "influencer-marketplace", "probe.png")
Image.new("RGB", (6, 6), (90, 40, 200)).save(image_path, format="PNG")
print("user ready:", username)
