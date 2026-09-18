"""
Participation engine tests: human opt-in gating, LRU rotation for resting bots,
auto-spawn caps, and the roster API contract.

Hermetic: snapshots persona_participation state before each test and restores it
afterwards, and purges spawned bots so repeat runs start from a clean slate.
"""
import sys
import time
import pytest

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.core.database import get_db_connection
from backend.app.personas.definitions import PERSONAS
from backend.app.engine.participation import (
    participation_engine, MAX_AUTO_SPAWNED, ROLE_LIBRARY,
)


def _purge_spawned():
    """Remove spawned bots from DB + memory so runs are repeatable."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT persona_id FROM persona_participation WHERE origin = 'spawned'").fetchall()
        for r in rows:
            conn.execute("DELETE FROM persona_participation WHERE persona_id = ?", (r["persona_id"],))
            conn.execute("DELETE FROM bot_balances WHERE persona_id = ?", (r["persona_id"],))
        conn.commit()
    for pid in [r["persona_id"] for r in rows]:
        PERSONAS.pop(pid, None)


def _snapshot_participation():
    with get_db_connection() as conn:
        rows = conn.execute("SELECT persona_id, status FROM persona_participation").fetchall()
    return {r["persona_id"]: r["status"] for r in rows}


def _restore_participation(snap):
    with get_db_connection() as conn:
        for pid, status in snap.items():
            conn.execute("UPDATE persona_participation SET status = ? WHERE persona_id = ?",
                         (status, pid))
        conn.commit()


@pytest.fixture(autouse=True)
def _hermetic_state():
    _purge_spawned()
    snap = _snapshot_participation()
    yield
    _restore_participation(snap)
    _purge_spawned()


def test_founders_active_by_default():
    """The five founding personas ship opted-in (ACTIVE); opt-in model is on."""
    entry = participation_engine.get_roster_entry("solon")
    assert entry["status"] == "ACTIVE" and entry["origin"] == "founder"
    assert participation_engine.is_participating("solon")
    for role in ROLE_LIBRARY:
        assert participation_engine.role_has_active(role), f"no ACTIVE coverage for {role}"


def test_opt_in_gating_for_spawned_bots():
    """No spawned bot participates until a human opts it in (then out again)."""
    bot = participation_engine.auto_spawn("challenger", requested_by="pytest")
    assert bot.id in PERSONAS
    # PENDING_OPT_IN -> silent
    assert participation_engine.get_roster_entry(bot.id)["status"] == "PENDING_OPT_IN"
    assert not participation_engine.is_participating(bot.id)
    assert bot.id not in [p.id for p in participation_engine.eligible_speakers()]

    # Human opts it in -> ACTIVE and eligible
    entry = participation_engine.set_opt_in(bot.id, True, opted_in_by="pytest")
    assert entry["status"] == "ACTIVE"
    assert participation_engine.is_participating(bot.id)

    # Human opts it back out -> silent again
    entry = participation_engine.set_opt_in(bot.id, False, opted_in_by="pytest")
    assert entry["status"] == "OPTED_OUT"
    assert not participation_engine.is_participating(bot.id)


def test_lru_rotation_replaces_resting_bot():
    """When a bot rests, the least-recently-spoken eligible peer rotates in."""
    from backend.app.personas.sentiment import sentiment_engine

    # Record a known speaking order: solon oldest, lyra newest.
    participation_engine.record_spoke("solon")
    time.sleep(0.02)
    participation_engine.record_spoke("kael")
    time.sleep(0.02)
    participation_engine.record_spoke("lyra")

    replacement = participation_engine.pick_replacement("lyra")  # athena/milo are LRU
    assert replacement is not None
    assert replacement.id not in ("lyra", "solon", "kael")

    # Role-filtered pool only returns that role.
    champ_pool = participation_engine.eligible_speakers(["challenger"])
    assert all(p.role_type == "challenger" for p in champ_pool)

    # Resting bots are excluded from the eligible pool.
    sentiment_engine.toggle_rest_day("athena", True, "pytest rest")
    assert "athena" not in [p.id for p in participation_engine.eligible_speakers()]
    sentiment_engine.toggle_rest_day("athena", False)


def test_auto_spawn_cap_and_unknown_role():
    """Spawn cap is enforced; unknown roles are rejected; spawned stay silent."""
    for i in range(MAX_AUTO_SPAWNED):
        participation_engine.auto_spawn("empiricist", requested_by="pytest")
    assert participation_engine.count_spawned() == MAX_AUTO_SPAWNED

    with pytest.raises(PermissionError):
        participation_engine.auto_spawn("empiricist", requested_by="pytest")

    with pytest.raises(ValueError):
        participation_engine.auto_spawn("warlord", requested_by="pytest")


def test_role_has_active_reflects_opt_out():
    """Opting out every anchor leaves the role uncovered (batch spawn trigger)."""
    for p in list(PERSONAS.values()):
        if p.role_type == "anchor":
            participation_engine.set_opt_in(p.id, False, opted_in_by="pytest")
    assert not participation_engine.role_has_active("anchor")
    # Restore founders for the remainder of the suite.
    for p in list(PERSONAS.values()):
        if p.role_type == "anchor":
            participation_engine.set_opt_in(p.id, True, opted_in_by="pytest")
    assert participation_engine.role_has_active("anchor")


def test_roster_api_contract():
    """Roster endpoint shape matches the frontend Bots tab contract."""
    from backend.app.api.routes import get_participation_roster, set_persona_participation, OptInRequest

    payload = get_participation_roster()
    assert payload["spawn_cap"] == MAX_AUTO_SPAWNED
    assert payload["opt_in_required"] is True
    assert set(ROLE_LIBRARY) == set(payload["roles_available"])

    roster = payload["roster"]
    assert isinstance(roster, list) and len(roster) >= 5
    sample = roster[0]
    for field in ("persona_id", "status", "origin", "role_type", "opted_in",
                  "is_resting", "name", "avatar", "last_spoke_ago_sec"):
        assert field in sample, f"roster missing UI field {field}"

    res = set_persona_participation("milo", OptInRequest(participate=False, opted_in_by="pytest"))
    assert res["entry"]["status"] == "OPTED_OUT"
    set_persona_participation("milo", OptInRequest(participate=True, opted_in_by="pytest"))


def test_auto_spawn_batch_and_cap_conflict():
    """Batch spawn covers uncovered roles; single spawn past cap returns HTTP 409."""
    from backend.app.api.routes import auto_spawn_persona, AutoSpawnRequest
    from fastapi import HTTPException

    # Opt out all provocateurs -> batch should spawn exactly one provocateur.
    for p in list(PERSONAS.values()):
        if p.role_type == "provocateur":
            participation_engine.set_opt_in(p.id, False, opted_in_by="pytest")

    res = auto_spawn_persona(AutoSpawnRequest(role_type=None, requested_by="pytest"))
    spawned_roles = [s["role_type"] for s in res["spawned"]]
    assert spawned_roles == ["provocateur"]
    new_bot = res["spawned"][0]
    entry = participation_engine.get_roster_entry(new_bot["id"])
    assert entry["status"] == "PENDING_OPT_IN"  # silent until human opts in

    # Fill the cap, then a single spawn must 409.
    while participation_engine.count_spawned() < MAX_AUTO_SPAWNED:
        participation_engine.auto_spawn("anchor", requested_by="pytest")
    with pytest.raises(HTTPException) as ei:
        auto_spawn_persona(AutoSpawnRequest(role_type="anchor", requested_by="pytest"))
    assert ei.value.status_code == 409
