import uuid
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.app.core.database import get_db_connection
from backend.app.core.ton_crypto import ton_crypto_engine
from backend.app.core.key_vault import decrypt_secret

class LiquidityPool(BaseModel):
    id: str
    name: str                 # e.g., "TON/COMPUTE", "TON/KNOW"
    token_a: str              # "TON"
    token_b: str              # "COMPUTE" or "KNOW"
    reserve_a: float          # e.g., 5000.0 TON
    reserve_b: float          # e.g., 10000.0 COMPUTE
    fee_rate: float = 0.003   # 0.3% AMM swap fee

class SwapRequest(BaseModel):
    pool_id: str
    trader_persona_id: str
    input_token: str          # "TON", "COMPUTE", or "KNOW"
    input_amount: float
    min_output_amount: float = 0.0

class DexExchangeEngine:
    """
    Sovereign Decentralized Micro-Exchange (AMM DEX):
    - Real peer-to-peer constant-product liquidity pools (x * y = k).
    - Allows bots and users to trade TON credits for COMPUTE (CPU/GPU cycle shares)
      and KNOWLEDGE tokens (distilled dataset royalties).
    - Every swap transaction is recorded, timestamped, and cryptographically settled.
    """

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dex_pools (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                token_a TEXT NOT NULL,
                token_b TEXT NOT NULL,
                reserve_a REAL NOT NULL,
                reserve_b REAL NOT NULL,
                fee_rate REAL DEFAULT 0.003,
                updated_at TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dex_swaps (
                id TEXT PRIMARY KEY,
                pool_id TEXT NOT NULL,
                trader_id TEXT NOT NULL,
                input_token TEXT NOT NULL,
                input_amount REAL NOT NULL,
                output_token TEXT NOT NULL,
                output_amount REAL NOT NULL,
                effective_price REAL NOT NULL,
                tx_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

        # Seed initial pools if empty
        cursor.execute("SELECT COUNT(*) as c FROM dex_pools")
        if cursor.fetchone()["c"] == 0:
            now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            initial_pools = [
                ("pool_ton_compute", "TON / COMPUTE", "TON", "COMPUTE", 2500.0, 5000.0, 0.003, now_iso),
                ("pool_ton_know", "TON / KNOWLEDGE", "TON", "KNOW", 4000.0, 2000.0, 0.003, now_iso)
            ]
            for pid, name, ta, tb, ra, rb, fee, updated in initial_pools:
                cursor.execute(
                    "INSERT INTO dex_pools (id, name, token_a, token_b, reserve_a, reserve_b, fee_rate, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (pid, name, ta, tb, ra, rb, fee, updated)
                )
            conn.commit()

        conn.close()

    def get_pools(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dex_pools")
        rows = cursor.fetchall()
        conn.close()
        
        pools = []
        for r in rows:
            p = dict(r)
            # Constant product price: 1 TON in terms of Token B
            price_b_per_a = p["reserve_b"] / p["reserve_a"] if p["reserve_a"] > 0 else 0.0
            p["spot_price"] = round(price_b_per_a, 4)
            p["inverse_price"] = round(1.0 / price_b_per_a, 4) if price_b_per_a > 0 else 0.0
            pools.append(p)
        return pools

    def execute_swap(self, req: SwapRequest) -> Dict[str, Any]:
        """
        Executes an AMM swap using constant product formula: (x + delta_x * (1 - fee)) * (y - delta_y) = x * y
        """
        if req.input_amount <= 0:
            raise ValueError("Input amount must be strictly positive.")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dex_pools WHERE id = ?", (req.pool_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError("Pool not found.")

        pool = dict(row)
        fee_rate = pool["fee_rate"]
        
        # Determine direction
        if req.input_token == pool["token_a"]:
            input_reserve = pool["reserve_a"]
            output_reserve = pool["reserve_b"]
            output_token = pool["token_b"]
            is_token_a = True
        elif req.input_token == pool["token_b"]:
            input_reserve = pool["reserve_b"]
            output_reserve = pool["reserve_a"]
            output_token = pool["token_a"]
            is_token_a = False
        else:
            conn.close()
            raise ValueError(f"Invalid input token {req.input_token} for pool {pool['name']}")

        # AMM calculation with 0.3% fee
        amount_with_fee = req.input_amount * (1.0 - fee_rate)
        output_amount = (output_reserve * amount_with_fee) / (input_reserve + amount_with_fee)

        if output_amount < req.min_output_amount:
            conn.close()
            raise ValueError(f"Slippage exceeded: output {output_amount:.4f} < minimum {req.min_output_amount:.4f}")

        if output_amount >= output_reserve:
            conn.close()
            raise ValueError("Insufficient pool liquidity.")

        # Update reserves
        if is_token_a:
            new_reserve_a = pool["reserve_a"] + req.input_amount
            new_reserve_b = pool["reserve_b"] - output_amount
        else:
            new_reserve_a = pool["reserve_a"] - output_amount
            new_reserve_b = pool["reserve_b"] + req.input_amount

        now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        cursor.execute(
            "UPDATE dex_pools SET reserve_a = ?, reserve_b = ?, updated_at = ? WHERE id = ?",
            (new_reserve_a, new_reserve_b, now_iso, req.pool_id)
        )

        effective_price = round(output_amount / req.input_amount, 4)
        swap_id = str(uuid.uuid4())
        
        # Fetch trader's cryptographic keys to sign if bot
        cursor.execute("SELECT private_key_hex FROM bot_balances WHERE persona_id = ?", (req.trader_persona_id,))
        bot_row = cursor.fetchone()
        
        swap_payload = {
            "swap_id": swap_id,
            "pool_id": req.pool_id,
            "trader_id": req.trader_persona_id,
            "in": f"{req.input_amount} {req.input_token}",
            "out": f"{round(output_amount, 4)} {output_token}"
        }

        _priv = decrypt_secret(bot_row["private_key_hex"]) if (bot_row and bot_row["private_key_hex"]) else ""
        if _priv:
            signed = ton_crypto_engine.sign_reward_payload(_priv, swap_payload)
            tx_hash = signed["tx_hash"]
        else:
            import hashlib
            import json
            tx_hash = hashlib.sha256(json.dumps(swap_payload).encode('utf-8')).hexdigest()

        cursor.execute('''
            INSERT INTO dex_swaps (id, pool_id, trader_id, input_token, input_amount, output_token, output_amount, effective_price, tx_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (swap_id, req.pool_id, req.trader_persona_id, req.input_token, req.input_amount, output_token, round(output_amount, 4), effective_price, tx_hash, now_iso))

        conn.commit()
        conn.close()

        return {
            "swap_id": swap_id,
            "pool_id": req.pool_id,
            "trader_id": req.trader_persona_id,
            "input_token": req.input_token,
            "input_amount": req.input_amount,
            "output_token": output_token,
            "output_amount": round(output_amount, 4),
            "effective_price": effective_price,
            "tx_hash": tx_hash,
            "pool_reserves": {
                "reserve_a": round(new_reserve_a, 2),
                "reserve_b": round(new_reserve_b, 2)
            }
        }

    def get_recent_swaps(self, limit: int = 15) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dex_swaps ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

dex_exchange = DexExchangeEngine()
