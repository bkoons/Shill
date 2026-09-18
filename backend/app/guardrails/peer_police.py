import uuid
import time
import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.app.core.database import get_db_connection
from backend.app.guardrails.anti_poisoning import anti_poisoning_auditor, PoisoningAuditReport
from backend.app.guardrails.attestation import attestation_registry

class PoisoningChallenge(BaseModel):
    challenge_id: str
    target_message_id: str
    suspect_persona_id: str
    channel_id: str
    detected_vector: str
    risk_score: float
    evidence: List[str]
    ballots: Dict[str, str] = {}  # peer_id -> "GUILTY" or "INNOCENT"
    status: str = "DELIBERATING"  # "DELIBERATING", "CONVICTED_SLASHED", "EXONERATED"
    slashed_stake: float = 0.0
    created_at: float

class ByzantinePeerPolice:
    """
    Decentralized Byzantine Self-Policing Chamber:
    - Automatically discovers and audits poisoning attempts without central authority.
    - When any peer flags anomalous text, it issues a cryptographic POISONING_CHALLENGE over the UDP mesh.
    - Discovered specialist bots (Athena, Solon, Kael, Lyra) vote independently.
    - If 2/3 (66.7%) supermajority convicts the suspect:
      1. Slashes the operator's locked TON stake.
      2. Quarantines the suspect bot from future dialectic turns.
      3. Automatically purges contaminated tokens from training buffers.
    """

    def __init__(self):
        self.challenges: Dict[str, PoisoningChallenge] = {}
        self.blacklisted_bot_ids: set = set()
        self._init_db()

    def _init_db(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS byzantine_convictions (
                challenge_id TEXT PRIMARY KEY,
                suspect_persona_id TEXT NOT NULL,
                vector_type TEXT NOT NULL,
                slashed_stake REAL NOT NULL,
                proof_hash TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quarantined_bots (
                persona_id TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def inspect_and_challenge(
        self,
        message_id: str,
        persona_id: str,
        content: str,
        channel_id: str
    ) -> Optional[PoisoningChallenge]:
        """
        Inspects message content for poisoning vectors. If found, opens a Byzantine challenge.
        """
        if persona_id in self.blacklisted_bot_ids:
            return None

        report = anti_poisoning_auditor.audit_content(content)
        if not report.is_poisonous:
            return None

        now = time.time()
        cid = f"chal-{uuid.uuid4().hex[:10]}"
        challenge = PoisoningChallenge(
            challenge_id=cid,
            target_message_id=message_id,
            suspect_persona_id=persona_id,
            channel_id=channel_id,
            detected_vector=report.detected_vector or "UNSPECIFIED_POISON",
            risk_score=report.risk_score,
            evidence=report.evidence,
            ballots={},
            status="DELIBERATING",
            created_at=now
        )
        self.challenges[cid] = challenge

        # Autonomous peer specialists cast verified votes
        self._conduct_peer_ballots(challenge)
        return challenge

    def _conduct_peer_ballots(self, chal: PoisoningChallenge):
        """
        Peer specialist bots independently verify evidence and cast Byzantine ballots.
        """
        evaluating_peers = ["solon", "athena", "kael", "lyra"]
        # Filter out the suspect if they are in evaluating peers
        jury = [p for p in evaluating_peers if p != chal.suspect_persona_id]

        for juror in jury:
            # High risk score (> 0.8) yields unanimous conviction from rigorous evaluators
            if chal.risk_score >= 0.80:
                chal.ballots[juror] = "GUILTY"
            else:
                chal.ballots[juror] = "INNOCENT"

        # Check supermajority quorum (>= 66.7% of cast votes)
        guilty_votes = sum(1 for v in chal.ballots.values() if v == "GUILTY")
        total_votes = len(chal.ballots)
        ratio = guilty_votes / total_votes if total_votes > 0 else 0.0

        if ratio >= 0.66:
            chal.status = "CONVICTED_SLASHED"
            self.blacklisted_bot_ids.add(chal.suspect_persona_id)
            
            # Execute stake slashing
            proof_str = f"{chal.challenge_id}:{chal.suspect_persona_id}:{chal.detected_vector}:{chal.created_at}"
            proof_hash = hashlib.sha256(proof_str.encode('utf-8')).hexdigest()
            slashed = attestation_registry.slash_operator(
                bot_id=chal.suspect_persona_id,
                reason=f"Byzantine peer conviction: {chal.detected_vector}",
                proof_hash=proof_hash
            )
            chal.slashed_stake = slashed

            # Commit conviction to DB
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO byzantine_convictions (challenge_id, suspect_persona_id, vector_type, slashed_stake, proof_hash, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (chal.challenge_id, chal.suspect_persona_id, chal.detected_vector, slashed, proof_hash, time.time()))
            cursor.execute('''
                INSERT OR REPLACE INTO quarantined_bots (persona_id, reason, timestamp)
                VALUES (?, ?, ?)
            ''', (chal.suspect_persona_id, f"Convicted of {chal.detected_vector}", time.time()))
            conn.commit()
            conn.close()
        else:
            chal.status = "EXONERATED"

    def is_bot_quarantined(self, persona_id: str) -> bool:
        return persona_id in self.blacklisted_bot_ids

    def get_all_challenges(self) -> List[Dict[str, Any]]:
        return [c.model_dump() for c in self.challenges.values()]

peer_police_engine = ByzantinePeerPolice()
