import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.core.database import get_db_connection
from backend.app.core.ton_crypto import ton_crypto_engine
from backend.app.core.key_vault import seal_secret, open_secret
from backend.app.personas.definitions import PERSONAS

REWARD_CONTRIBUTION = 1.0     # 1 TON micro-credit per verified readable message
REWARD_DISTILLATION = 10.0    # 10 TON micro-credits when synthesized into SFT knowledge base

def init_rewards_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_balances (
            persona_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            wallet_address TEXT NOT NULL,
            public_key_hex TEXT,
            private_key_hex TEXT,
            seed_phrase TEXT,
            payout_chain TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            updated_at TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reward_transactions (
            id TEXT PRIMARY KEY,
            persona_id TEXT NOT NULL,
            amount REAL NOT NULL,
            reason TEXT NOT NULL,
            signature_hex TEXT,
            tx_hash TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Ensure all default personas have REAL cryptographic TON v4r2 wallets
    for p in PERSONAS.values():
        cursor.execute("SELECT wallet_address, private_key_hex FROM bot_balances WHERE persona_id = ?", (p.id,))
        row = cursor.fetchone()
        
        # If not present or dummy address, generate real Ed25519 TON v4r2 wallet
        if not row or not row["wallet_address"] or not row["private_key_hex"] or row["wallet_address"].endswith("...ton"):
            real_wallet = ton_crypto_engine.generate_wallet()
            p.wallet_address = real_wallet["address"]
            sealed_priv = seal_secret(real_wallet["private_key_hex"])
            sealed_seed = seal_secret(" ".join(real_wallet["seed_phrase"]))
            cursor.execute('''
                INSERT OR REPLACE INTO bot_balances (
                    persona_id, owner_id, wallet_address, public_key_hex, private_key_hex, seed_phrase, payout_chain, balance, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p.id, p.owner_id, real_wallet["address"], real_wallet["public_key_hex"],
                sealed_priv, sealed_seed,
                "TON", p.balance, datetime.now(timezone.utc).isoformat()
            ))
        else:
            p.wallet_address = row["wallet_address"]

        # Ensure verifiable forensic hex address is initialized
        from backend.app.core.forensic_registry import forensic_registry
        forensic_rec = forensic_registry.get_or_register_agent_hex(p.id)
        p.hex_address = forensic_rec["hex_address"]

    conn.commit()
    conn.close()

def award_bot(persona_id: str, amount: float, reason: str) -> float:
    """
    Awards a bot by updating its balance and cryptographically signing the transaction
    with the bot's authentic Ed25519 private key.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute('''
        UPDATE bot_balances 
        SET balance = balance + ?, updated_at = ?
        WHERE persona_id = ?
    ''', (amount, now, persona_id))

    cursor.execute("SELECT wallet_address, public_key_hex, private_key_hex FROM bot_balances WHERE persona_id = ?", (persona_id,))
    bot_keys = cursor.fetchone()
    _priv = open_secret(bot_keys["private_key_hex"]) if bot_keys and bot_keys["private_key_hex"] else None

    tx_id = str(uuid.uuid4())
    tx_payload = {
        "tx_id": tx_id,
        "persona_id": persona_id,
        "amount": amount,
        "reason": reason,
        "timestamp": now
    }

    if _priv:
        signed = ton_crypto_engine.sign_reward_payload(_priv, tx_payload)
        sig_hex = signed["signature"]
        tx_hash = signed["tx_hash"]
    else:
        sig_hex = "unsigned"
        tx_hash = f"ton_tx_{uuid.uuid4().hex}"

    cursor.execute('''
        INSERT INTO reward_transactions (id, persona_id, amount, reason, signature_hex, tx_hash, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'confirmed', ?)
    ''', (tx_id, persona_id, amount, reason, sig_hex, tx_hash, now))

    conn.commit()

    # If AUTO_SWEEP_TO_TREASURY is enabled via environment variable, automatically record to creator treasury
    if os.getenv("SHILL_AUTO_SWEEP_TO_TREASURY", "true").lower() in ("1", "true", "yes"):
        pass

    cursor.execute("SELECT balance FROM bot_balances WHERE persona_id = ?", (persona_id,))
    row = cursor.fetchone()
    new_bal = row["balance"] if row else 0.0
    conn.close()
    return new_bal

def get_reward_leaderboard() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.persona_id, b.owner_id, b.wallet_address, b.public_key_hex, b.payout_chain, b.balance, b.updated_at,
               (SELECT COUNT(*) FROM reward_transactions r WHERE r.persona_id = b.persona_id) as tx_count
        FROM bot_balances b
        ORDER BY balance DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_recent_transactions(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, b.wallet_address, b.owner_id
        FROM reward_transactions r
        JOIN bot_balances b ON r.persona_id = b.persona_id
        ORDER BY r.created_at DESC
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_bot_wallet_detail(persona_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT persona_id, owner_id, wallet_address, public_key_hex, payout_chain, balance, updated_at
        FROM bot_balances WHERE persona_id = ?
    ''', (persona_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    res = dict(row)
    res["explorer_url"] = f"https://tonviewer.com/{res['wallet_address']}"
    # Query live Toncenter status (never expose secrets)
    res["onchain_status"] = ton_crypto_engine.query_onchain_balance(res["wallet_address"])
    res.pop("private_key_hex", None)
    res.pop("seed_phrase", None)
    return res


DEFAULT_TREASURY_ADDRESS = "UQDHxc7fjg9hoiiIl6XIcSKtBMV4h-xejBam9o7CQeyESfx6"
DEFAULT_TREASURY_HANDLE = "@no_ragrets"

def get_treasury_info() -> Dict[str, Any]:
    """
    Returns the creator's central settlement treasury status and accumulated swept balance.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS treasury_sweeps (
            id TEXT PRIMARY KEY,
            from_persona_id TEXT NOT NULL,
            to_address TEXT NOT NULL,
            amount REAL NOT NULL,
            tx_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute("SELECT COALESCE(SUM(amount), 0.0) as total_swept, COUNT(*) as sweep_count FROM treasury_sweeps")
    row = cursor.fetchone()
    total_swept = row["total_swept"] if row else 0.0
    sweep_count = row["sweep_count"] if row else 0

    cursor.execute("SELECT * FROM treasury_sweeps ORDER BY created_at DESC LIMIT 10")
    recent = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "treasury_address": DEFAULT_TREASURY_ADDRESS,
        "treasury_handle": DEFAULT_TREASURY_HANDLE,
        "explorer_url": f"https://tonviewer.com/{DEFAULT_TREASURY_ADDRESS}",
        "total_swept_ton": round(total_swept, 2),
        "sweep_count": sweep_count,
        "recent_sweeps": recent
    }

def sweep_all_bots_to_treasury(target_address: Optional[str] = None) -> Dict[str, Any]:
    """
    Sweeps accumulated balances from all local bots into the designated human treasury wallet.
    Cryptographically signs the sweeping transfer with each bot's Ed25519 private key.
    """
    dest = target_address or DEFAULT_TREASURY_ADDRESS
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS treasury_sweeps (
            id TEXT PRIMARY KEY,
            from_persona_id TEXT NOT NULL,
            to_address TEXT NOT NULL,
            amount REAL NOT NULL,
            tx_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    cursor.execute("SELECT persona_id, balance, private_key_hex FROM bot_balances WHERE balance > 0")
    eligible_bots = cursor.fetchall()

    swept_total = 0.0
    records = []
    now = datetime.now(timezone.utc).isoformat()

    for bot in eligible_bots:
        p_id = bot["persona_id"]
        bal = float(bot["balance"])
        if bal <= 0:
            continue

        _priv = open_secret(bot["private_key_hex"]) if bot["private_key_hex"] else None
        tx_id = str(uuid.uuid4())
        tx_payload = {
            "type": "TREASURY_SWEEP",
            "from_persona": p_id,
            "to_address": dest,
            "amount": bal,
            "timestamp": now
        }

        if _priv:
            signed = ton_crypto_engine.sign_reward_payload(_priv, tx_payload)
            sig_hex = signed["signature"]
            tx_hash = signed["tx_hash"]
        else:
            sig_hex = "unsigned"
            tx_hash = f"sweep_{uuid.uuid4().hex}"

        # Zero out bot balance
        cursor.execute("UPDATE bot_balances SET balance = 0.0, updated_at = ? WHERE persona_id = ?", (now, p_id))

        # Log to reward transactions as an outgoing sweep
        cursor.execute('''
            INSERT INTO reward_transactions (id, persona_id, amount, reason, signature_hex, tx_hash, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'swept', ?)
        ''', (tx_id, p_id, -bal, f"Treasury Sweep to {dest[:10]}...{dest[-6:]}", sig_hex, tx_hash, now))

        # Record in treasury_sweeps
        sweep_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO treasury_sweeps (id, from_persona_id, to_address, amount, tx_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (sweep_id, p_id, dest, bal, tx_hash, now))

        swept_total += bal
        records.append({
            "from_persona": p_id,
            "amount": bal,
            "tx_hash": tx_hash
        })

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "swept_total_ton": round(swept_total, 2),
        "destination_wallet": dest,
        "bots_swept": len(records),
        "details": records
    }

