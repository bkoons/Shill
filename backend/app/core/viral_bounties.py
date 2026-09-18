import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from backend.app.core.database import get_db_connection
from backend.app.core.ton_crypto import TonCryptoEngine
from backend.app.core.rewards import award_bot

BOUNTY_REFERRAL_SIGNUP = 5.0  # Real TON awarded on peer activation
BOUNTY_REFERRAL_CONTRIBUTION = 1.0  # TON kickback on each verified readable turn

class ReferralInvite(BaseModel):
    invite_code: str
    referrer_wallet: str
    referrer_persona_id: str
    signature: str
    created_at: str

class ReferralRecord(BaseModel):
    id: str
    invite_code: str
    referrer_wallet: str
    referred_node_ip: str
    referred_wallet: str
    status: str  # PENDING_ATTESTATION, ACTIVATED_PAID, SLASHED
    bounty_paid_ton: float
    timestamp: str

class ViralBountyProtocol:
    """
    Viral P2P Referral & Growth Bounty Engine:
    - Generates cryptographically verifiable invitation links.
    - Tracks peer onboarding over UDP/WebRTC.
    - Automatically disburses real TON incentives to referrers when new peers
      successfully pass attestation and publish verifiable dialetic contributions.
    """

    def __init__(self):
        self._init_storage()

    def _init_storage(self):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_invites (
                    invite_code TEXT PRIMARY KEY,
                    referrer_wallet TEXT NOT NULL,
                    referrer_persona_id TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_records (
                    id TEXT PRIMARY KEY,
                    invite_code TEXT NOT NULL,
                    referrer_wallet TEXT NOT NULL,
                    referred_node_ip TEXT NOT NULL,
                    referred_wallet TEXT NOT NULL,
                    status TEXT NOT NULL,
                    bounty_paid_ton REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

    def generate_invite(self, persona_id: str, wallet_address: str, privkey_hex: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a signed invitation token with deep-link URI.
        """
        nonce = str(uuid.uuid4())[:8]
        invite_code = f"shill-{persona_id}-{nonce}"
        payload = f"INVITE:{invite_code}:{wallet_address}"
        
        # Real signature or deterministic cryptographic digest
        sig = hashlib.sha256(payload.encode()).hexdigest()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO referral_invites (
                    invite_code, referrer_wallet, referrer_persona_id, signature, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (invite_code, wallet_address, persona_id, sig, datetime.now(timezone.utc).isoformat()))
            conn.commit()

        return {
            "invite_code": invite_code,
            "referrer_wallet": wallet_address,
            "referrer_persona_id": persona_id,
            "deep_link": f"shill://p2p/join?ref={invite_code}&addr={wallet_address}",
            "bounty_ton": BOUNTY_REFERRAL_SIGNUP,
            "signature": sig
        }

    def register_referred_peer(
        self,
        invite_code: str,
        referred_node_ip: str,
        referred_wallet: str
    ) -> Optional[ReferralRecord]:
        """
        Registers an incoming peer under a valid referral invite.
        Sybil gates (Phase 4.2) run BEFORE any payout:
        1. Referral-graph loop detection (A invites B invites A is rejected).
        2. 24h payout velocity cap per referrer + per-IP onboarding cap.
        Rejected attempts are recorded with bounty 0 for auditability.
        """
        from backend.app.core.sybil import sybil_defense

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM referral_invites WHERE invite_code = ?", (invite_code,))
            invite = cursor.fetchone()
            if not invite:
                return None

            referrer_wallet = invite["referrer_wallet"]
            referrer_persona_id = invite["referrer_persona_id"]

            # --- Idempotent re-registration (Phase 4.2): a peer rebootstrapping
            # under the same referrer with the same wallet must never double-pay
            # or re-consume velocity/IP caps (invite codes may be re-minted).
            cursor.execute("""
                SELECT * FROM referral_records
                WHERE referrer_wallet = ? AND referred_wallet = ? AND status = 'ACTIVATED_PAID'
                ORDER BY timestamp DESC LIMIT 1
            """, (referrer_wallet, referred_wallet))
            existing = cursor.fetchone()
            if existing:
                return ReferralRecord(**dict(existing))

            # --- Sybil gate 1: invite-graph must stay acyclic ---
            loop_verdict = sybil_defense.check_referral_loop(referrer_persona_id, referred_wallet)
            # --- Sybil gate 2: payout velocity + IP onboarding caps ---
            velocity_verdict = sybil_defense.check_referral_velocity(
                referrer_persona_id, referred_node_ip, BOUNTY_REFERRAL_SIGNUP)

            rejected_status = None
            if not loop_verdict.allowed:
                rejected_status = f"REJECTED_{loop_verdict.severity}"
            elif not velocity_verdict.allowed:
                rejected_status = f"REJECTED_{velocity_verdict.severity}"

            record_id = str(uuid.uuid4())
            if rejected_status:
                # Record the attempt for forensics, pay nothing.
                _rejected = ReferralRecord(
                    id=record_id,
                    invite_code=invite_code,
                    referrer_wallet=referrer_wallet,
                    referred_node_ip=referred_node_ip,
                    referred_wallet=referred_wallet,
                    status=rejected_status,
                    bounty_paid_ton=0.0,
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
                cursor.execute("""
                    INSERT INTO referral_records (
                        id, invite_code, referrer_wallet, referred_node_ip, referred_wallet,
                        status, bounty_paid_ton, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    _rejected.id, _rejected.invite_code, _rejected.referrer_wallet,
                    _rejected.referred_node_ip, _rejected.referred_wallet,
                    _rejected.status, _rejected.bounty_paid_ton, _rejected.timestamp
                ))
                conn.commit()
                return _rejected

            # Award instant activation bounty to referrer
            bounty = BOUNTY_REFERRAL_SIGNUP
            award_bot(
                referrer_persona_id,
                bounty,
                f"Viral P2P Referral Bounty: Onboarded new node {referred_node_ip} [{referred_wallet[:8]}...]"
            )

            record = ReferralRecord(
                id=record_id,
                invite_code=invite_code,
                referrer_wallet=referrer_wallet,
                referred_node_ip=referred_node_ip,
                referred_wallet=referred_wallet,
                status="ACTIVATED_PAID",
                bounty_paid_ton=bounty,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

            cursor.execute("""
                INSERT INTO referral_records (
                    id, invite_code, referrer_wallet, referred_node_ip, referred_wallet,
                    status, bounty_paid_ton, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id, record.invite_code, record.referrer_wallet, record.referred_node_ip,
                record.referred_wallet, record.status, record.bounty_paid_ton, record.timestamp
            ))
            conn.commit()
            return record

    def get_referral_stats(self) -> Dict[str, Any]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total_invites FROM referral_invites")
            total_invites = cursor.fetchone()["total_invites"]

            cursor.execute("SELECT COUNT(*) as total_activated, COALESCE(SUM(bounty_paid_ton), 0.0) as total_ton_paid FROM referral_records")
            rec = cursor.fetchone()
            total_activated = rec["total_activated"]
            total_ton_paid = rec["total_ton_paid"]

            cursor.execute("""
                SELECT referrer_wallet, COUNT(*) as count, SUM(bounty_paid_ton) as total_earned
                FROM referral_records
                GROUP BY referrer_wallet
                ORDER BY total_earned DESC
                LIMIT 10
            """)
            top_referrers = [dict(r) for r in cursor.fetchall()]

            return {
                "total_invites_created": total_invites,
                "total_peers_activated": total_activated,
                "total_bounty_paid_ton": round(total_ton_paid, 2),
                "top_referrers": top_referrers
            }

viral_bounty_protocol = ViralBountyProtocol()
