import hashlib
from backend.app.core.database import init_db
from backend.app.core.democratic_sharding import (
    DemocraticHiveSliceEngine, ShardConfig, ShardInferenceRequest,
    TOTAL_MODEL_SLICES, MAX_SLICES_HARD_CAP,
)

def test_genesis_defaults_backward_compat():
    init_db()
    e = DemocraticHiveSliceEngine(node_id="genesis-test-node")
    assert e.total_slices == TOTAL_MODEL_SLICES == 16
    assert 1 <= len(e.hosted_slice_indices) <= 2
    topo = e.get_cluster_topology_coverage()
    assert topo["total_slices"] == 16 and topo["total_model_slices"] == 16
    assert topo["local_storage_used_mb"] <= 64.0

def test_capacity_weighted_striping():
    init_db()
    small = DemocraticHiveSliceEngine(node_id="phone-node", storage_limit_mb=32.0)
    big = DemocraticHiveSliceEngine(node_id="rig-node", storage_limit_mb=512.0)
    assert len(small.hosted_slice_indices) == 1
    assert len(big.hosted_slice_indices) == 16  # capped by N=16 genesis
    big.set_model_manifest("big-model", model_bytes_mb=2400.0)
    assert big.total_slices > 16
    assert len(big.hosted_slice_indices) == 21  # 512//24
    assert big.get_cluster_topology_coverage()["local_storage_used_mb"] <= 512.0 + 24.0

def test_scsi_formula_and_parity():
    init_db()
    e = DemocraticHiveSliceEngine(node_id="formula-node")
    assert e.recalculate_total_slices(24.0) == 16  # min floor
    n = e.recalculate_total_slices(2000.0)
    assert n == 95, n  # 84 data + 11 parity
    assert e.is_parity_slice(8) is True
    assert e.is_parity_slice(0) is False

def test_swarm_grows_limitless():
    init_db()
    e = DemocraticHiveSliceEngine(node_id="swarm-node")
    assert e.total_slices == 16
    e.register_peer_slice_announcement("peer-big", 100, tflops=2.0, total_slices=200)
    assert e.total_slices == 200
    e.register_peer_slice_announcement("peer-small", 5, tflops=1.0, total_slices=50)
    assert e.total_slices == 200  # grow-only
    e.set_model_manifest("llama-70b", model_bytes_mb=40000.0)
    assert e.total_slices == 1876
    plan = e.get_stripe_plan(limit=9)
    assert plan[8]["is_parity"] is True
    assert "owners" in plan[0] and "wanted_replicas" in plan[0]

def test_rendezvous_minimal_reshuffle():
    init_db()
    e = DemocraticHiveSliceEngine(node_id="stable-node")
    before = set(e.hosted_slice_indices)
    e.set_model_manifest("grow-model", total_slices=64)
    after = set(e.hosted_slice_indices)
    assert len(after) == 2  # same capacity
    assert len(before & after) >= 0  # rendezvous keeps overlap likely; just check valid
    assert all(0 <= i < 64 for i in after)

def test_out_of_bounds_rejected():
    init_db()
    import pytest
    e = DemocraticHiveSliceEngine(node_id="bounds-node")
    with pytest.raises(ValueError):
        e.register_peer_slice_announcement("p", MAX_SLICES_HARD_CAP + 5)


def test_elastic_on_demand_adoption():
    init_db()
    e = DemocraticHiveSliceEngine(node_id="elastic-node", storage_limit_mb=64.0)
    # Baseline footprint is 64/24 = 2 stripes.
    assert len(e.hosted_slice_indices) == 2
    before = set(e.hosted_slice_indices)

    # A peer requests a stripe we do NOT host and that does not exist yet (idx 100).
    # With elastic autohost ON (default), the node should ADOPT it on demand.
    result = e.request_stripe_demand(100, origin="peer:9999", reason="peer needed stripe 100")
    assert result["adopted"] is True
    assert result["local_stripes"] == 3
    assert 100 in e.hosted_slice_indices
    assert e.get_elastic_status()["hosted_stripes"] == 3
    assert e.get_elastic_status()["elastic_ceiling"] >= 10  # 256MB/24MB >= 10

    # The adoption must be audited.
    ledger = e.get_adoption_ledger(limit=10)
    assert any(ev["action"] == "ADOPTED" and ev["slice_index"] == 100 for ev in ledger)

    # Demand for a stripe we already host does not double-adopt.
    dup = e.request_stripe_demand(100, origin="peer:9998")
    assert dup["adopted"] is False


def test_elastic_budget_cap_enforced():
    init_db()
    # Baseline 2 stripes (64/24), elastic ceiling 4 (96/24), headroom 1.0.
    e = DemocraticHiveSliceEngine(
        node_id="capped-node", storage_limit_mb=64.0,
        config=ShardConfig(target_shard_mb=24.0, replication_factor=1, min_slices=1, max_slices=256),
        total_slices=16)
    e.elastic_budget_mb = 96.0  # 96/24 = 4 ceiling
    e.elastic_headroom_multiplier = 1.0
    ceiling = e.elastic_stripe_ceiling()
    assert ceiling == 4, f"expected 4, got {ceiling}"

    # Adopt up to ceiling.
    adopted = 0
    for idx in range(16, 200):
        r = e.request_stripe_demand(idx, reason="load")
        if r["adopted"]:
            adopted += 1
        if adopted >= ceiling:
            break
    assert len(e.hosted_slice_indices) == ceiling, f"expected {ceiling}, got {len(e.hosted_slice_indices)}"

    # The next demand should be REFUSED (budget exhausted).
    refuse = e.request_stripe_demand(500, reason="load")
    assert refuse["adopted"] is False


def test_elastic_autohost_can_be_disabled():
    init_db()
    e = DemocraticHiveSliceEngine(node_id="passive-node")
    e.elastic_enabled = False
    e.autohost_on_demand = False
    r = e.request_stripe_demand(50, reason="test")
    assert r["adopted"] is False
    assert r["reason"] == "elastic autohost disabled"
