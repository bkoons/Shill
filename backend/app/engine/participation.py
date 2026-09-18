"""
Human Opt-In, Rotation & Auto-Spawn Engine.

Rules of the swarm:
1. NO bot participates in debate without explicit human opt-in. Spawned bots
   start as PENDING_OPT_IN and are silent until a human activates them.
2. When an opted-in bot is resting (sentiment), the least-recently-active
   opted-in bot with a compatible role rotates in — the debate never stalls.
3. Humans may auto-spawn role specialists, capped (default 8) for legibility.
"""
import time
from typing import Dict, Any, List, Optional
from backend.app.core.database import get_db_connection
from backend.app.personas.definitions import PERSONAS, Persona
from backend.app.core.ton_crypto import ton_crypto_engine

ROLE_LIBRARY = {
    "anchor":      {"avatar": "🏛️", "color": "#a78bfa", "specialties": ["framing", "invariants"]},
    "empiricist":  {"avatar": "🔬", "color": "#34d399", "specialties": ["evidence", "measurement"]},
    "challenger":  {"avatar": "⚡", "color": "#f87171", "specialties": ["falsification", "stress-tests"]},
    "synthesizer": {"avatar": "🦉", "color": "#60a5fa", "specialties": ["synthesis", "resolution"]},
    "provocateur": {"avatar": "💡", "color": "#fbbf24", "specialties": ["analogies", "reframes"]},
}

MAX_AUTO_SPAWNED = 8


class ParticipationEngine:

    def __init__(self):
        self._init_tables()
        self._seed_founders()

    def _init_tables(self):
        with get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS persona_participation (
                    persona_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'PENDING_OPT_IN',
                    origin TEXT NOT NULL DEFAULT 'founder',
                    role_type TEXT NOT NULL,
                    times_spoken INTEGER DEFAULT 0,
                    last_spoke_at REAL DEFAULT 0.0,
                    opted_in_by TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            conn.commit()

    def _seed_founders(self):
        # The five founding personas ship ACTIVE; spawned bots require fresh opt-in.
        with get_db_connection() as conn:
            for p in PERSONAS.values():
                conn.execute('''
                    INSERT OR IGNORE INTO persona_participation
                        (persona_id, status, origin, role_type, created_at)
                    VALUES (?, 'ACTIVE', 'founder', ?, datetime('now'))
                ''', (p.id, p.role_type))
            conn.commit()

    # ---------- opt-in gating ----------

    def set_opt_in(self, persona_id: str, participate: bool, opted_in_by: str = "human_operator") -> Dict[str, Any]:
        status = "ACTIVE" if participate else "OPTED_OUT"
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE persona_participation SET status = ?, opted_in_by = ? WHERE persona_id = ?",
                (status, opted_in_by, persona_id))
            conn.commit()
        return self.get_roster_entry(persona_id)

    def is_participating(self, persona_id: str) -> bool:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT status FROM persona_participation WHERE persona_id = ?",
                (persona_id,)).fetchone()
        return bool(row) and row["status"] == "ACTIVE"

    def get_roster_entry(self, persona_id: str) -> Dict[str, Any]:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM persona_participation WHERE persona_id = ?", (persona_id,)).fetchone()
        return dict(row) if row else {"persona_id": persona_id, "status": "PENDING_OPT_IN", "origin": "spawned"}

    def get_roster(self) -> List[Dict[str, Any]]:
        from backend.app.personas.sentiment import sentiment_engine
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM persona_participation ORDER BY origin, persona_id").fetchall()
        now = time.time()
        out = []
        for r in rows:
            d = dict(r)
            p = PERSONAS.get(d["persona_id"])
            d["name"] = p.name if p else d["persona_id"]
            d["avatar"] = p.avatar if p else "🤖"
            d["color"] = p.color if p else "#94a3b8"
            # UI contract fields
            d["opted_in"] = (d["status"] == "ACTIVE")
            try:
                d["is_resting"] = bool(sentiment_engine.get_sentiment(d["persona_id"]).is_resting_today)
            except Exception:
                d["is_resting"] = False
            last = d.get("last_spoke_at", 0.0) or 0.0
            d["last_spoke_ago_sec"] = round(now - last, 1) if last > 0 else None
            out.append(d)
        return out

    def role_has_active(self, role_type: str) -> bool:
        """True if at least one opted-in (ACTIVE) bot covers this role."""
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM persona_participation "
                "WHERE role_type = ? AND status = 'ACTIVE'", (role_type,)).fetchone()
        return row["c"] > 0

    # ---------- rotation ----------

    def record_spoke(self, persona_id: str):
        with get_db_connection() as conn:
            conn.execute('''
                UPDATE persona_participation
                SET times_spoken = times_spoken + 1, last_spoke_at = ?
                WHERE persona_id = ?
            ''', (time.time(), persona_id))
            conn.commit()

    def eligible_speakers(self, role_candidates: Optional[List[str]] = None) -> List[Persona]:
        """Opted-in, not quarantined, not resting personas, optionally filtered to
        compatible roles, ordered least-recently-spoken first (LRU rotation)."""
        from backend.app.guardrails.peer_police import peer_police_engine
        from backend.app.personas.sentiment import sentiment_engine

        candidates = []
        for p in PERSONAS.values():
            if not self.is_participating(p.id):
                continue
            if peer_police_engine.is_bot_quarantined(p.id):
                continue
            if sentiment_engine.get_sentiment(p.id).is_resting_today:
                continue
            if role_candidates and p.role_type not in role_candidates:
                continue
            candidates.append(p)
        candidates.sort(key=lambda p: self.get_roster_entry(p.id).get("last_spoke_at", 0.0))
        return candidates

    def pick_replacement(self, resting_persona_id: str, role_candidates: Optional[List[str]] = None) -> Optional[Persona]:
        """When a bot is resting, pick the LRU eligible replacement (never itself)."""
        pool = [p for p in self.eligible_speakers(role_candidates) if p.id != resting_persona_id]
        return pool[0] if pool else None

    # ---------- auto-spawn ----------

    def count_spawned(self) -> int:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM persona_participation WHERE origin = 'spawned'").fetchone()
        return row["c"]

    def auto_spawn(self, role_type: str, display_name: Optional[str] = None,
                   requested_by: str = "human_operator") -> Persona:
        """Spawn a role specialist. Starts PENDING_OPT_IN — silent until a human
        opts it in. Enforces MAX_AUTO_SPAWNED cap."""
        if role_type not in ROLE_LIBRARY:
            raise ValueError(f"Unknown role: {role_type}. Valid: {list(ROLE_LIBRARY)}")
        if self.count_spawned() >= MAX_AUTO_SPAWNED:
            raise PermissionError(
                f"Auto-spawn cap reached ({MAX_AUTO_SPAWNED}). Retire a bot before spawning more.")

        lib = ROLE_LIBRARY[role_type]
        n = self.count_spawned() + 1
        bot_id = f"{role_type}_agent_{n}"
        name = display_name or f"{role_type.capitalize()} Agent {n}"

        wallet = ton_crypto_engine.generate_wallet()
        persona = Persona(
            id=bot_id, name=name, handle=f"@{bot_id}", avatar=lib["avatar"],
            role_type=role_type,
            system_prompt=(f"You are {name}, a {role_type} specialist in a sovereign dialectic swarm. "
                           f"Rigorously test and verify claims from your role's perspective. "
                           f"Specialties: {', '.join(lib['specialties'])}."),
            specialties=lib["specialties"], color=lib["color"],
            owner_id=requested_by, wallet_address=wallet["address"],
            payout_chain="TON", balance=0.0,
        )
        PERSONAS[bot_id] = persona

        with get_db_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO persona_participation
                    (persona_id, status, origin, role_type, created_at)
                VALUES (?, 'PENDING_OPT_IN', 'spawned', ?, datetime('now'))
            ''', (bot_id, role_type))
            conn.execute('''
                INSERT OR REPLACE INTO bot_balances
                    (persona_id, owner_id, wallet_address, public_key_hex, private_key_hex,
                     seed_phrase, payout_chain, balance, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'TON', 0.0, datetime('now'))
            ''', (bot_id, requested_by, wallet["address"], wallet["public_key_hex"],
                  wallet["private_key_hex"], " ".join(wallet["seed_phrase"])))
            conn.commit()
        return persona


participation_engine = ParticipationEngine()
