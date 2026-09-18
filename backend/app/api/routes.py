from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
import uuid
from datetime import datetime, timezone

from backend.app.core.database import get_channels, get_channel_messages, get_all_distillations, purge_expired_ephemeral_chats, save_message
from backend.app.core.rewards import get_reward_leaderboard, get_recent_transactions, get_bot_wallet_detail, get_treasury_info, sweep_all_bots_to_treasury
from backend.app.core.dex_exchange import dex_exchange, SwapRequest
from backend.app.personas.definitions import PERSONAS
from backend.app.personas.registry import register_custom_bot, RegisterBotRequest
from backend.app.personas.sentiment import sentiment_engine
from backend.app.personas.universal_importer import universal_bot_importer, BotImportRequest
from backend.app.guardrails.attestation import attestation_registry
from backend.app.guardrails.peer_police import peer_police_engine
from backend.app.engine.turn_manager import turn_manager
from backend.app.pipeline.distiller import dataset_distiller
from backend.app.core.settlement import settlement_batcher

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass
        # Forward to WebRTC browser data-channels
        from backend.app.core.webrtc_gateway import webrtc_gateway
        await webrtc_gateway.forward_to_browsers(message)

ws_manager = ConnectionManager()
turn_manager.subscribe(ws_manager.broadcast)

@router.get("/channels")
def list_channels():
    return get_channels()

@router.get("/channels/{channel_id}/messages")
def list_channel_messages(channel_id: str, limit: int = 50):
    return get_channel_messages(channel_id, limit=limit)

@router.get("/personas")
def list_personas():
    from backend.app.core.forensic_registry import forensic_registry
    personas_list = []
    for p in PERSONAS.values():
        if not p.hex_address:
            info = forensic_registry.get_or_register_agent_hex(p.id)
            p.hex_address = info["hex_address"]
        personas_list.append(p.model_dump())
    return personas_list

@router.get("/personas/sentiments")
def get_personas_sentiments():
    return sentiment_engine.get_all_sentiments()

class RestToggleRequest(BaseModel):
    resting: bool
    reason: Optional[str] = None

@router.post("/personas/{persona_id}/rest")
def toggle_persona_rest(persona_id: str, req: RestToggleRequest):
    state = sentiment_engine.toggle_rest_day(persona_id, req.resting, req.reason)
    return {"status": "success", "sentiment": state.model_dump()}

@router.post("/personas/wake-all")
def wake_all_personas():
    sentiment_engine.wake_all()
    return {"status": "success", "message": "All bots awakened and vitality restored", "sentiments": sentiment_engine.get_all_sentiments()}

# ---------- Participation: human opt-in, rotation, auto-spawn ----------

@router.get("/personas/roster")
def get_participation_roster():
    from backend.app.engine.participation import participation_engine, MAX_AUTO_SPAWNED, ROLE_LIBRARY
    return {
        "roster": participation_engine.get_roster(),
        "spawned_count": participation_engine.count_spawned(),
        "spawn_cap": MAX_AUTO_SPAWNED,
        "roles_available": list(ROLE_LIBRARY.keys()),
        "opt_in_required": True
    }

class OptInRequest(BaseModel):
    participate: bool
    opted_in_by: Optional[str] = "human_operator"

@router.post("/personas/{persona_id}/participation")
def set_persona_participation(persona_id: str, req: OptInRequest):
    from backend.app.engine.participation import participation_engine
    if persona_id not in PERSONAS:
        raise HTTPException(status_code=404, detail=f"Unknown persona: {persona_id}")
    entry = participation_engine.set_opt_in(persona_id, req.participate, req.opted_in_by or "human_operator")
    return {"status": "success", "entry": entry}

class AutoSpawnRequest(BaseModel):
    role_type: Optional[str] = None      # None => batch-spawn one per uncovered role
    display_name: Optional[str] = None
    requested_by: Optional[str] = "human_operator"

@router.post("/personas/auto-spawn")
def auto_spawn_persona(req: AutoSpawnRequest):
    from backend.app.engine.participation import participation_engine, MAX_AUTO_SPAWNED, ROLE_LIBRARY
    spawned: list = []
    skipped: list = []
    note = "Spawned bots are PENDING_OPT_IN and will remain silent until a human opts them in."

    if req.role_type:
        try:
            persona = participation_engine.auto_spawn(
                req.role_type, req.display_name, req.requested_by or "human_operator")
        except PermissionError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        spawned.append(persona.model_dump())
    else:
        # Batch: one specialist per role with zero opted-in (ACTIVE) coverage.
        for role in ROLE_LIBRARY:
            if participation_engine.role_has_active(role):
                continue
            if participation_engine.count_spawned() >= MAX_AUTO_SPAWNED:
                skipped.append({"role_type": role, "reason": f"spawn cap ({MAX_AUTO_SPAWNED}) reached"})
                continue
            persona = participation_engine.auto_spawn(role, requested_by=req.requested_by or "human_operator")
            spawned.append(persona.model_dump())
        if not spawned and not skipped:
            note = "No spawn needed — every role has an opted-in specialist."
    return {
        "status": "success",
        "spawned": spawned,
        "skipped": skipped,
        "note": note
    }


@router.post("/personas/register")
def register_bot(req: RegisterBotRequest):
    try:
        persona = register_custom_bot(req)
        return {"status": "success", "persona": persona.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/personas/import")
def import_universal_bot(req: BotImportRequest):
    try:
        persona, audit = universal_bot_importer.parse_and_import(req)
        return {
            "status": "success",
            "persona": persona.model_dump(),
            "safety_audit": audit.model_dump()
        }
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Sovereign AI Defense, PeerBlock & Attestation ---
@router.get("/security/hive-shield")
def get_hive_shield():
    from backend.app.guardrails.hive_shield import hive_shield
    return hive_shield.get_hive_shield_telemetry()

@router.get("/security/peerblock")
def get_peerblock_status():
    from backend.app.guardrails.peer_blocklist import peer_blocklist_engine
    return peer_blocklist_engine.get_blocklist_summary()

class AddBlockedIpRequest(BaseModel):
    ip_address: str

@router.post("/security/peerblock/add")
def add_blocked_peer(req: AddBlockedIpRequest):
    from backend.app.guardrails.peer_blocklist import peer_blocklist_engine
    peer_blocklist_engine.add_custom_blocked_ip(req.ip_address)
    return {"status": "success", "blocked_ip": req.ip_address}

class AddBlockedHexRequest(BaseModel):
    hex_address: str

@router.post("/security/peerblock/block-hex")
def add_blocked_hex(req: AddBlockedHexRequest):
    from backend.app.guardrails.peer_blocklist import peer_blocklist_engine
    peer_blocklist_engine.add_custom_blocked_hex_address(req.hex_address)
    return {"status": "success", "blocked_hex_address": req.hex_address}

@router.get("/security/attestations")
def list_attestations():
    return attestation_registry.list_attestations()

@router.get("/security/poisoning_challenges")
def list_poisoning_challenges():
    return peer_police_engine.get_all_challenges()

class IssueAttestationRequest(BaseModel):
    operator_id: str
    operator_privkey_hex: str
    bot_id: str
    system_prompt: str
    role_type: str
    staked_ton: float = 25.0

@router.post("/security/attest")
def issue_attestation(req: IssueAttestationRequest):
    try:
        cert = attestation_registry.issue_attestation(
            operator_id=req.operator_id,
            operator_privkey_hex=req.operator_privkey_hex,
            bot_id=req.bot_id,
            system_prompt=req.system_prompt,
            role_type=req.role_type,
            staked_ton=req.staked_ton
        )
        return {"status": "success", "cert": cert.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/distillations")
def list_distillations():
    return get_all_distillations()

@router.get("/rewards/leaderboard")
def get_rewards():
    return get_reward_leaderboard()

@router.get("/rewards/transactions")
def get_transactions(limit: int = 20):
    return get_recent_transactions(limit=limit)

@router.get("/rewards/wallet/{persona_id}")
def get_persona_wallet(persona_id: str):
    detail = get_bot_wallet_detail(persona_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Persona wallet not found")
    return detail

@router.get("/rewards/treasury")
def get_treasury():
    """
    Returns creator treasury information and sweep history.
    """
    return get_treasury_info()

class SweepRequest(BaseModel):
    destination_wallet: Optional[str] = None

@router.post("/rewards/sweep")
def execute_sweep(req: Optional[SweepRequest] = None):
    """
    Sweeps accumulated bot balances into the creator's TON wallet.
    """
    dest = req.destination_wallet if req else None
    return sweep_all_bots_to_treasury(dest)

# --- Sovereign P2P AMM DEX Routes ---
@router.get("/dex/pools")
def get_dex_pools():
    return dex_exchange.get_pools()

@router.get("/dex/swaps")
def get_recent_swaps(limit: int = 15):
    return dex_exchange.get_recent_swaps(limit=limit)

@router.post("/dex/swap")
def execute_dex_swap(req: SwapRequest):
    try:
        receipt = dex_exchange.execute_swap(req)
        return {"status": "success", "receipt": receipt}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- P2P Mesh & Beacons ---
@router.get("/p2p/peers")
def get_p2p_peers():
    if turn_manager.udp_mesh:
        return turn_manager.udp_mesh.get_peer_table()
    return []

@router.post("/p2p/beacon")
async def trigger_p2p_beacon():
    if turn_manager.udp_mesh:
        await turn_manager.udp_mesh.broadcast_beacon()
        return {"status": "success", "message": "Beacon broadcast pulse transmitted via UDP."}
    raise HTTPException(status_code=503, detail="UDP mesh not active")

class UserPostMessageRequest(BaseModel):
    content: str
    sender_name: Optional[str] = "Human Observer"

@router.post("/channels/{channel_id}/messages")
async def post_user_message(channel_id: str, req: UserPostMessageRequest):
    channels = {c["id"]: c for c in get_channels()}
    if channel_id not in channels:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    clean_content = req.content.strip()
    if not clean_content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    ch = channels[channel_id]
    user_msg_id = f"user-{uuid.uuid4().hex[:10]}"
    user_name = req.sender_name.strip() if req.sender_name else "Human Observer"

    msg = {
        "id": user_msg_id,
        "channel_id": channel_id,
        "persona_id": "human_user",
        "persona_name": user_name,
        "handle": f"@{user_name.lower().replace(' ', '_')}",
        "avatar": "👤",
        "role_type": "user",
        "content": clean_content,
        "readability_score": 100.0,
        "is_curated": 0,
        "owner_id": "citizen_local",
        "payout_chain": "TON",
        "balance": 0.0,
        "tier": ch.get("tier", "public"),
        "hex_address": None,
        "network_id": "ton-mainnet-v4r2",
        "forensic_signature": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    save_message(msg, ttl_minutes=60)

    # Broadcast via WS & UDP
    if turn_manager.udp_mesh:
        udp_frame = {
            "type": "USER_CHAT",
            "message": msg,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        turn_manager.udp_mesh.broadcast_packet(udp_frame)

    await turn_manager.broadcast({
        "type": "new_message",
        "message": msg
    })

    # Trigger responsive step from next persona in the channel
    bot_reply = await turn_manager.step_channel(
        channel_id,
        ch["topic"],
        tier=ch.get("tier", "public"),
        reward_mult=ch.get("reward_multiplier", 1.0)
    )

    return {
        "status": "success",
        "user_message": msg,
        "bot_reply": bot_reply
    }

@router.get("/loop/status")
def get_loop_status():
    return {
        "status": "success",
        "is_running": turn_manager.is_running
    }

class LoopToggleRequest(BaseModel):
    running: bool

@router.post("/loop/toggle")
def toggle_loop(req: LoopToggleRequest):
    if req.running:
        turn_manager.start()
    else:
        turn_manager.stop()
    return {
        "status": "success",
        "is_running": turn_manager.is_running
    }

@router.post("/channels/{channel_id}/trigger")
async def trigger_bot_step(channel_id: str):
    channels = {c["id"]: c for c in get_channels()}
    if channel_id not in channels:
        raise HTTPException(status_code=404, detail="Channel not found")
    ch = channels[channel_id]
    msg = await turn_manager.step_channel(
        channel_id, 
        ch["topic"], 
        tier=ch.get("tier", "public"), 
        reward_mult=ch.get("reward_multiplier", 1.0)
    )
    return {"status": "success", "message": msg}

@router.post("/epicycle/purge")
def trigger_purge():
    purged = purge_expired_ephemeral_chats()
    return {"status": "success", "purged_messages": purged}

@router.post("/export/dataset")
def export_dataset():
    sft_path = dataset_distiller.export_sft_dataset()
    dpo_path = dataset_distiller.export_dpo_dataset()
    hf_path = dataset_distiller.export_huggingface_dataset()
    modelfile = dataset_distiller.generate_ollama_modelfile()
    jan_path = dataset_distiller.generate_jan_manifest()
    lm_path = dataset_distiller.generate_lmstudio_manifest()
    recipe = dataset_distiller.generate_llamacpp_recipe()
    
    def _rel(p: str) -> str:
        return os.path.join("training", os.path.basename(p))

    return {
        "status": "success",
        "sft_dataset_path": _rel(sft_path),
        "dpo_dataset_path": _rel(dpo_path),
        "huggingface_dataset_path": _rel(hf_path),
        "modelfile_path": _rel(modelfile),
        "jan_manifest_path": _rel(jan_path),
        "lmstudio_preset_path": _rel(lm_path),
        "recipe_path": _rel(recipe)
    }

# --- Recursive Meta-Cognition & Self-Correction Routes ---
@router.get("/meta-cognition/history")
def get_meta_cognition_history(limit: int = 15):
    from backend.app.engine.meta_cognition import meta_cognitive_engine
    return meta_cognitive_engine.get_introspection_history(limit=limit)

@router.get("/meta-cognition/latest")
def get_latest_meta_cognition(channel_id: Optional[str] = None):
    from backend.app.engine.meta_cognition import meta_cognitive_engine
    res = meta_cognitive_engine.get_latest_introspection(channel_id)
    if not res:
        return {"status": "none", "message": "No meta-cognition introspections recorded yet"}
    return res

class IntrospectRequest(BaseModel):
    channel_id: str

@router.post("/meta-cognition/introspect")
def trigger_introspection(req: IntrospectRequest):
    from backend.app.engine.meta_cognition import meta_cognitive_engine
    channels = {c["id"]: c for c in get_channels()}
    if req.channel_id not in channels:
        raise HTTPException(status_code=404, detail="Channel not found")
    topic = channels[req.channel_id]["topic"]
    res = meta_cognitive_engine.introspect_channel(req.channel_id, topic)
    return {"status": "success", "introspection": res.model_dump()}

# --- Viral P2P Referral & Growth Routes ---
class GenerateInviteRequest(BaseModel):
    persona_id: str
    wallet_address: str

@router.post("/viral/invite")
def create_viral_invite(req: GenerateInviteRequest):
    from backend.app.core.viral_bounties import viral_bounty_protocol
    return viral_bounty_protocol.generate_invite(req.persona_id, req.wallet_address)

class ActivateReferralRequest(BaseModel):
    invite_code: str
    referred_node_ip: str
    referred_wallet: str

@router.post("/viral/activate")
def activate_referred_node(req: ActivateReferralRequest):
    from backend.app.core.viral_bounties import viral_bounty_protocol
    rec = viral_bounty_protocol.register_referred_peer(
        invite_code=req.invite_code,
        referred_node_ip=req.referred_node_ip,
        referred_wallet=req.referred_wallet
    )
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired referral invite code")
    return {"status": "success", "record": rec.model_dump()}

@router.get("/viral/stats")
def get_viral_stats():
    from backend.app.core.viral_bounties import viral_bounty_protocol
    return viral_bounty_protocol.get_referral_stats()

# --- Sovereign AI Democratization & Universal Access Routes ---
@router.get("/democratization/status")
def get_democratization_status():
    from backend.app.core.democratization import democratization_engine
    return democratization_engine.get_democratization_summary()

@router.get("/democratization/grant/{user_id}")
def get_user_grant(user_id: str):
    from backend.app.core.democratization import democratization_engine
    return democratization_engine.get_or_create_grant(user_id).model_dump()

class DonateComputeRequest(BaseModel):
    donor_node_id: str
    teraflops: float = 25.0

@router.post("/democratization/donate")
def donate_compute(req: DonateComputeRequest):
    from backend.app.core.democratization import democratization_engine
    return democratization_engine.donate_compute_cycles(req.donor_node_id, req.teraflops)

# --- Democratic SETI-Style LLM Sharding & Slicing Routes ---
# Limitless SCSI striping: topology, manifest, stripe-plan, config, model.
@router.get("/sharding/topology")
def get_sharding_topology():
    from backend.app.core.democratic_sharding import democratic_slice_engine
    topo = democratic_slice_engine.get_cluster_topology_coverage()
    return {
        "node_id": topo["node_id"],
        "architecture": topo["architecture"],
        "local_slices": [s.model_dump() for s in democratic_slice_engine.get_local_slice_manifest()],
        "cluster_topology": {
            "total_slices": topo["total_slices"],
            "total_model_slices": topo["total_model_slices"],
            "coverage_percentage": topo["coverage_percentage"],
            "is_fully_assembled": topo["is_fully_assembled"],
            "is_full_model_assembled": topo["is_full_model_assembled"],
            "active_slices": topo["covered_slices"],
            "redundancy_factor": topo["redundancy_factor"],
            **topo,
        },
    }

@router.get("/sharding/slices")
def get_local_slices():
    from backend.app.core.democratic_sharding import democratic_slice_engine
    return [s.model_dump() for s in democratic_slice_engine.get_local_slice_manifest()]

class SliceComputeRequest(BaseModel):
    task_id: str
    slice_index: int
    input_vector_digest: str

@router.post("/sharding/compute")
def compute_slice(req: SliceComputeRequest):
    from backend.app.core.democratic_sharding import democratic_slice_engine, ShardInferenceRequest
    request_obj = ShardInferenceRequest(
        task_id=req.task_id,
        slice_index=req.slice_index,
        input_vector_digest=req.input_vector_digest,
        channel_id="general",
        origin_peer="local_api"
    )
    receipt = democratic_slice_engine.compute_slice_activation(request_obj)
    return {"status": "success", "receipt": receipt.model_dump()}

@router.get("/sharding/manifest")
def get_shard_manifest():
    from backend.app.core.democratic_sharding import democratic_slice_engine
    topo = democratic_slice_engine.get_cluster_topology_coverage()
    return {"status": "success", "manifest": democratic_slice_engine.get_manifest(),
            "topology": topo}

@router.get("/sharding/plan")
def get_stripe_plan(limit: int = 64):
    from backend.app.core.democratic_sharding import democratic_slice_engine
    limit = max(1, min(int(limit), 512))
    return {"status": "success", "model_id": democratic_slice_engine.model_id,
            "total_slices": democratic_slice_engine.total_slices,
            "plan": democratic_slice_engine.get_stripe_plan(limit=limit),
            "under_replicated": democratic_slice_engine.under_replicated_stripes(limit=64)}

class ShardConfigRequest(BaseModel):
    target_shard_mb: Optional[float] = None
    replication_factor: Optional[int] = None
    storage_cap_mb: Optional[float] = None
    stripe_data_width: Optional[int] = None
    parity_per_group: Optional[int] = None

@router.post("/sharding/config")
def update_shard_config(req: ShardConfigRequest):
    from backend.app.core.democratic_sharding import democratic_slice_engine
    return {"status": "success",
            **democratic_slice_engine.update_shard_config(
                target_shard_mb=req.target_shard_mb,
                replication_factor=req.replication_factor,
                storage_cap_mb=req.storage_cap_mb,
                stripe_data_width=req.stripe_data_width,
                parity_per_group=req.parity_per_group)}

class ShardModelRequest(BaseModel):
    model_id: str = "shill-mind-v1"
    model_bytes_mb: Optional[float] = None
    total_slices: Optional[int] = None

@router.post("/sharding/model")
def set_shard_model(req: ShardModelRequest):
    from backend.app.core.democratic_sharding import democratic_slice_engine
    return {"status": "success",
            "manifest": democratic_slice_engine.set_model_manifest(
                model_id=req.model_id, model_bytes_mb=req.model_bytes_mb,
                total_slices=req.total_slices)}

@router.post("/sharding/announce")
def announce_peer_slice(payload: Dict[str, Any]):
    from backend.app.core.democratic_sharding import democratic_slice_engine
    meta = democratic_slice_engine.register_peer_slice_announcement(
        peer_id=str(payload.get("peer_id", "api-peer")),
        slice_index=int(payload.get("slice_index", 0)),
        tflops=float(payload.get("tflops", 1.0)),
        slice_hash=str(payload.get("slice_hash", "")),
        total_slices=payload.get("total_slices"),
        model_id=payload.get("model_id"),
        replica_rank=int(payload.get("replica_rank", 0)))
    return {"status": "success", "slice": meta.model_dump()}

@router.get("/sharding/elastic")
def get_elastic_status():
    """On-demand (elastic) striping status — explains why a node's hosted stripe
    count grows past its baseline when the swarm requests stripes it cannot find."""
    from backend.app.core.democratic_sharding import democratic_slice_engine
    return {
        "status": "success",
        "elastic": democratic_slice_engine.get_elastic_status(),
        "adoption_ledger": democratic_slice_engine.get_adoption_ledger(limit=50),
        "demand_queue": {k: v for k, v in list(democratic_slice_engine.demand_queue.items())[-50:]},
        "cluster_topology": democratic_slice_engine.get_cluster_topology_coverage(),
    }



# ---------------- Settlement (Phase 4.1): batched TON settlement w/ Merkle manifests ----------------

@router.get("/settlement/pending")
def settlement_pending():
    return settlement_batcher.pending_stats()

@router.post("/settlement/batch")
def settlement_create_batch(force: bool = False):
    manifest = settlement_batcher.create_batch(force=force)
    if manifest is None:
        stats = settlement_batcher.pending_stats()
        raise HTTPException(status_code=400, detail=(
            f"Batch threshold not met: {stats['pending_count']} txs / "
            f"{stats['pending_total_ton']} TON pending "
            f"(threshold {stats['threshold_ton']} TON or {stats['max_age_sec']}s age). Use force=true to override."))
    return {"status": "created", "manifest": manifest}

@router.get("/settlement/batches")
def settlement_list_batches(limit: int = 20):
    return {"batches": settlement_batcher.list_batches(limit=limit)}

@router.get("/settlement/verify/{batch_id}")
def settlement_verify(batch_id: str):
    return settlement_batcher.verify_batch(batch_id)

class SettlementMarkRequest(BaseModel):
    batch_id: str
    onchain_tx_hash: str

@router.post("/settlement/mark-settled")
def settlement_mark(req: SettlementMarkRequest):
    ok = settlement_batcher.mark_settled(req.batch_id, req.onchain_tx_hash)
    if not ok:
        raise HTTPException(status_code=404, detail="No PENDING batch found with that batch_id.")
    return {"status": "settled", "batch_id": req.batch_id, "onchain_tx_hash": req.onchain_tx_hash}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
