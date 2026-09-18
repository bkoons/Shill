import os
import base64
import hashlib
from typing import Optional

try:
    from cryptography.fernet import Fernet, InvalidToken
    _FERNET_AVAILABLE = True
except Exception:
    Fernet = None  # type: ignore
    InvalidToken = Exception  # type: ignore
    _FERNET_AVAILABLE = False


def _derive_fernet_key(passphrase: str, salt: bytes = b"shill-vault-v1") -> bytes:
    dk = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, 200_000, dklen=32)
    return base64.urlsafe_b64encode(dk)


def _vault_passphrase() -> Optional[str]:
    return os.getenv("SHILL_VAULT_KEY") or os.getenv("SHILL_VAULT_PASSPHRASE")


def is_vault_configured() -> bool:
    return bool(_vault_passphrase()) and _FERNET_AVAILABLE


def _fernet():
    pw = _vault_passphrase()
    if not pw:
        raise RuntimeError("SHILL_VAULT_KEY not set")
    if not _FERNET_AVAILABLE:
        raise RuntimeError("cryptography package not installed")
    salt_hex = os.getenv("SHILL_VAULT_SALT", "")
    salt = bytes.fromhex(salt_hex) if salt_hex else b"shill-vault-v1"
    return Fernet(_derive_fernet_key(pw, salt))


def encrypt_secret(plaintext: Optional[str]) -> str:
    if not plaintext:
        return ""
    if plaintext.startswith("enc:v1:"):
        return plaintext
    if not is_vault_configured():
        return f"plain:v1:{plaintext}"
    token = _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return f"enc:v1:{token}"


def decrypt_secret(stored: Optional[str]) -> str:
    if not stored:
        return ""
    if stored.startswith("enc:v1:"):
        token = stored[len("enc:v1:"):]
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    if stored.startswith("plain:v1:"):
        return stored[len("plain:v1:"):]
    return stored


def is_encrypted(stored: Optional[str]) -> bool:
    return bool(stored and stored.startswith("enc:v1:"))


seal_secret = encrypt_secret
open_secret = decrypt_secret
