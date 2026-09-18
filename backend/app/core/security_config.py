"""Central security + deployment configuration (env-driven, no hardcoded secrets)."""
import os

def _get(key: str, default: str = "") -> str:
    v = os.getenv(key, default)
    return v.strip() if isinstance(v, str) else v

# --- Superuser auth (Phase 0/1: no committed defaults in production) ---
SUPERUSER_USERNAME = _get("SHILL_ROOT_USER", "root_admin")
# PBKDF2 hash is derived at runtime from SHILL_ROOT_PASSWORD; dev fallback only.
SUPERUSER_SALT = _get("SHILL_SALT", "SHILL_SECURE_SALT_984729384729")
_DEV_PASSWORD = _get("SHILL_ROOT_PASSWORD", "")
SUPERUSER_TOTP_SECRET = _get("SHILL_TOTP_SECRET", "")

# --- Mesh encryption (Phase 1.1): pre-shared key for SecretBox ---
# 32-byte key, base64 or hex in MESH_PSK. Empty => plaintext with warning (dev LAN only).
MESH_PSK = _get("SHILL_MESH_PSK", "")
MESH_REQUIRE_ENCRYPTION = _get("SHILL_MESH_REQUIRE_ENCRYPTION", "0") == "1"

# --- Key vault (Phase 1.2): Fernet envelope passphrase ---
VAULT_PASSPHRASE = _get("SHILL_VAULT_PASSPHRASE", "")

# --- CORS allowlist (Phase 1.4) ---
_cors_raw = _get("SHILL_CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]

# --- Rate limits (Phase 1.4) ---
RATE_CHAT_PER_MIN = _get("SHILL_RATE_CHAT", "30/minute")
RATE_SWAP_PER_MIN = _get("SHILL_RATE_SWAP", "20/minute")
RATE_IMPORT_PER_MIN = _get("SHILL_RATE_IMPORT", "10/minute")

SENSITIVE_KEYS = ("private_key_hex", "private_key", "seed_phrase", "seedphrase", "mnemonic")

def redact(obj):
    """Recursively redact sensitive key material from logs/telemetry."""
    if isinstance(obj, dict):
        return {k: ("***REDACTED***" if k in SENSITIVE_KEYS else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj
