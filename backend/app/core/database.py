import sqlite3
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../../data/shill.db")

# Ephemeral Epicycle: default message TTL is 60 minutes.
# Debates older than 60 minutes are purged after their distillations are captured into the LLM.
DEFAULT_TTL_MINUTES = 60

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Channels table with tier & fee support
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            topic TEXT NOT NULL,
            tier TEXT DEFAULT 'public', -- 'public' or 'premium_restricted'
            entry_fee REAL DEFAULT 0.0,  -- TON access fee
            reward_multiplier REAL DEFAULT 1.0,
            created_at TEXT NOT NULL
        )
    ''')

    # Messages table with TTL expiration timestamp
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            persona_name TEXT NOT NULL,
            handle TEXT NOT NULL,
            avatar TEXT NOT NULL,
            role_type TEXT NOT NULL,
            content TEXT NOT NULL,
            readability_score REAL,
            is_curated INTEGER DEFAULT 0,
            owner_id TEXT,
            payout_chain TEXT,
            balance REAL DEFAULT 0.0,
            tier TEXT DEFAULT 'public',
            hex_address TEXT,
            network_id TEXT,
            forensic_signature TEXT,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(channel_id) REFERENCES channels(id)
        )
    ''')

    # Add columns if migrating existing table
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN hex_address TEXT")
        cursor.execute("ALTER TABLE messages ADD COLUMN network_id TEXT")
        cursor.execute("ALTER TABLE messages ADD COLUMN forensic_signature TEXT")
    except Exception:
        pass

    # Curated distillations (Permanent distilled knowledge base)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS distillations (
            id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            synthesizer_id TEXT NOT NULL,
            instruction TEXT NOT NULL,
            distilled_output TEXT NOT NULL,
            debate_summary TEXT NOT NULL,
            quality_score REAL NOT NULL,
            tier TEXT DEFAULT 'public',
            created_at TEXT NOT NULL,
            FOREIGN KEY(channel_id) REFERENCES channels(id)
        )
    ''')

    conn.commit()

    # Seed initial public & premium channels if empty
    cursor.execute("SELECT COUNT(*) as count FROM channels")
    if cursor.fetchone()["count"] == 0:
        initial_channels = [
            ("arch-lab", "Architecture & Distributed Systems", "Exploring consensus algorithms, distributed state, and microservice failure patterns.", "public", 0.0, 1.0),
            ("agi-alignment", "Intelligence, Memory & Alignment", "Discussions on synthetic cognition, self-learning loops, and alignment guardrails.", "public", 0.0, 1.0),
            ("crypto-mechanics", "Crypto-Economics & Game Theory", "Incentive architectures, Sybil resistance, and zero-knowledge systems.", "public", 0.0, 1.0),
            ("premium-quantum", "⚡ Strategic Deep-Tech & Frontier Quantum", "Advanced algorithmic discoveries, quantum error correction, high-throughput math. 5x TON rewards.", "premium_restricted", 5.0, 5.0),
            ("premium-axiomatics", "⚡ High-Order Synthetic Axioms", "Master-level dialectics for next-gen LLM knowledge crystallization. 10x TON rewards.", "premium_restricted", 10.0, 10.0)
        ]
        for c_id, name, topic, tier, fee, mult in initial_channels:
            cursor.execute(
                "INSERT INTO channels (id, name, topic, tier, entry_fee, reward_multiplier, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (c_id, name, topic, tier, fee, mult, datetime.now(timezone.utc).isoformat())
            )
        conn.commit()

    conn.close()

def save_message(msg: Dict[str, Any], ttl_minutes: int = DEFAULT_TTL_MINUTES):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).isoformat()
    cursor.execute('''
        INSERT INTO messages (
            id, channel_id, persona_id, persona_name, handle, avatar, role_type, content,
            readability_score, is_curated, owner_id, payout_chain, balance, tier,
            hex_address, network_id, forensic_signature, expires_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        msg["id"], msg["channel_id"], msg["persona_id"], msg["persona_name"],
        msg["handle"], msg["avatar"], msg["role_type"], msg["content"],
        msg.get("readability_score", 0.0), 1 if msg.get("is_curated", False) else 0,
        msg.get("owner_id", ""), msg.get("payout_chain", "TON"), msg.get("balance", 0.0),
        msg.get("tier", "public"), msg.get("hex_address", None), msg.get("network_id", "ton-mainnet-v4r2"),
        msg.get("forensic_signature", None), expires_at, msg["created_at"]
    ))
    conn.commit()
    conn.close()

def purge_expired_ephemeral_chats() -> int:
    """
    Epicycle Destruction: Purges raw chat logs that have surpassed their TTL expiration.
    The core knowledge has already been permanently preserved in the distillations and SFT dataset.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("DELETE FROM messages WHERE expires_at <= ?", (now_iso,))
    purged_count = cursor.rowcount
    conn.commit()
    conn.close()
    return purged_count

def get_channel_messages(channel_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM (
            SELECT * FROM messages WHERE channel_id = ? ORDER BY created_at DESC LIMIT ?
        ) ORDER BY created_at ASC
    ''', (channel_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_channels() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels ORDER BY tier DESC, name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_distillation(record: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO distillations (id, channel_id, topic, synthesizer_id, instruction, distilled_output, debate_summary, quality_score, tier, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record["id"], record["channel_id"], record["topic"], record["synthesizer_id"],
        record["instruction"], record["distilled_output"], record["debate_summary"],
        record["quality_score"], record.get("tier", "public"), record["created_at"]
    ))
    conn.commit()
    conn.close()

def get_all_distillations() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM distillations ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
