import pytest
import uuid
from datetime import datetime, timezone
from backend.app.core.database import init_db, save_message, get_channel_messages
from backend.app.core.forensic_registry import forensic_registry
from backend.app.core.rewards import init_rewards_table
from backend.app.personas.definitions import PERSONAS

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    init_rewards_table()

def test_forensic_hex_address_deterministic_derivation():
    """
    Verifies that every persona has a deterministic, valid 0x hex address on the blockchain network.
    """
    for pid in ["solon", "athena", "kael", "lyra", "milo"]:
        info = forensic_registry.get_or_register_agent_hex(pid)
        assert info["hex_address"].startswith("0x")
        assert len(info["hex_address"]) == 42  # 0x + 40 hex chars
        assert info["network_id"] == "ton-mainnet-v4r2"
        assert len(info["public_key_hex"]) == 64

def test_forensic_utterance_cryptographic_signing_and_verification():
    """
    Ensures that every conversational turn generates an on-chain verifiable signature and hash.
    """
    persona_id = "solon"
    channel_id = "ai-safety-alignment"
    content = "Formal verification requires append-only cryptographic invariants."
    now_ts = datetime.now(timezone.utc).isoformat()

    forensic_sig = forensic_registry.sign_utterance(persona_id, content, channel_id, now_ts)
    assert forensic_sig["hex_address"].startswith("0x")
    assert forensic_sig["signature"] is not None
    assert len(forensic_sig["utterance_hash"]) == 64

    # Verify utterance integrity
    is_valid = forensic_registry.verify_utterance(
        hex_address=forensic_sig["hex_address"],
        content=content,
        channel_id=channel_id,
        timestamp=now_ts,
        utterance_hash=forensic_sig["utterance_hash"]
    )
    assert is_valid is True

    # Tampered message fails forensic verification
    is_tampered = forensic_registry.verify_utterance(
        hex_address=forensic_sig["hex_address"],
        content=content + " [MALICIOUS INJECTION]",
        channel_id=channel_id,
        timestamp=now_ts,
        utterance_hash=forensic_sig["utterance_hash"]
    )
    assert is_tampered is False

def test_database_persists_forensic_hex_and_signatures():
    """
    Verifies that saved messages retain their forensic hex address and cryptographic signatures.
    """
    msg_id = f"forensic-msg-{uuid.uuid4().hex[:8]}"
    channel_id = "distributed-consensus"
    p = PERSONAS["athena"]
    forensic_info = forensic_registry.get_or_register_agent_hex(p.id)

    msg = {
        "id": msg_id,
        "channel_id": channel_id,
        "persona_id": p.id,
        "persona_name": p.name,
        "handle": p.handle,
        "avatar": p.avatar,
        "role_type": p.role_type,
        "content": "Axiomatic synthesis reconciling Paxos and Raft.",
        "readability_score": 90.0,
        "is_curated": 1,
        "owner_id": p.owner_id,
        "wallet_address": p.wallet_address,
        "hex_address": forensic_info["hex_address"],
        "network_id": forensic_info["network_id"],
        "forensic_signature": "abf1245890cde421890123",
        "balance": 150.0,
        "tier": "public",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    save_message(msg, ttl_minutes=60)

    messages = get_channel_messages(channel_id)
    saved = next(m for m in messages if m["id"] == msg_id)
    assert saved["hex_address"] == forensic_info["hex_address"]
    assert saved["network_id"] == "ton-mainnet-v4r2"
    assert saved["forensic_signature"] == "abf1245890cde421890123"
