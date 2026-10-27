"""Flip USE_SES on and set the verified sender in backend/.env (secrets kept)."""

from pathlib import Path

env_path = Path(__file__).resolve().parent / ".env"
lines = env_path.read_text(encoding="utf-8").splitlines()

updated = []
found_from = False
for line in lines:
    if line.startswith("USE_SES="):
        updated.append("USE_SES=True")
    elif line.startswith("AWS_SES_FROM_EMAIL="):
        updated.append("AWS_SES_FROM_EMAIL=prasadhm439@gmail.com")
    elif line.startswith("DEFAULT_FROM_EMAIL="):
        updated.append("DEFAULT_FROM_EMAIL=InfluenceHub <prasadhm439@gmail.com>")
        found_from = True
    else:
        updated.append(line)

if not found_from:
    updated.append("DEFAULT_FROM_EMAIL=InfluenceHub <prasadhm439@gmail.com>")

env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
print("env updated:")
for line in updated:
    if line.startswith(("USE_SES", "AWS_SES_FROM_EMAIL", "USE_S3")):
        print(" ", line)
