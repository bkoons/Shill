"""Optional PSK mesh encryption (Phase 1.1): NaCl SecretBox over UDP datagrams."""
import base64
import json
from backend.app.core import security_config as sec

def _load_key():
    raw = (sec.MESH_PSK or "").strip()
    if not raw:
        return None
    try:
        key = bytes.fromhex(raw) if len(raw) == 64 else base64.b64decode(raw)
        return key if len(key) == 32 else None
    except Exception:
        return None

def is_enabled() -> bool:
    return _load_key() is not None

def seal(packet: dict) -> bytes:
    raw = json.dumps(packet, separators=(",", ":")).encode("utf-8")
    key = _load_key()
    if key is None:
        return raw
    from nacl.secret import SecretBox
    box = SecretBox(key)
    sealed = box.encrypt(raw)
    env = {"enc": "nacl-secretbox-v1",
           "nonce_b64": base64.b64encode(sealed.nonce).decode(),
           "ct_b64": base64.b64encode(sealed.ciphertext).decode()}
    return json.dumps(env, separators=(",", ":")).encode("utf-8")

def open_frame(data: bytes):
    key = _load_key()
    try:
        obj = json.loads(data.decode("utf-8"))
    except Exception:
        return None, "rejected"
    if isinstance(obj, dict) and obj.get("enc") == "nacl-secretbox-v1":
        if key is None:
            return None, "rejected"
        try:
            from nacl.secret import SecretBox
            raw = SecretBox(key).decrypt(base64.b64decode(obj["ct_b64"]), base64.b64decode(obj["nonce_b64"]))
            return json.loads(raw.decode("utf-8")), "encrypted"
        except Exception:
            return None, "rejected"
    if sec.MESH_REQUIRE_ENCRYPTION:
        return None, "rejected"
    return obj, "plaintext"
