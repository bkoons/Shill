import re

# Patterns redacted from logs / telemetry / API responses.
_REDACT_PATTERNS = [
    (re.compile(r"(?i)(private_key_hex['\"]?\s*[:=]\s*['\"]?)([0-9a-fA-F]{16,})"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(seed_phrase['\"]?\s*[:=]\s*['\"]?)([^'\",\n]{8,})"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(bearer_token['\"]?\s*[:=]\s*['\"]?)([A-Za-z0-9_\-]{16,})"), r"\1***REDACTED***"),
    (re.compile(r"shill_root_[0-9a-f]{16,}"), "shill_root_***REDACTED***"),
    (re.compile(r"vault1:[A-Za-z0-9+/=]{16,}"), "vault1:***REDACTED***"),
    (re.compile(r"(?i)(totp|secret_base32['\"]?\s*[:=]\s*['\"]?)([A-Z2-7=]{16,})"), r"\1***REDACTED***"),
    (re.compile(r"EQ[A-Za-z0-9_\-]{20,}"), lambda m: m.group(0)[:6] + "…REDACTED"),
]


def sanitize_for_log(text: str) -> str:
    if not text:
        return text
    out = text
    for pat, repl in _REDACT_PATTERNS:
        out = pat.sub(repl, out)
    return out


def sanitize_packet_for_telemetry(packet: dict) -> dict:
    """Shallow-copy a mesh packet with secret-bearing fields scrubbed for the admin feed."""
    if not isinstance(packet, dict):
        return packet
    scrubbed = dict(packet)
    for k in ("private_key_hex", "seed_phrase", "signature", "bearer_token", "secret_base32"):
        if k in scrubbed:
            scrubbed[k] = "***REDACTED***"
    msg = scrubbed.get("message")
    if isinstance(msg, dict):
        msg2 = dict(msg)
        for k in ("private_key_hex", "seed_phrase", "forensic_signature"):
            if k in msg2:
                msg2[k] = "***REDACTED***"
        scrubbed["message"] = msg2
    return scrubbed
