"""Unit tests for auth.cookie_params() — verifies http vs https flag logic.

db.py reads MONGO_URL at import time, so we must load_dotenv() BEFORE
importing auth (which imports db).
"""
import os
import importlib
import sys
import pathlib

from dotenv import load_dotenv

# Load backend/.env so MONGO_URL/JWT_SECRET are set before importing db/auth.
BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
sys.path.insert(0, str(BACKEND_DIR))

import auth  # noqa: E402


def _reload_with_frontend(url: str):
    os.environ["FRONTEND_URL"] = url
    importlib.reload(auth)
    return auth.cookie_params()


def test_cookie_params_http_returns_lax_non_secure():
    params = _reload_with_frontend("http://localhost:8080")
    assert params == {"secure": False, "samesite": "lax"}, params


def test_cookie_params_http_ip_returns_lax_non_secure():
    params = _reload_with_frontend("http://192.168.1.10:3000")
    assert params == {"secure": False, "samesite": "lax"}, params


def test_cookie_params_https_returns_secure_none():
    params = _reload_with_frontend("https://drift.example.com")
    assert params == {"secure": True, "samesite": "none"}, params


def test_cookie_params_empty_defaults_to_lax_non_secure():
    os.environ["FRONTEND_URL"] = ""
    importlib.reload(auth)
    assert auth.cookie_params() == {"secure": False, "samesite": "lax"}


def teardown_module(module):
    # Restore the .env FRONTEND_URL so subsequent tests / server keep working.
    load_dotenv(BACKEND_DIR / ".env", override=True)
    importlib.reload(auth)
