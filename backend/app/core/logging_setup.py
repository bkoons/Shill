"""Central logging bootstrap (Phase 2.4): structured logger + secret redaction.

Usage:
    from backend.app.core.logging_setup import get_logger
    _log = get_logger(__name__)
    _log.info("...")

All messages pass through sanitize_for_log() so private keys, seed phrases,
TOTP secrets, and wallet addresses never land in logs. Level via SHILL_LOG_LEVEL.
"""
import logging
import sys

from backend.app.core.log_sanitize import sanitize_for_log

_CONFIGURED = False


class _RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_for_log(record.msg)
        if record.args:
            try:
                record.args = tuple(
                    sanitize_for_log(a) if isinstance(a, str) else a for a in record.args
                )
            except Exception:
                pass
        return True


def setup_logging(level: str = "") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    import os
    level_name = (level or os.getenv("SHILL_LOG_LEVEL", "INFO")).upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RedactingFilter())
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s", "%H:%M:%S"
    ))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level_name)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
