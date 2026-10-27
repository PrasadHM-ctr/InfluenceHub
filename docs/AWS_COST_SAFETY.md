# InfluenceHub — AWS Cost Safety Guide

> **Honest disclaimer:** this project is *designed* for AWS Free Tier
> eligibility and strong cost controls, but **AWS does not guarantee that any
> usage is free**. Free Tier eligibility depends on your account type, region,
> current AWS pricing, and how much you use the app. Always verify pricing in
> your own [AWS Billing console](https://console.aws.amazon.com/billing/) and
> set up a **Billing alarm** (a budget alert) as an extra safety net.

---

## 1. Which AWS services are used, and why

| Service | Used for | Why it is needed | Where configured |
|---|---|---|---|
| **S3** (one private bucket) | Profile images, business logos, campaign attachments, chat attachments | Durable object storage; PostgreSQL only stores file paths/references, never binary data | `infrastructure/terraform/s3.tf`, `backend/config/storages.py` |
| **SES** (optional) | Transactional verification codes + resends only | Email delivery for the existing OTP signup flow. No marketing/bulk/newsletter sending exists in the codebase | `infrastructure/terraform/ses.tf`, `backend/config/email_backends.py` |
| **IAM** (one user, inline policy) | Least-privilege runtime permissions (`s3:GetObject/PutObject/DeleteObject`, `ses:SendEmail`) | The app must never be able to create infrastructure or touch other services | `infrastructure/terraform/iam.tf` |

### Explicitly NOT used (and refused by design)

EC2 · RDS · NAT Gateway · Load Balancer · CloudFront · Lambda · API Gateway ·
ECS/Fargate · EKS · ElastiCache · OpenSearch · SNS/SMS OTP · Cognito.

The Django API + PostgreSQL + Redis run wherever you host them yourself
(local machine / Docker); AWS is only storage + email.

---

## 2. Run the whole project locally at $0 AWS usage

Both AWS integrations are **off by default** in `backend/.env`:

```env
USE_S3=False    # uploads go to backend/media/ on disk
USE_SES=False   # verification emails print to the runserver console
```

With those defaults the application makes **zero calls to AWS**: no storage
requests, no emails, nothing billable. All features work identically — the
only difference is where files land and where emails print.

Enable AWS only when you specifically want to test it:

```env
USE_S3=True                 # uploads now go to the S3 bucket
AWS_STORAGE_BUCKET_NAME=...
AWS_S3_REGION_NAME=ap-south-1

USE_SES=True                # emails now go through SES
AWS_SES_REGION_NAME=ap-south-1
AWS_SES_FROM_EMAIL=no-reply@your-verified-address
```

Credentials are read from the normal environment/AWS chain — they are never
hardcoded anywhere in this repository.

---

## 3. Built-in cost controls

### Upload limits (application-enforced)

Every upload passes `backend/config/validators.py` **before** touching S3:

| Upload type | Max size | Allowed types |
|---|---|---|
| Influencer profile image | 5 MB | JPG, JPEG, PNG, WEBP |
| Business logo | 5 MB | JPG, JPEG, PNG, WEBP |
| Campaign attachment | 10 MB | PDF (images also allowed via the image path) |
| Chat attachment | 10 MB | Images (JPG/JPEG/PNG/WEBP) or PDF |

Everything else is rejected with a 400 — no exceptions.

### Storage-growth guards

* Replacing a logo/profile photo **deletes the old object** from storage
  (`config/media_cleanup.py`) so orphaned files never accumulate.
* A conversation may hold at most `CHAT_MAX_ATTACHMENTS_PER_CONVERSATION`
  stored attachments (default **200**, tunable in `.env`; `0` disables).
* One profile = one logo/photo field; one campaign = one attachment. There is
  no endpoint that lets users upload arbitrary extra files.
* DRF throttling (`ANON/USER/AUTH/UPLOAD_THROTTLE_RATE`) caps request volume,
  which indirectly caps upload attempts.

### S3 bucket posture (Terraform)

* **One** bucket total — no per-user buckets, no replication targets.
* Fully **private**: all four Block-Public-Access settings +
  `BucketOwnerEnforced`. Image display goes through Django URLs; we do **not**
  make objects public to fix display issues.
* SSE-S3 encryption (no KMS key charges).
* Versioning **off** by default (overwrites would double billed bytes).
* **No** Intelligent-Tiering, Storage-Class Analytics, Inventory lists,
  cross-region replication, transfer acceleration, or lifecycle transitions.
* The single lifecycle rule aborts incomplete multipart uploads after 7 days
  so failed uploads can't silently bill forever.

### Email controls

* Only two email flows exist: **verification code** and **resend code**.
  Both are rate-limited (`AUTH_THROTTLE_RATE`, default 20/min) and the code
  expires in 15 minutes.
* No bulk, scheduled, marketing or digest emailing exists anywhere in the app.
* No SMS OTP, no SNS, no paid phone services.

---

## 4. How to check your AWS billing

1. Open <https://console.aws.amazon.com/billing/>.
2. **Bills** → month-to-date per service (expect only tiny S3/SES rows when
   enabled, and empty rows when `USE_S3=False`/`USE_SES=False`).
3. **Budgets → Create budget** → e.g. "Zero-spend" or a small monthly cap
   with email alerts at 50%/80%/100%. Best protection against surprises.
4. Optional: **Cost Explorer** for daily S3 request counts.
5. Check **Free Tier usage alerts** in the Billing console.

If you ever see an unexpected service in Bills: stop the app, review
`terraform plan`, and investigate before continuing.

---

## 5. Terraform workflow (read before running)

All infra lives in `infrastructure/terraform/` and creates **only**
bucket + security config + CORS + IAM policy + optional SES identity.

```bash
cd infrastructure/terraform

# 0) Authenticate first — credentials NEVER go into these files:
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...      # PowerShell: $env:AWS_ACCESS_KEY_ID="..."

# 1) Copy and edit variables (unique bucket name, verified sender):
cp terraform.tfvars.example terraform.tfvars

# 2) ALWAYS inspect the plan. Read every line:
terraform init
terraform plan

# 3) The plan may ONLY contain:
#      aws_s3_bucket.media,
#      aws_s3_bucket_public_access_block.media,
#      aws_s3_bucket_ownership_controls.media,
#      aws_s3_bucket_server_side_encryption_configuration.media,
#      aws_s3_bucket_versioning.media,
#      aws_s3_bucket_lifecycle_configuration.media,
#      aws_s3_bucket_cors_configuration.media,
#      aws_ses_email_identity.from,
#      aws_iam_user.app, aws_iam_user_policy.app
#    Anything else → STOP. Do not apply.

# 4) Only after a clean review:
terraform apply

# NEVER run `terraform destroy` unless you truly mean to delete everything.
```

Access keys are **not** created by Terraform (secrets must stay out of state).
After applying, create the runtime key yourself and put it in `backend/.env`:

```bash
aws iam create-access-key --user-name influencehub-app
```

---

## 6. Credential hygiene checklist

- [x] No credentials in source code, Terraform, docs, `.env.example`, or Git
- [x] `backend/.env`, `*.tfvars`, and state files are git-ignored
- [ ] IAM user has only its inline least-privilege policy (no groups/admin)
- [ ] Access keys rotated if ever exposed (screenshot, chat, logs)
- [ ] Billing alarm active

## 7. Disabling AWS again later

Flip both flags back and restart Django — nothing else needed:

```env
USE_S3=False
USE_SES=False
```

Existing DB rows keep working because local media serving is already wired
for `DEBUG=true` (`/media/`). Files uploaded while S3 was enabled remain in
the bucket until you remove them via the console.

---

## 8. Current deployment status (live)

| Item | Value |
|---|---|
| S3 bucket | `influencehub-media-909762691220` (ap-south-1) — private, BPA all-on, BucketOwnerEnforced, AES256, versioning suspended, multipart-abort lifecycle |
| App IAM user | `influencehub-app` — inline policy `influencehub-app-least-privilege` only (ListBucket/GetObject/PutObject/DeleteObject + SendEmail) |
| Terraform | applied; `terraform plan` reports "No changes" |
| SES identity | **pending** — set `create_ses_identity = true` + your sender address in `terraform.tfvars`, apply, then click the verification email AWS sends you |
| Verification scripts | `backend/aws_e2e_check.py` (full S3 E2E), `backend/aws_ses_probe.py`, `backend/aws_local_mode_probe.py` |

Re-run any probe at any time with the backend venv python.


