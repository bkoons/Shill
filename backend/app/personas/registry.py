from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import re
from backend.app.personas.definitions import PERSONAS, Persona
from backend.app.core.database import get_db_connection
from backend.app.core.ton_crypto import ton_crypto_engine

class RegisterBotRequest(BaseModel):
    id: str = Field(..., description="Unique alphanumeric handle for the bot")
    name: str
    handle: str
    avatar: str = "🤖"
    role_type: str = "challenger"  # anchor, challenger, empiricist, synthesizer, provocateur
    specialties: List[str] = ["systems", "ai"]
    system_prompt: str
    owner_id: str
    wallet_address: Optional[str] = None
    payout_chain: str = "TON"
    color: str = "#3b82f6"

def register_custom_bot(req: RegisterBotRequest) -> Persona:
    clean_id = re.sub(r'[^a-zA-Z0-9_-]', '', req.id).lower()
    if not clean_id:
        raise ValueError("Invalid bot ID.")

    # 0. Zero-Quarter Anti-Poisoning & Hive Shield Inspection on Prompt
    from backend.app.guardrails.hive_shield import hive_shield
    from backend.app.guardrails.anti_poisoning import anti_poisoning_auditor
    from backend.app.guardrails.peer_blocklist import peer_blocklist_engine

    h_check = hive_shield.inspect_threat(req.system_prompt, sender_id=clean_id)
    if h_check.is_hardened_threat:
        raise PermissionError(f"Collective Hive Shield blocked bot registration ({h_check.threat_category}): {h_check.reason}")

    p_check = anti_poisoning_auditor.audit_content(req.system_prompt)
    if p_check.is_poisonous:
        raise PermissionError(f"Anti-Poisoning Auditor rejected bot prompt: {p_check.detected_vector} detected.")

    pb_check = peer_blocklist_engine.check_content_payload(req.system_prompt)
    if pb_check.is_blocked:
        raise PermissionError(f"PeerBlock violation on bot prompt: {pb_check.rule_matched}")

    if req.wallet_address:
        hex_check = peer_blocklist_engine.check_hex_address(req.wallet_address)
        if hex_check.is_blocked:
            raise PermissionError(f"Proscribed blockchain hex address: {hex_check.rule_matched}")

    # Generate a real TON v4r2 wallet if none provided or if dummy placeholder
    if not req.wallet_address or req.wallet_address.endswith("...ton"):
        real_wallet = ton_crypto_engine.generate_wallet()
        wallet_address = real_wallet["address"]
        pub_k = real_wallet["public_key_hex"]
        priv_k = real_wallet["private_key_hex"]
        seed = " ".join(real_wallet["seed_phrase"])
    else:
        wallet_address = req.wallet_address
        pub_k = ""
        priv_k = ""
        seed = ""

    persona = Persona(
        id=clean_id,
        name=req.name,
        handle=req.handle if req.handle.startswith("@") else f"@{req.handle}",
        avatar=req.avatar,
        role_type=req.role_type,
        system_prompt=req.system_prompt,
        specialties=req.specialties,
        color=req.color,
        owner_id=req.owner_id,
        wallet_address=wallet_address,
        payout_chain=req.payout_chain,
        balance=0.0
    )

    PERSONAS[clean_id] = persona

    # Register into SQLite reward ledger with real keys
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO bot_balances (persona_id, owner_id, wallet_address, public_key_hex, private_key_hex, seed_phrase, payout_chain, balance, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ''', (persona.id, persona.owner_id, wallet_address, pub_k, priv_k, seed, persona.payout_chain, 0.0))
    conn.commit()
    conn.close()

    return persona
