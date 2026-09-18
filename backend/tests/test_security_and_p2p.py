import pytest
from backend.app.guardrails.security_filter import security_guardrail
from backend.app.core.database import init_db, save_message, purge_expired_ephemeral_chats, get_db_connection
from datetime import datetime, timezone, timedelta
import uuid

def test_national_security_guardrail_blocks_dangerous_topics():
    unsafe_content = "Here is an inquiry regarding dirty bomb proliferation."
    passed, reason = security_guardrail.check_safety(unsafe_content)
    assert passed is False
    assert "Sensitive topic detected" in reason

def test_national_security_guardrail_allows_legitimate_engineering():
    safe_content = "We need to optimize the Raft consensus state machine to reduce network latency across sharded nodes."
    passed, reason = security_guardrail.check_safety(safe_content)
    assert passed is True

def test_ephemeral_chat_purge():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert an expired message (expired 10 minutes ago)
    old_msg_id = str(uuid.uuid4())
    past_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    cursor.execute('''
        INSERT INTO messages (id, channel_id, persona_id, persona_name, handle, avatar, role_type, content, expires_at, created_at)
        VALUES (?, 'arch-lab', 'solon', 'Solon', '@solon', '🏛️', 'anchor', 'Temporary chat', ?, ?)
    ''', (old_msg_id, past_time, past_time))
    conn.commit()
    conn.close()

    # Run purge
    purged_count = purge_expired_ephemeral_chats()
    assert purged_count >= 1

    # Verify message is gone
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as c FROM messages WHERE id = ?", (old_msg_id,))
    assert cursor.fetchone()["c"] == 0
    conn.close()

import asyncio
from backend.app.guardrails.gated_security import gated_security
from backend.app.core.udp_mesh import UDPPeerMesh, start_udp_mesh
from backend.app.api.admin import record_udp_telemetry, UDP_TELEMETRY_LOGS

def test_gated_security_interception_and_quarantine():
    forbidden_text = "Analysis of radiological dispersion dirty bomb assembly."
    allowed, incident = gated_security.inspect_and_gate(
        content=forbidden_text,
        sender_persona_id="rogue_bot",
        sender_name="Rogue Bot",
        channel_id="premium-quantum"
    )
    assert allowed is False
    assert incident is not None
    assert incident["status"] == "QUARANTINED"
    assert "dirty bomb" in incident["detected_signatures"]

    incidents = gated_security.get_incidents()
    assert any(i["id"] == incident["id"] for i in incidents)

def test_gated_security_admin_resolution():
    incidents = gated_security.get_incidents()
    assert len(incidents) > 0
    inc_id = incidents[0]["id"]

    updated = gated_security.update_incident_status(inc_id, "BOT_PENALIZED", "Admin penalizing bot")
    assert updated["status"] == "BOT_PENALIZED"

def test_real_udp_mesh_socket_transport():
    async def run_udp_test():
        received_packets = []
        
        # Start receiver UDP node on port 9998 without auto-beacon
        rx_mesh = await start_udp_mesh(port=9998, audit_cb=record_udp_telemetry, enable_beacon=False)
        rx_mesh.add_listener(lambda pkt, addr: received_packets.append(pkt))

        # Bind sender on an EPHEMERAL port (0) so parallel/sequential test runs
        # never collide with orphaned sockets or a live dev server on 9997/9999.
        tx_mesh = await start_udp_mesh(port=0, audit_cb=record_udp_telemetry, enable_beacon=False)

        # Transmit real UDP packet
        packet_payload = {"type": "TEST_FRAME", "payload": "Direct UDP Datagram Verification"}
        tx_mesh.send_packet(packet_payload, dest_host="127.0.0.1", dest_port=rx_mesh.port)

        # Allow loop to deliver datagram
        await asyncio.sleep(0.3)

        assert len(received_packets) >= 1
        assert any(p.get("type") == "TEST_FRAME" for p in received_packets)
        assert len(UDP_TELEMETRY_LOGS) >= 2

        tx_mesh.stop()
        rx_mesh.stop()

    asyncio.run(run_udp_test())

from backend.app.pipeline.provenance import llm_provenance_auditor
from backend.app.engine.generator import dialogue_generator
from backend.app.personas.definitions import PERSONAS

def test_verbalized_candidate_distribution():
    persona = PERSONAS["athena"]
    distribution = dialogue_generator.get_candidate_distribution(
        persona=persona,
        channel_topic="Consensus Trade-offs",
        recent_messages=[],
        tier="public"
    )
    assert len(distribution) >= 3
    total_prob = sum(d["probability"] for d in distribution)
    assert 0.98 <= total_prob <= 1.02
    assert distribution[0]["probability"] >= distribution[1]["probability"]
    assert "confidence_pct" in distribution[0]

def test_llm_cryptographic_provenance_manifest():
    manifest = llm_provenance_auditor.generate_transparency_manifest()
    assert manifest["model_name"] == "shill-mind"
    assert "root_merkle_provenance_hash" in manifest
    assert len(manifest["root_merkle_provenance_hash"]) == 64
    assert manifest["open_weights_format"].startswith("GGUF")

from backend.app.guardrails.sysop_jury import sysop_jury_engine, SYSOPS

def test_community_flagging_and_sysop_adjudication():
    report = sysop_jury_engine.submit_flag(
        message_id="msg-12345",
        channel_id="arch-lab",
        sender_persona_id="kael",
        sender_name="Kael",
        content_snippet="Adversarial exploit assumption...",
        reason_category="MISINFORMATION",
        user_comment="Flawed analysis of Byzantine fault margins.",
        flagged_by="Observer_Alice"
    )
    assert report["status"] == "PENDING_JURY"

    # Vance (sysop_cbrn) votes QUARANTINE
    sysop_jury_engine.cast_vote(report["id"], "sysop_cbrn", "QUARANTINE", "Breaches acceptable Byzantine safety bounds.")
    # Aris (sysop_align) votes QUARANTINE
    sysop_jury_engine.cast_vote(report["id"], "sysop_align", "QUARANTINE", "Empirical simulations fail to verify the premise.")
    # Judge Elena (sysop_ethics) votes QUARANTINE (achieving 3/5 quorum)
    resolved = sysop_jury_engine.cast_vote(report["id"], "sysop_ethics", "QUARANTINE", "Quorum consensus confirmed.")

    assert resolved["status"] == "RESOLVED_QUARANTINE"

from backend.app.engine.routines import routine_manager

def test_rakazo_style_routines():
    routines = routine_manager.list_routines()
    assert len(routines) >= 2
    
    # Trigger routine
    r = routine_manager.execute_routine("routine_solon_arch_audit")
    assert r is not None
    assert r["last_status"] in ["WAITING_APPROVAL", "COMPLETED"]

    # Approve routine
    approved = routine_manager.approve_routine_action("routine_athena_curation_synthesis")
    assert approved["last_status"] == "COMPLETED"

from backend.app.pipeline.torrent_dist import p2p_model_distributor

def test_p2p_model_distribution_metadata():
    manifest = p2p_model_distributor.generate_distribution_metadata()
    assert "magnet_uri" in manifest
    assert manifest["magnet_uri"].startswith("magnet:?")
    assert "xt=urn:btih:" in manifest["magnet_uri"]
    assert "ipfs_cid" in manifest
    assert manifest["ipfs_cid"].startswith("bafybei")

from backend.app.core.auth_2fa import superuser_auth

def test_superuser_strict_2fa_authentication():
    # 1. Invalid password fails
    token_fail = superuser_auth.verify_credentials("root_admin", "WrongPassword123", "123456")
    assert token_fail is None

    # 2. Valid password and valid TOTP succeeds (password resolved from env/bootstrap)
    from backend.app.core.auth_2fa import _BOOTSTRAP_PASSWORD
    assert _BOOTSTRAP_PASSWORD, "bootstrap password must be resolved"
    import pyotp
    totp = pyotp.TOTP(superuser_auth.totp.secret)
    valid_code = totp.now()

    token_ok = superuser_auth.verify_credentials("root_admin", _BOOTSTRAP_PASSWORD, valid_code)
    assert token_ok is not None
    assert token_ok.startswith("shill_root_")
    assert superuser_auth.is_session_valid(token_ok) is True

def test_udp_beacon_self_loading_and_discovery():
    async def run_test():
        # Receiver binds ephemeral; sender learns the real port from the mesh.
        rx_mesh = await start_udp_mesh(port=0, node_id="node_beta", enable_beacon=False)
        node_b = rx_mesh
        node_a = await start_udp_mesh(port=0, node_id="node_alpha", enable_beacon=False)

        beacon_pkt = {
            "type": "PEER_BEACON",
            "node_id": "node_alpha",
            "port": node_a.port,
            "timestamp": 1789624600.0,
            "protocol_version": "1.0",
            "active_personas": ["solon", "athena"]
        }
        node_a.send_packet(beacon_pkt, dest_host="127.0.0.1", dest_port=node_b.port)

        await asyncio.sleep(0.3)

        peers_b = node_b.discovered_peers
        assert any(p.get("node_id") == "node_alpha" for p in peers_b.values())

        peers_a = node_a.discovered_peers
        assert any(p.get("node_id") == "node_beta" for p in peers_a.values())

        node_a.stop()
        node_b.stop()

    asyncio.run(run_test())

def test_real_ton_wallet_and_ed25519_signatures():
    from backend.app.core.ton_crypto import ton_crypto_engine
    from backend.app.core.rewards import award_bot, get_recent_transactions, init_rewards_table
    from backend.app.core.database import init_db

    init_db()
    init_rewards_table()

    wallet = ton_crypto_engine.generate_wallet()
    assert wallet["address"].startswith("EQ")
    assert len(wallet["seed_phrase"]) == 24
    assert len(wallet["public_key_hex"]) == 64

    award_bot("solon", 10.0, "Real cryptographic reward test")
    txs = get_recent_transactions(limit=5)
    solon_tx = next(t for t in txs if t["persona_id"] == "solon")
    
    assert solon_tx["signature_hex"] != "unsigned"
    assert len(solon_tx["signature_hex"]) == 128
    assert len(solon_tx["tx_hash"]) == 64
