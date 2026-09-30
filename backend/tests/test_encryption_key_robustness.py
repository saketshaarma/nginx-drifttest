"""Regression tests for db._load_fernet ENCRYPTION_KEY robustness fix.

The user's crash reproduced when ENCRYPTION_KEY was the placeholder
'change-me-to-a-fernet-key' — Fernet(...) raised at import so the backend
never came up. The fix makes _load_fernet() accept ANY string, using a
valid Fernet key as-is and deriving a deterministic one otherwise.
"""
import importlib
import os
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# db.py reads MONGO_URL at import time — ensure .env is loaded first
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def restore_env():
    """Snapshot ENCRYPTION_KEY and reload db module on teardown."""
    original = os.environ.get("ENCRYPTION_KEY")
    yield
    if original is None:
        os.environ.pop("ENCRYPTION_KEY", None)
    else:
        os.environ["ENCRYPTION_KEY"] = original
    import db  # noqa: F401
    importlib.reload(db)


def _reload_db():
    if "db" in sys.modules:
        return importlib.reload(sys.modules["db"])
    import db
    return db


def test_invalid_placeholder_key_does_not_crash_and_roundtrips(restore_env):
    os.environ["ENCRYPTION_KEY"] = "change-me-to-a-fernet-key"
    db = _reload_db()
    # Encrypt/decrypt round-trip must work
    token = db.encrypt_secret("ssh-pw")
    assert isinstance(token, str) and token
    assert db.decrypt_secret(token) == "ssh-pw"


def test_valid_fernet_key_used_as_is(restore_env):
    real_key = Fernet.generate_key().decode()
    os.environ["ENCRYPTION_KEY"] = real_key
    db = _reload_db()
    # Round-trip works
    token = db.encrypt_secret("hello")
    assert db.decrypt_secret(token) == "hello"
    # Verify the raw key is used as-is: an independent Fernet(real_key) must
    # decrypt what the module encrypted.
    independent = Fernet(real_key.encode("utf-8"))
    assert independent.decrypt(token.encode("utf-8")).decode("utf-8") == "hello"


def test_empty_encryption_key_still_yields_working_fernet(restore_env):
    os.environ["ENCRYPTION_KEY"] = ""
    db = _reload_db()
    token = db.encrypt_secret("secret-value")
    assert db.decrypt_secret(token) == "secret-value"


def test_arbitrary_passphrase_is_deterministic(restore_env):
    """Same passphrase across reloads should decrypt previously encrypted data."""
    os.environ["ENCRYPTION_KEY"] = "my-passphrase-not-fernet"
    db = _reload_db()
    token = db.encrypt_secret("payload-x")
    # Reload again with same key — must still decrypt
    db2 = _reload_db()
    assert db2.decrypt_secret(token) == "payload-x"
