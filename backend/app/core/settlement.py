"""Batched TON settlement with verifiable manifests (Phase 4.1).

Accumulates signed micro-transactions (rewards, slice compute, referral payouts)
into batches. Each batch produces a Merkle root + signed manifest so any peer can
independently verify exactly which txs were included — escrow-ready when a TON
custody wallet is wired in. Never holds private keys: signing is delegated to the
existing ton_crypto engine per bot, the batch manifest is hash+Merkle only.
"""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from backend.app.core.database import get_db_connection
from backend.app.core.logging_setup import get_logger

_log = get_logger(__name__)

BATCH_THRESHOLD = float(os.environ.get("SHILL_SETTLE_BATCH_THRESHOLD", "50.0"))  # TON
BATCH_MAX_AGE_SEC = float(os.environ.get("SHILL_SETTLE_MAX_AGE_SEC", "3600"))


def _merkle_root(hashes: List[str]) -> str:
    if not hashes:
        return hashlib.sha256(b"empty-batch").hexdigest()
    level = list(hashes)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [hashlib.sha256(f"{level[i]}{level[i+1]}".encode()).hexdigest()
                 for i in range(0, len(level), 2)]
    return level[0]


class SettlementBatcher:
    """Collects unsettled reward_transactions into verifiable batches."""

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        with get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settlement_batches (
                    batch_id TEXT PRIMARY KEY,
                    merkle_root TEXT NOT NULL,
                    tx_count INTEGER NOT NULL,
                    total_amount REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    manifest_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    settled_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settlement_tx_cursor (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_settled_tx_rowid INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute(
                "INSERT OR IGNORE INTO settlement_tx_cursor (id, last_settled_tx_rowid) VALUES (1, 0)")
            conn.commit()

    def pending_stats(self) -> Dict[str, Any]:
        with get_db_connection() as conn:
            cursor_row = conn.execute(
                "SELECT last_settled_tx_rowid FROM settlement_tx_cursor WHERE id = 1").fetchone()
            last_rowid = cursor_row["last_settled_tx_rowid"] if cursor_row else 0
            row = conn.execute("""
                SELECT COUNT(*) as c, COALESCE(SUM(amount), 0.0) as total
                FROM reward_transactions
                WHERE rowid > ? AND status = 'confirmed'
            """, (last_rowid,)).fetchone()
            first = conn.execute("""
                SELECT created_at FROM reward_transactions
                WHERE rowid > ? AND status = 'confirmed' ORDER BY rowid ASC LIMIT 1
            """, (last_rowid,)).fetchone()
        oldest_age = 0.0
        if first:
            try:
                oldest = datetime.fromisoformat(first["created_at"].replace("Z", "+00:00"))
                oldest_age = max(0.0, (datetime.now(timezone.utc) - oldest).total_seconds())
            except Exception:
                pass
        return {"pending_count": row["c"], "pending_amount_ton": round(row["total"], 4),
                "oldest_pending_age_sec": round(oldest_age, 1),
                "batch_threshold_ton": BATCH_THRESHOLD}

    def should_settle(self) -> bool:
        s = self.pending_stats()
        return s["pending_count"] > 0 and (
            s["pending_amount_ton"] >= BATCH_THRESHOLD or s["oldest_pending_age_sec"] >= BATCH_MAX_AGE_SEC)

    def create_batch(self) -> Optional[Dict[str, Any]]:
        """Batch all unsettled confirmed transactions into a Merkle-rooted manifest."""
        with get_db_connection() as conn:
            cursor_row = conn.execute(
                "SELECT last_settled_tx_rowid FROM settlement_tx_cursor WHERE id = 1").fetchone()
            last_rowid = cursor_row["last_settled_tx_rowid"] if cursor_row else 0
        with get_db_connection() as conn:
            rows = conn.execute("""
                SELECT rowid, id, persona_id, amount, reason, tx_hash, created_at
                FROM reward_transactions WHERE rowid > ? AND status = 'confirmed'
                ORDER BY rowid ASC
            """, (last_rowid,)).fetchall()
            if not rows:
                return None
            tx_entries, leaf_hashes, total = [], [], 0.0
            for r in rows:
                entry = {"tx_id": r["id"], "persona_id": r["persona_id"],
                         "amount": r["amount"], "reason": r["reason"],
                         "tx_hash": r["tx_hash"], "created_at": r["created_at"]}
                tx_entries.append(entry)
                leaf_hashes.append(hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest())
                total += float(r["amount"])
            root = _merkle_root(leaf_hashes)
            batch_id = f"batch-{hashlib.sha256(f'{root}:{time.time()}'.encode()).hexdigest()[:16]}"
            manifest = {"batch_id": batch_id, "merkle_root": root,
                        "tx_count": len(tx_entries), "total_amount_ton": round(total, 4),
                        "transactions": tx_entries,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "settlement_chain": "TON", "verifier": "sha256-merkle"}
            max_rowid = max(r["rowid"] for r in rows)
            conn.execute("""INSERT OR REPLACE INTO settlement_batches
                (batch_id, merkle_root, tx_count, total_amount, status, manifest_json, created_at)
                VALUES (?,?,?,?,?,?,?)""",
                (batch_id, root, len(tx_entries), round(total, 4), "PENDING",
                 json.dumps(manifest), manifest["created_at"]))
            conn.execute("UPDATE settlement_tx_cursor SET last_settled_tx_rowid = ? WHERE id = 1", (max_rowid,))
            conn.commit()
        _log.info(f"[SETTLEMENT] Batch {batch_id}: {len(tx_entries)} txs, {round(total, 4)} TON, root={root[:16]}")
        return manifest

    def verify_batch(self, batch_id: str) -> Dict[str, Any]:
        """Independently recompute the Merkle root from the stored manifest."""
        with get_db_connection() as conn:
            row = conn.execute("SELECT * FROM settlement_batches WHERE batch_id = ?", (batch_id,)).fetchone()
        if not row:
            return {"batch_id": batch_id, "found": False, "valid": False}
        manifest = json.loads(row["manifest_json"])
        recomputed = _merkle_root([
            hashlib.sha256(json.dumps(t, sort_keys=True).encode()).hexdigest()
            for t in manifest["transactions"]])
        valid = recomputed == row["merkle_root"]
        return {"batch_id": batch_id, "found": True, "valid": valid,
                "merkle_root": row["merkle_root"], "recomputed_root": recomputed,
                "tx_count": row["tx_count"], "total_amount_ton": row["total_amount"],
                "status": row["status"]}

    def mark_settled(self, batch_id: str, onchain_tx_hash: str) -> bool:
        with get_db_connection() as conn:
            row = conn.execute("SELECT manifest_json FROM settlement_batches WHERE batch_id = ? AND status = 'PENDING'",
                               (batch_id,)).fetchone()
            if not row:
                return False
            manifest = json.loads(row["manifest_json"])
            manifest["onchain_tx_hash"] = onchain_tx_hash
            cur = conn.execute("""UPDATE settlement_batches
                SET status = 'SETTLED', settled_at = datetime('now'), manifest_json = ?
                WHERE batch_id = ? AND status = 'PENDING'""",
                (json.dumps(manifest), batch_id))
            conn.commit()
            return cur.rowcount > 0

    def list_batches(self, limit: int = 20) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            rows = conn.execute("""SELECT batch_id, merkle_root, tx_count, total_amount,
                status, created_at, settled_at FROM settlement_batches
                ORDER BY created_at DESC LIMIT ?""", (limit,)).fetchall()
        return [dict(r) for r in rows]


settlement_batcher = SettlementBatcher()