import hashlib
import hmac
import time
import secrets
import pyotp
from typing import Dict, Any, Optional
from pydantic import BaseModel

# ----------------------------------------------------------------------------
# Superuser auth (Phase 0 fix): NO committed credentials.
# Production: set SHILL_ROOT_PASSWORD (or SHILL_ROOT_PASSWORD_HASH),
# SHILL_ROOT_SALT, SHILL_TOTP_SECRET. Dev fallback generates a warning and uses
# a random per-boot password so tests/LAN never depend on a committed secret.
# ----------------------------------------------------------------------------
from backend.app.core import security_config as sec

SUPERUSER_USERNAME = sec.SUPERUSER_USERNAME or "root_admin"
SUPERUSER_SALT = sec.SUPERUSER_SALT

# Active authenticated session bearer tokens: token -> expires_at
ACTIVE_SESSIONS: Dict[str, float] = {}

_PASSWORD_HASH_CACHE: Optional[str] = None
_BOOTSTRAP_PASSWORD: Optional[str] = None


def _resolve_password_hash() -> str:
    """PBKDF2 hash (100k iters) of SHILL_ROOT_PASSWORD; random dev fallback once."""
    global _PASSWORD_HASH_CACHE, _BOOTSTRAP_PASSWORD
    if _PASSWORD_HASH_CACHE:
        return _PASSWORD_HASH_CACHE
    env_hash = (sec._get("SHILL_ROOT_PASSWORD_HASH", "") or "").strip()
    if env_hash:
        _PASSWORD_HASH_CACHE = env_hash
        return _PASSWORD_HASH_CACHE
    pwd = sec._DEV_PASSWORD
    if not pwd:
        pwd = "dev-" + secrets.token_urlsafe(18)
        print("=" * 72)
        print("[AUTH BOOTSTRAP] SHILL_ROOT_PASSWORD unset — random DEV password (use env in prod):")
        print(f"[AUTH BOOTSTRAP]   user:     {SUPERUSER_USERNAME}")
        print(f"[AUTH BOOTSTRAP]   password: {pwd}")
        print("=" * 72)
    _BOOTSTRAP_PASSWORD = pwd
    _PASSWORD_HASH_CACHE = hashlib.pbkdf2_hmac(
        "sha256", pwd.encode("utf-8"), sec.SUPERUSER_SALT.encode("utf-8"), 100000
    ).hex()
    return _PASSWORD_HASH_CACHE


def _resolve_totp_secret() -> str:
    if sec.SUPERUSER_TOTP_SECRET:
        return sec.SUPERUSER_TOTP_SECRET
    print("[AUTH] WARNING: SHILL_TOTP_SECRET unset — random per-boot TOTP secret.")
    return pyotp.random_base32()


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str  # 6-digit rolling 2FA code

class SuperuserAuthManager:
    """
    Super-Strict 2FA Security Backend:
    1. PBKDF2 with 100,000 iterations for password verification.
    2. RFC 6238 Time-based One-Time Password (TOTP) algorithm.
    3. Rate-limited constant-time comparisons to prevent timing attacks.
    4. Ephemeral cryptographic session tokens.
    """

    def __init__(self):
        self.totp = pyotp.TOTP(_resolve_totp_secret(), interval=30)
        self.failed_attempts = 0
        self.last_failed_time = 0.0

    def verify_credentials(self, username: str, password: str, totp_code: str) -> Optional[str]:
        # Simple lockout defense: if 5 failed attempts within 60s, rate limit
        now = time.time()
        if self.failed_attempts >= 5 and (now - self.last_failed_time) < 60:
            raise PermissionError("Too many failed authentication attempts. Locked for 60 seconds.")

        # Constant time username check
        if not hmac.compare_digest(username, sec.SUPERUSER_USERNAME):
            self._record_failure()
            return None

        # Verify password hash (runtime-derived from env, 100k iterations)
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            sec.SUPERUSER_SALT.encode('utf-8'),
            100000
        ).hex()

        if not hmac.compare_digest(computed_hash, _resolve_password_hash()):
            self._record_failure()
            return None

        # Verify RFC 6238 TOTP 2FA code (permits 1 timestep skew for clock drift)
        clean_code = totp_code.strip().replace(" ", "")
        if not self.totp.verify(clean_code, valid_window=1):
            self._record_failure()
            return None

        # Success: reset failures and issue secure token (valid for 4 hours)
        self.failed_attempts = 0
        session_token = f"shill_root_{secrets.token_hex(32)}"
        ACTIVE_SESSIONS[session_token] = now + (4 * 3600)
        return session_token

    def is_session_valid(self, token: Optional[str]) -> bool:
        if not token:
            return False
        expires_at = ACTIVE_SESSIONS.get(token)
        if not expires_at:
            return False
        if time.time() > expires_at:
            del ACTIVE_SESSIONS[token]
            return False
        return True

    def get_provisioning_uri(self) -> str:
        return self.totp.provisioning_uri(name="root_admin", issuer_name="Shill-Sovereign-P2P")

    def get_current_totp_for_testing(self) -> str:
        return self.totp.now()

    def _record_failure(self):
        self.failed_attempts += 1
        self.last_failed_time = time.time()

superuser_auth = SuperuserAuthManager()
