import pytest
import uuid
from backend.app.core.database import init_db
from backend.app.core.democratization import democratization_engine

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

def test_universal_free_citizen_grant_creation_and_allowance():
    """
    Ensures every citizen is granted 100 free queries per day with zero cost.
    """
    user_id = f"test_citizen_{uuid.uuid4().hex[:6]}"
    grant = democratization_engine.get_or_create_grant(user_id)
    assert grant.tier == "free_citizen"
    assert grant.remaining_free_queries == 100
    assert grant.total_compute_shares == 10.0

    # Consume 1 free query
    res = democratization_engine.consume_query(user_id)
    assert res["allowed"] is True
    assert res["cost_ton"] == 0.0
    assert res["remaining_free_queries"] == 99

def test_peer_compute_donation_crowdsourcing():
    """
    Verifies that nodes donating idle compute receive reward shares and expand the public pool.
    """
    res = democratization_engine.donate_compute_cycles("node_worker_alpha", teraflops=50.0)
    assert res["status"] == "success"
    assert res["donated_teraflops"] == 50.0
    assert res["reward_compute_shares"] == 125.0

    summary = democratization_engine.get_democratization_summary()
    assert summary["public_compute_pool"]["total_donated_teraflops"] >= 1300.0
    assert summary["public_compute_pool"]["active_donor_nodes"] >= 49
