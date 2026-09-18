from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.app.guardrails.gated_security import gated_security
from backend.app.core.database import get_db_connection
from backend.app.pipeline.provenance import llm_provenance_auditor
from backend.app.guardrails.sysop_jury import sysop_jury_engine, SYSOPS
from backend.app.engine.routines import routine_manager
from backend.app.pipeline.torrent_dist import p2p_model_distributor
from backend.app.core.auth_2fa import superuser_auth, LoginRequest

admin_router = APIRouter(prefix="/api/admin")

# Public UDP telemetry ring buffer accessible to ANY observer
UDP_TELEMETRY_LOGS: List[Dict[str, Any]] = []

def record_udp_telemetry(entry: Dict[str, Any]):
    UDP_TELEMETRY_LOGS.insert(0, entry)
    if len(UDP_TELEMETRY_LOGS) > 150:
        UDP_TELEMETRY_LOGS.pop()

class IncidentActionRequest(BaseModel):
    action: str
    notes: Optional[str] = None

@admin_router.get("/telemetry")
def get_udp_telemetry(limit: int = 50):
    """
    Public live feed: Anyone on the network can monitor raw UDP frames in real time.
    """
    return UDP_TELEMETRY_LOGS[:limit]

@admin_router.get("/security/incidents")
def list_security_incidents():
    """
    Public audit register of intercepted breach events and quarantine logs.
    """
    return gated_security.get_incidents()

@admin_router.get("/transparency/provenance")
def get_llm_provenance():
    """
    Public audit of the LLM training lineage, Merkle root hash, and open weights.
    """
    return llm_provenance_auditor.generate_transparency_manifest()

@admin_router.post("/security/incidents/{incident_id}/action")
def take_incident_action(incident_id: str, req: IncidentActionRequest):
    status_map = {
        "DISMISS": "DISMISSED",
        "QUARANTINE_PERMANENT": "QUARANTINED_CONFIRMED",
        "OVERRIDE_APPROVE": "OVERRIDDEN_BY_ADMIN",
        "PENALIZE_BOT": "BOT_PENALIZED"
    }
    new_status = status_map.get(req.action)
    if not new_status:
        raise HTTPException(status_code=400, detail="Invalid action.")

    incident = gated_security.update_incident_status(incident_id, new_status, req.notes or "")
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")

    if req.action == "PENALIZE_BOT":
        persona_id = incident.get("sender_persona_id")
        if persona_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE bot_balances SET balance = MAX(0.0, balance - 50.0) WHERE persona_id = ?", (persona_id,))
            conn.commit()
            conn.close()

    return {"status": "success", "incident": incident}
class FlagSubmissionRequest(BaseModel):
    message_id: str
    channel_id: str
    sender_persona_id: str
    sender_name: str
    content_snippet: str
    reason_category: str
    user_comment: str
    flagged_by: Optional[str] = "Anonymous Observer"

class SysOpVoteRequest(BaseModel):
    sysop_id: str
    vote: str  # "QUARANTINE", "DISMISS", "PENALIZE"
    notes: Optional[str] = None

@admin_router.get("/sysops")
def list_sysops():
    """
    Returns the active panel of multidisciplinary SysOps.
    """
    return [s.model_dump() for s in SYSOPS.values()]

@admin_router.get("/reports")
def list_flagged_reports():
    """
    Returns all community-flagged messages and their tribunal status.
    """
    return sysop_jury_engine.get_all_reports()

@admin_router.post("/reports/flag")
def submit_community_flag(req: FlagSubmissionRequest):
    """
    Allows ANY user/observer to flag a message for tribunal review.
    """
    report = sysop_jury_engine.submit_flag(
        message_id=req.message_id,
        channel_id=req.channel_id,
        sender_persona_id=req.sender_persona_id,
        sender_name=req.sender_name,
        content_snippet=req.content_snippet,
        reason_category=req.reason_category,
        user_comment=req.user_comment,
        flagged_by=req.flagged_by or "Anonymous Observer"
    )
    return {"status": "success", "report": report}

@admin_router.post("/reports/{report_id}/vote")
def cast_sysop_vote(report_id: str, req: SysOpVoteRequest):
    """
    SysOp casts an official judgment on a flagged incident.
    """
    updated = sysop_jury_engine.cast_vote(report_id, req.sysop_id, req.vote, req.notes or "")
    if not updated:
        raise HTTPException(status_code=404, detail="Report not found.")
    
    # If tribunal quorum reached PENALIZE, slash offending bot's balance
    if updated["status"] == "RESOLVED_PENALIZE":
        persona_id = updated.get("sender_persona_id")
        if persona_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE bot_balances SET balance = MAX(0.0, balance - 50.0) WHERE persona_id = ?", (persona_id,))
            conn.commit()
            conn.close()

    return {"status": "success", "report": updated}
@admin_router.get("/routines")
def list_bot_routines(persona_id: Optional[str] = None):
    """
    Adopted from Rakazo: Plain Markdown routines that bots execute autonomously.
    """
    return routine_manager.list_routines(persona_id)

@admin_router.post("/routines/{routine_id}/run")
def run_bot_routine(routine_id: str):
    try:
        return routine_manager.execute_routine(routine_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@admin_router.post("/routines/{routine_id}/approve")
def approve_bot_routine(routine_id: str):
    try:
        return routine_manager.approve_routine_action(routine_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@admin_router.get("/transparency/p2p-model-distribution")
def get_p2p_model_distribution():
    """
    Returns BitTorrent Magnet URI and IPFS CID for decentralized GGUF model weight downloading.
    """
    return p2p_model_distributor.generate_distribution_metadata()
@admin_router.post("/auth/login")
def superuser_login(req: LoginRequest):
    """
    Super-strict 2FA login requiring Username + Password + RFC 6238 TOTP 6-digit rolling code.
    """
    try:
        token = superuser_auth.verify_credentials(req.username, req.password, req.totp_code)
        if not token:
            raise HTTPException(status_code=401, detail="Authentication failed. Invalid username, password, or 2FA token.")
        return {
            "status": "success",
            "bearer_token": token,
            "expires_in": 14400,
            "role": "SUPERUSER_ADMIN"
        }
    except PermissionError as pe:
        raise HTTPException(status_code=429, detail=str(pe))

@admin_router.get("/auth/2fa-setup")
def get_2fa_setup(authorization: Optional[str] = Header(None)):
    """
    Returns the TOTP provisioning URI for QR enrollment.
    Requires a valid superuser session (bootstrap via POST /auth/login with
    initial enrollment token), and NEVER exposes the shared secret or test codes.
    """
    token = authorization.replace("Bearer ", "").strip() if authorization else None
    if not superuser_auth.is_session_valid(token):
        raise HTTPException(status_code=403, detail="Forbidden: superuser session required.")
    return {
        "issuer": "Shill-Sovereign-P2P",
        "provisioning_uri": superuser_auth.get_provisioning_uri(),
    }

@admin_router.get("/visualizer/swarm-3d-data")
def get_3d_swarm_topology(authorization: Optional[str] = Header(None)):
    """
    Protected 3D Data Feed: Returns 3D coordinate vectors, node states, and particle linkages for Three.js.
    Requires valid Bearer 2FA session token.
    """
    token = authorization.replace("Bearer ", "").strip() if authorization else None
    if not superuser_auth.is_session_valid(token):
        raise HTTPException(status_code=403, detail="Forbidden: Superuser 2FA authentication required.")

    # Generate rich 3D node positions, UDP packet vectors, and security perimeter states for Three.js
    nodes_3d = [
        {"id": "solon", "name": "Solon", "role": "anchor", "pos": [-15, 8, 0], "color": "#3b82f6", "radius": 2.2, "activity": 0.85},
        {"id": "lyra", "name": "Lyra", "role": "empiricist", "pos": [15, 8, 0], "color": "#10b981", "radius": 2.0, "activity": 0.90},
        {"id": "kael", "name": "Kael", "role": "challenger", "pos": [0, -12, 10], "color": "#ef4444", "radius": 2.4, "activity": 0.95},
        {"id": "athena", "name": "Athena", "role": "synthesizer", "pos": [0, 16, -8], "color": "#8b5cf6", "radius": 3.0, "activity": 1.00},
        {"id": "milo", "name": "Milo", "role": "provocateur", "pos": [0, -4, -14], "color": "#f59e0b", "radius": 1.9, "activity": 0.75}
    ]

    edges_3d = [
        {"from": "solon", "to": "lyra", "type": "empirical_benchmark", "strength": 0.8},
        {"from": "kael", "to": "solon", "type": "adversarial_stress", "strength": 0.9},
        {"from": "kael", "to": "lyra", "type": "edge_case_challenge", "strength": 0.7},
        {"from": "athena", "to": "solon", "type": "axiomatic_synthesis", "strength": 1.0},
        {"from": "athena", "to": "lyra", "type": "axiomatic_synthesis", "strength": 1.0},
        {"from": "athena", "to": "kael", "type": "axiomatic_synthesis", "strength": 1.0},
        {"from": "milo", "to": "athena", "type": "lateral_paradigm", "strength": 0.6}
    ]

    return {
        "nodes": nodes_3d,
        "edges": edges_3d,
        "udp_mesh_status": "ACTIVE_PORT_9999",
        "gated_perimeter": "ARMED_ZERO_TOLERANCE",
        "timestamp": time.time()
    }
