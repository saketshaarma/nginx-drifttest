import os
import base64
import hashlib
import logging
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]


def _load_fernet(raw_key: str) -> Fernet:
    """Accept ANY string as ENCRYPTION_KEY.

    If it's already a valid Fernet key, use it as-is. Otherwise derive a
    deterministic valid key from it, so a placeholder or passphrase can't
    crash the app on startup. The derivation is stable across restarts, so
    encrypted SSH passwords stay decryptable.
    """
    raw_key = (raw_key or "").strip()
    try:
        return Fernet(raw_key.encode("utf-8"))
    except Exception:
        logger.warning(
            "ENCRYPTION_KEY is not a valid Fernet key; deriving one from it. "
            "For production, generate a proper key: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


_fernet = _load_fernet(os.environ["ENCRYPTION_KEY"])


def encrypt_secret(value: str) -> str:
    if value is None:
        return None
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False
