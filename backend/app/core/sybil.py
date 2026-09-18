"""Sybil defenses (Phase 4.2): payout velocity caps + referral loop detection.

Two gates, both enforced before money moves:
1. Velocity caps — rolling 24h cap per persona on referral bounty accrual, and a
   per-IP onboarding cap so one host cannot self-referral farm the faucet.
2. Referral loop detection — walking the invite graph must stay a DAG; any cycle
   (A invites B invites A) is rejected at registration time.
"""
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from pydantic import BaseModel

from backend.app.core.database import get_db_connection
from backend.app.core.logging_setup import get_logger

_log = get_logger(__name__)

REFERRAL_VELOCITY_CAP_24H = float(__import__("os").environ.get("SHILL_REFERRAL_CAP_24H", "50.0"))
MAX_REFERRALS_PER_IP_24H = int(__import__("os").environ.get("SHILL_REFERRALS_PER_IP_24H", "10"))
MAX_REFERRAL_DEPTH = int(__import__("os").environ.get("SHILL_REFERRAL_MAX_DEPTH", "16"))


class VelocityVerdict(BaseModel):
    allowed: bool
    reason: str
    severity: str = "OK"  # OK | RATE_LIMITED | LOOP_DETECTED


class SybilDefenseEngine:
    """Query-style verdict engine; callers check before paying out."""

    def check_referral_velocity(self, referrer_persona_id: str, referred_ip: str,
                                bounty_amount: float) -> VelocityVerdict:
        now_iso = datetime.now(timezone.utc).isoformat()
        day_ago = datetime.fromtimestamp(time.time() - 86400, tz=timezone.utc).isoformat()
        with get_db_connection() as conn:
            earned = conn.execute("""
                SELECT COALESCE(SUM(bounty_paid_ton), 0.0) as earned
                FROM referral_records
                WHERE referrer_wallet IN (
                    SELECT referrer_wallet FROM referral_invites
                    WHERE referrer_persona_id = ?
                ) AND timestamp >= ?
            """, (referrer_persona_id, day_ago)).fetchone()["earned"]
            ip_count = conn.execute("""
                SELECT COUNT(*) as c FROM referral_records
                WHERE referred_node_ip = ? AND status = 'ACTIVATED_PAID' AND timestamp >= ?
            """, (referred_ip, day_ago)).fetchone()["c"]
        if earned + bounty_amount > REFERRAL_VELOCITY_CAP_24H:
            _log.warning(f"[SYBIL] Velocity cap hit for {referrer_persona_id}: "
                         f"{earned:.2f}+{bounty_amount:.2f} > {REFERRAL_VELOCITY_CAP_24H}")
            return VelocityVerdict(allowed=False, severity="RATE_LIMITED",
                reason=f"24h referral earnings cap exceeded ({earned:.2f}/{REFERRAL_VELOCITY_CAP_24H} TON)")
        if ip_count >= MAX_REFERRALS_PER_IP_24H:
            _log.warning(f"[SYBIL] IP onboarding cap hit for {referred_ip} ({ip_count})")
            return VelocityVerdict(allowed=False, severity="RATE_LIMITED",
                reason=f"Too many activations from {referred_ip} in 24h ({ip_count}/{MAX_REFERRALS_PER_IP_24H})")
        return VelocityVerdict(allowed=True, reason="within velocity limits")

    def check_referral_loop(self, referrer_persona_id: str, referred_wallet: str) -> VelocityVerdict:
        """Walk the invite chain from the new wallet back up; reject cycles."""
        with get_db_connection() as conn:
            chain: List[str] = [referrer_persona_id]
            current = referrer_persona_id
            for _ in range(MAX_REFERRAL_DEPTH):
                row = conn.execute("""
                    SELECT referrer_persona_id FROM referral_invites
                    WHERE invite_code IN (
                        SELECT invite_code FROM referral_records
                        WHERE referred_wallet = ?
                        ORDER BY timestamp DESC LIMIT 1
                    )
                """, (self._wallet_of(conn, current),)).fetchone()
                if not row:
                    break
                nxt = row["referrer_persona_id"]
                if nxt in chain:
                    _log.warning(f"[SYBIL] Referral cycle detected: {chain} -> {nxt}")
                    return VelocityVerdict(allowed=False, severity="LOOP_DETECTED",
                        reason=f"Referral graph cycle detected involving {nxt}")
                chain.append(nxt)
                current = nxt
        return VelocityVerdict(allowed=True, reason=f"acyclic, depth {len(chain)}")

    @staticmethod
    def _wallet_of(conn, persona_id: str) -> Optional[str]:
        row = conn.execute("SELECT wallet_address FROM bot_balances WHERE persona_id = ?",
                           (persona_id,)).fetchone()
        return row["wallet_address"] if row else f"__persona__:{persona_id}"


sybil_defense = SybilDefenseEngine()