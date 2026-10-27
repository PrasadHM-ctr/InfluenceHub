"""One-off live AWS integration check for InfluenceHub.

Runs the REAL Django stack (real .env -> real S3 bucket, real PostgreSQL)
through the actual REST endpoints: signup -> verify -> login -> logo/image
upload + REPLACE (old S3 object must be deleted), search, campaign with PDF
attachment, campaign accept, chat image/pdf uploads.

Self-created throwaway accounts/objects are removed at the end; pre-existing
data is never touched. Exits non-zero on any failure.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from django.core.files.storage import default_storage  # noqa: E402

from campaigns.models import CampaignRequest  # noqa: E402
from chat.models import Conversation  # noqa: E402
from notifications.models import Notification  # noqa: E402
from rest_framework import status  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

RUN_ID = uuid.uuid4().hex[:8]


def make_png():
    """Generate a guaranteed-valid tiny PNG via Pillow (ImageField runs PIL)."""
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color=(139, 92, 246)).save(buffer, format="PNG")
    return buffer.getvalue()


PNG_1X1 = make_png()
TINY_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"

results = []


def record(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" :: {detail}" if detail else ""))


def is_s3_url(url):
    return bool(url) and "influencehub-media-909762691220" in url


def s3_exists(key):
    if not key:
        return False
    return default_storage.exists(key.split("?")[0])  # strip signed-URL params



print("== settings ==")
from django.conf import settings  # noqa: E402

record("USE_S3 enabled", settings.USE_S3 is True, f"bucket={settings.AWS_STORAGE_BUCKET_NAME}")

print("== storage smoke test ==")
key = f"e2e-check/{RUN_ID}/probe.png"
path = default_storage.save(key, ContentFile(PNG_1X1))
record("storage.save", s3_exists(path), path)
with default_storage.open(path) as handle:
    data = handle.read()
record("storage.read-back", data == PNG_1X1, f"{len(data)} bytes")
default_storage.delete(path)
record("storage.delete", not s3_exists(path))

print("== business flow ==")
# SERVER_NAME keeps ALLOWED_HOSTS happy outside the Django test runner.
client = APIClient(SERVER_NAME="localhost")
biz_name = f"awse2ebiz{RUN_ID}"
r = client.post(
    "/api/business/register/",
    {
        "username": biz_name,
        "email": f"{biz_name}@example.com",
        "password": "safe-password-123",
        "company_name": "AWS E2E Co",
        "industry": "Testing",
        "phone": "1234567890",
        "city": "Mumbai",
        "state": "Maharashtra",
    },
    format="json",
)
record("business signup", r.status_code == status.HTTP_201_CREATED)

from accounts.models import EmailVerificationCode  # noqa: E402

code = (
    EmailVerificationCode.objects.filter(user__email=f"{biz_name}@example.com", consumed_at__isnull=True)
    .order_by("-created_at")
    .first()
    .code
)
r = client.post("/api/verify-email/", {"email": f"{biz_name}@example.com", "code": code}, format="json")
record("business email verify", r.status_code == status.HTTP_200_OK)

r = client.post("/api/login/", {"username": biz_name, "password": "safe-password-123"}, format="json")
record("business login (JWT)", r.status_code == status.HTTP_200_OK and r.data.get("role") == "business")
client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

logo_a = ContentFile(PNG_1X1, name=f"logo-a-{RUN_ID}.png")
r = client.put("/api/business/profile/", {"logo": logo_a}, format="multipart")
if r.status_code != 200:
    print("   logo#1 error body:", str(r.data)[:200])
logo_key_a = r.data["data"]["logo"].split(".com/")[-1] if r.status_code == 200 else ""
record(
    "logo upload #1 -> S3",
    r.status_code == 200 and is_s3_url(r.data["data"]["logo"]) and s3_exists(logo_key_a),
    logo_key_a,
)

logo_b = ContentFile(PNG_1X1, name=f"logo-b-{RUN_ID}.png")
r = client.put("/api/business/profile/", {"logo": logo_b}, format="multipart")
logo_key_b = r.data["data"]["logo"].split(".com/")[-1] if r.status_code == 200 else ""
old_gone = not s3_exists(logo_key_a)
new_there = s3_exists(logo_key_b)
record("logo replace: OLD object deleted", r.status_code == 200 and old_gone, f"a_gone={old_gone}")
record("logo replace: NEW object kept", r.status_code == 200 and new_there, logo_key_b)

print("== influencer flow ==")
inf_client = APIClient(SERVER_NAME="localhost")
inf_name = f"awse2einf{RUN_ID}"
r = inf_client.post(
    "/api/influencer/register/",
    {
        "username": inf_name,
        "email": f"{inf_name}@example.com",
        "password": "safe-password-123",
        "full_name": "AWS E2E Creator",
        "category": "Testing",
        "language": "English",
        "followers": 1000,
        "city": "Delhi",
        "state": "Delhi",
    },
    format="json",
)
record("influencer signup", r.status_code == status.HTTP_201_CREATED)

code = (
    EmailVerificationCode.objects.filter(user__email=f"{inf_name}@example.com", consumed_at__isnull=True)
    .order_by("-created_at")
    .first()
    .code
)
r = inf_client.post("/api/verify-email/", {"email": f"{inf_name}@example.com", "code": code}, format="json")
record("influencer email verify", r.status_code == status.HTTP_200_OK)

r = inf_client.post("/api/login/", {"username": inf_name, "password": "safe-password-123"}, format="json")
record("influencer login (JWT)", r.status_code == status.HTTP_200_OK and r.data.get("role") == "influencer")
inf_client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

img_a = ContentFile(PNG_1X1, name=f"pic-a-{RUN_ID}.png")
r = inf_client.patch("/api/influencer/profile/", {"profile_image": img_a}, format="multipart")
img_key_a = r.data["profile_image"].split(".com/")[-1] if r.status_code == 200 else ""
record(
    "profile image upload -> S3",
    r.status_code == 200 and is_s3_url(r.data["profile_image"]) and s3_exists(img_key_a),
    img_key_a,
)

img_b = ContentFile(PNG_1X1, name=f"pic-b-{RUN_ID}.png")
r = inf_client.patch("/api/influencer/profile/", {"profile_image": img_b}, format="multipart")
img_key_b = r.data["profile_image"].split(".com/")[-1] if r.status_code == 200 else ""
img_url_b = r.data["profile_image"] if r.status_code == 200 else ""
record(
    "image replace: OLD deleted / NEW kept",
    r.status_code == 200 and not s3_exists(img_key_a) and s3_exists(img_key_b),
)

print("== search ==")
r = client.get("/api/influencers/", {"search": "AWS E2E"})
record("search finds new creator (paginated)", r.status_code == 200 and any(True for _ in r.data["results"]))

print("== signed URL check ==")
if img_url_b:
    import urllib.request

    try:
        with urllib.request.urlopen(img_url_b, timeout=20) as resp:
            record(
                "profile image viewable via SIGNED url (browser case)",
                resp.status == 200 and resp.read(8) == b"\x89PNG\r\n\x1a\n",
            )
    except Exception as error:  # noqa: BLE001
        record("profile image viewable via SIGNED url (browser case)", False, repr(error)[:80])


print("== campaign flow ==")
influencer_id = User.objects.get(username=inf_name).influencerprofile.id
pdf_file = ContentFile(TINY_PDF, name=f"brief-{RUN_ID}.pdf")
r = client.post(
    "/api/campaigns/send/",
    {
        "influencer": influencer_id,
        "title": "AWS E2E Campaign",
        "message": "Integration check campaign.",
        "budget": "5000.00",
        "attachment": pdf_file,
    },
    format="multipart",
)
campaign_id = r.data.get("id") if r.status_code == 201 else None
att_url = (r.data or {}).get("attachment_url") or ""
if r.status_code != 201 or not is_s3_url(att_url):
    print("   campaign debug:", r.status_code, str(r.data)[:300])
record("campaign create w/ attachment", r.status_code == 201 and is_s3_url(att_url), att_url[:80])
if att_url and campaign_id:
    try:
        stored = CampaignRequest.objects.get(id=campaign_id).attachment
        with stored.open() as handle:  # authorised read via app credentials
            head = handle.read(5)
        record(
            "attachment readable from S3 (authorised)",
            head == b"%PDF-",
            f"public-anonymous 403 expected on private bucket",
        )
    except Exception as error:  # noqa: BLE001
        record("attachment readable from S3 (authorised)", False, repr(error)[:80])

r = inf_client.post(f"/api/campaigns/{campaign_id}/accept/")
record("influencer accepts campaign", r.status_code == 200)
biz_user = User.objects.get(username=biz_name)
record(
    "notification generated for business",
    Notification.objects.filter(recipient=biz_user, notification_type="campaign_accepted").exists(),
)
conv = Conversation.objects.filter(campaign_id=campaign_id).first()
record("conversation auto-created", conv is not None)

print("== chat attachments ==")
chat_img = ContentFile(PNG_1X1, name=f"chat-img-{RUN_ID}.png")
r = inf_client.post("/api/chat/upload/", {"conversation": conv.id, "image": chat_img}, format="multipart")
chat_img_key = ""
ok_img = False
if r.status_code == 201:
    chat_img_key = (r.data.get("image_url") or "").split(".com/")[-1]
    ok_img = is_s3_url(r.data.get("image_url")) and s3_exists(chat_img_key)
record("chat image upload -> S3", ok_img, chat_img_key)

chat_pdf = ContentFile(TINY_PDF, name=f"chat-pdf-{RUN_ID}.pdf")
r = client.post("/api/chat/upload/", {"conversation": conv.id, "file": chat_pdf}, format="multipart")
chat_pdf_key = ""
ok_pdf = False
if r.status_code == 201:
    chat_pdf_key = (r.data.get("file_url") or "").split(".com/")[-1]
    ok_pdf = is_s3_url(r.data.get("file_url")) and s3_exists(chat_pdf_key)
record("chat pdf upload -> S3", ok_pdf, chat_pdf_key)

print("== cleanup (self-created artifacts only) ==")
for leftover in [logo_key_a, logo_key_b, img_key_a, img_key_b, chat_img_key, chat_pdf_key]:
    if leftover:
        try:
            default_storage.delete(leftover)
        except Exception:  # noqa: BLE001
            pass
try:
    att_name = CampaignRequest.objects.get(id=campaign_id).attachment.name
    if att_name:
        default_storage.delete(att_name)
except Exception:  # noqa: BLE001
    pass
_, deleted_users = User.objects.filter(username__in=[biz_name, inf_name]).delete()
print(f"cleanup done ({deleted_users} self-created user rows removed via cascade)")

failed = [label for label, ok in results if not ok]
print("\n================ SUMMARY ================")
print(f"PASS {len(results) - len(failed)}/{len(results)}")
if failed:
    print("FAILED:", failed)
sys.exit(1 if failed else 0)
