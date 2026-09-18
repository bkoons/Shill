import pytest
import hashlib
from backend.app.core.database import init_db
from backend.app.core.democratic_sharding import (
    democratic_slice_engine,
    ShardInferenceRequest,
    TOTAL_MODEL_SLICES
)

def test_democratic_slice_assignment_and_storage_caps():
    """
    Validates SETI-style lightweight slice assignment:
    - Node hosts only 1-2 slices (each ~24MB, total < 64MB storage).
    - Fully within democratic non-intrusive citizen limits.
    """
    init_db()
    manifest = democratic_slice_engine.get_local_slice_manifest()
    assert len(manifest) >= 1
    assert len(manifest) <= 2

    # Check non-intrusive lightweight storage footprint
    total_storage_mb = sum(m.storage_mb for m in manifest)
    assert total_storage_mb <= democratic_slice_engine.storage_limit_mb
    assert total_storage_mb <= 64.0

    for s in manifest:
        assert s.total_slices == TOTAL_MODEL_SLICES
        assert s.activation_status == "ONLINE_HOSTING"
        assert s.slice_index in range(TOTAL_MODEL_SLICES)
        assert len(s.slice_sha256) == 64

def test_distributed_slice_inference_and_proof_receipt():
    """
    Validates execution of forward pipeline activation pass on a hosted slice.
    Ensures work is cryptographically verified and rewarded with micro-shares.
    """
    init_db()
    local_slices = list(democratic_slice_engine.hosted_slice_indices)
    target_slice = local_slices[0]

    req = ShardInferenceRequest(
        task_id="task-seti-pipeline-01",
        slice_index=target_slice,
        input_vector_digest=hashlib.sha256(b"TENSOR_ACTIVATION_INPUT_V1").hexdigest(),
        channel_id="arch-lab",
        origin_peer="192.168.1.42:9999"
    )

    receipt = democratic_slice_engine.compute_slice_activation(req)
    assert receipt.task_id == "task-seti-pipeline-01"
    assert receipt.slice_index == target_slice
    assert len(receipt.output_vector_digest) == 64
    assert receipt.latency_ms > 0
    assert receipt.earned_compute_reward > 0
    assert receipt.proof_signature.startswith("b") or len(receipt.proof_signature) == 64

def test_democratic_swarm_slice_announcement_and_coverage():
    """
    Validates dynamic peer slice aggregation across the swarm:
    Simulates peers broadcasting slices until 100% full model coverage is achieved.
    """
    init_db()
    # Register remaining slices from simulated peer nodes
    for idx in range(TOTAL_MODEL_SLICES):
        peer_name = f"citizen-peer-{idx}"
        democratic_slice_engine.register_peer_slice_announcement(
            peer_id=peer_name,
            slice_index=idx,
            tflops=1.5
        )

    coverage = democratic_slice_engine.get_cluster_topology_coverage()
    assert coverage["covered_slice_count"] == TOTAL_MODEL_SLICES
    assert coverage["global_swarm_coverage_pct"] == "100.0%"
    assert coverage["is_full_model_assembled"] is True
    assert coverage["local_storage_used_mb"] <= 64.0
