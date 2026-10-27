"""Check inactive-account login now returns friendly 400 (not 500)."""

import json
import urllib.error
import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/login/",
    data=json.dumps({"username": "prasadll", "password": "definitely-wrong-or-right"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        print("status:", response.status)
except urllib.error.HTTPError as error:
    print("status:", error.code)
    print("body :", error.read().decode()[:250])
