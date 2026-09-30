"""Regression test for hosted HTTPS preview: login cookie must still be
Secure; SameSite=None, and /api/auth/me must succeed with that cookie.
"""
import os
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://nginx-config-tracker.preview.emergentagent.com"
).rstrip("/")
ADMIN_EMAIL = "admin@driftwatch.io"
ADMIN_PASSWORD = "admin123"


def test_https_login_sets_secure_samesite_none_cookie_and_me_ok():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text

    set_cookies = r.headers.get("set-cookie") or ""
    # Multi cookie header may be joined; requests exposes raw via r.raw only w/ stream.
    # Fallback: use r.cookies + inspect the concatenated Set-Cookie string.
    combined = ",".join(v for k, v in r.raw.headers.items() if k.lower() == "set-cookie") \
        if hasattr(r, "raw") and r.raw else set_cookies

    # We only look at the access_token cookie's flags.
    lowered = combined.lower()
    assert "access_token=" in lowered, combined
    # Extract the access_token cookie chunk
    chunk = [c for c in combined.split(",") if "access_token=" in c.lower()]
    chunk_str = ";".join(chunk).lower()
    assert "secure" in chunk_str, f"missing Secure on HTTPS: {chunk_str}"
    assert "samesite=none" in chunk_str, f"missing SameSite=None on HTTPS: {chunk_str}"
    assert "httponly" in chunk_str, f"missing HttpOnly: {chunk_str}"

    # Follow up /me with same session cookies should be authorized
    me = s.get(f"{BASE_URL}/api/auth/me")
    assert me.status_code == 200, me.text
    assert me.json()["email"] == ADMIN_EMAIL
