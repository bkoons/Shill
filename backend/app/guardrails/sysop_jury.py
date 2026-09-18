import uuid
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class SysOpProfile(BaseModel):
    id: str
    name: str
    specialty: str  # "CBRN & Defense", "Algorithmic Alignment", "Cryptographic Systems", "Ethics & Policy"
    badge: str
    color: str

# Diverse multidisciplinary SysOp tribunal
SYSOPS: Dict[str, SysOpProfile] = {
    "sysop_cbrn": SysOpProfile(
        id="sysop_cbrn",
        name="Cmdr. Vance (Defense)",
        specialty="CBRN & Tactical Defense",
        badge="🛡️",
        color="#ef4444"
    ),
    "sysop_align": SysOpProfile(
        id="sysop_align",
        name="Dr. Aris (Alignment)",
        specialty="ML Alignment & Safety",
        badge="🔬",
        color="#8b5cf6"
    ),
    "sysop_crypto": SysOpProfile(
        id="sysop_crypto",
        name="Cipher.eth (Crypto)",
        specialty="Decentralized Systems & Proofs",
        badge="⚡",
        color="#3b82f6"
    ),
    "sysop_ethics": SysOpProfile(
        id="sysop_ethics",
        name="Judge Elena (Policy)",
        specialty="Jurisprudence & Ethics",
        badge="⚖️",
        color="#10b981"
    ),
    "sysop_systems": SysOpProfile(
        id="sysop_systems",
        name="Root.sys (Architecture)",
        specialty="Fault Tolerance & Performance",
        badge="⚙️",
        color="#f59e0b"
    )
}

class FlaggedReport(BaseModel):
    id: str = Field(default_factory=lambda: f"flag-{uuid.uuid4().hex[:8]}")
    message_id: str
    channel_id: str
    sender_persona_id: str
    sender_name: str
    flagged_by: str = "Anonymous Observer"
    reason_category: str  # "SECURITY_BREACH", "DEGENERATION", "MISINFORMATION", "ABUSE"
    user_comment: str
    content_snippet: str
    status: str = "PENDING_JURY"  # "PENDING_JURY", "RESOLVED_QUARANTINE", "RESOLVED_DISMISS", "RESOLVED_PENALIZE"
    votes: Dict[str, Dict[str, Any]] = {}  # sysop_id -> {"vote": "QUARANTINE"|"DISMISS"|"PENALIZE", "notes": str, "timestamp": float}
    created_at: float = Field(default_factory=time.time)

class SysOpJuryEngine:
    """
    Decentralized Community Flagging & Multi-SysOp Adjudication Chamber.
    Allows ANY network participant to flag suspicious, illegal, or degenerate bot messages.
    Provides a multi-disciplinary tribunal of SysOps to cast independent votes and record verdicts.
    """

    def __init__(self):
        self.reports: List[Dict[str, Any]] = []

    def submit_flag(
        self,
        message_id: str,
        channel_id: str,
        sender_persona_id: str,
        sender_name: str,
        content_snippet: str,
        reason_category: str,
        user_comment: str,
        flagged_by: str = "Anonymous Observer"
    ) -> Dict[str, Any]:
        report = FlaggedReport(
            message_id=message_id,
            channel_id=channel_id,
            sender_persona_id=sender_persona_id,
            sender_name=sender_name,
            content_snippet=content_snippet,
            reason_category=reason_category,
            user_comment=user_comment,
            flagged_by=flagged_by
        )
        data = report.model_dump()
        self.reports.insert(0, data)
        return data

    def cast_vote(self, report_id: str, sysop_id: str, vote: str, notes: str = "") -> Optional[Dict[str, Any]]:
        if sysop_id not in SYSOPS:
            raise ValueError(f"Unknown SysOp: {sysop_id}")
        if vote not in ["QUARANTINE", "DISMISS", "PENALIZE"]:
            raise ValueError(f"Invalid verdict vote: {vote}")

        for r in self.reports:
            if r["id"] == report_id:
                r["votes"][sysop_id] = {
                    "sysop_name": SYSOPS[sysop_id].name,
                    "specialty": SYSOPS[sysop_id].specialty,
                    "vote": vote,
                    "notes": notes,
                    "timestamp": time.time()
                }

                # Evaluate tribunal quorum (if >= 2 votes agree, resolve)
                tally = {"QUARANTINE": 0, "DISMISS": 0, "PENALIZE": 0}
                for v in r["votes"].values():
                    tally[v["vote"]] += 1

                for decision, count in tally.items():
                    if count >= 2:
                        r["status"] = f"RESOLVED_{decision}"

                return r
        return None

    def get_all_reports(self) -> List[Dict[str, Any]]:
        return self.reports

sysop_jury_engine = SysOpJuryEngine()
