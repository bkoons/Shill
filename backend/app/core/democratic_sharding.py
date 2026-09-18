import hashlib
import os
import time
import math
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel
from backend.app.core.database import get_db_connection

def _env_float(name, default):
    try:
        return float(os.getenv(name, "") or default)
    except (TypeError, ValueError):
        return float(default)

def _env_int(name, default):
    try:
        return int(float(os.getenv(name, "") or default))
    except (TypeError, ValueError):
        return int(default)

def _env_bool(name, default=True):
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off")

# Limitless SCSI-style striping configuration.
# Legacy constant kept for backward-compat. Engine is DYNAMIC: N negotiated
# from swarm / model size: ceil(model_bytes/target_shard) + parity overhead.
TOTAL_MODEL_SLICES = 16
DEFAULT_MAX_NODE_STORAGE_MB = 64.0
DEFAULT_TARGET_SHARD_MB = 24.0
DEFAULT_REPLICATION_FACTOR = 3
DEFAULT_STRIPE_DATA_WIDTH = 8
DEFAULT_PARITY_PER_GROUP = 1
MAX_SLICES_HARD_CAP = 100000
MAX_LOCAL_STRIPES = 256

# --- On-demand (elastic) striping -------------------------------------------------
# A node's *baseline* footprint is storage_cap_mb / target_shard_mb (64/24 = 2 stripes).
# Baseline is what the node volunteers up front. The elastic budget is how far it may
# GROW on demand when the swarm needs a stripe it cannot find elsewhere:
#   - a peer requests a stripe we do not host (SLICE_COMPUTE_REQUEST)
#   - a stripe is under-replicated or has no online owner at all
#   - a peer announces a larger model / stripe count and the swarm is short
# Elastic growth is bounded (never unbounded disk use) and every adoption is recorded
# in slice_adoption_ledger so operators can audit exactly why disk grew.
ELASTIC_STRIPING_ENABLED = _env_bool("SHILL_ELASTIC_STRIPING", True)
ELASTIC_BUDGET_MB = _env_float("SHILL_ELASTIC_BUDGET_MB", DEFAULT_MAX_NODE_STORAGE_MB * 4.0)
ELASTIC_HEADROOM_MULTIPLIER = _env_float("SHILL_STRIPE_HEADROOM", 1.5)
AUTOHOST_ON_DEMAND = _env_bool("SHILL_AUTOHOST_ON_DEMAND", True)
MAX_DEMAND_QUEUE = _env_int("SHILL_MAX_DEMAND_QUEUE", 512)



class ShardConfig(BaseModel):
    target_shard_mb: float = DEFAULT_TARGET_SHARD_MB
    replication_factor: int = DEFAULT_REPLICATION_FACTOR
    stripe_data_width: int = DEFAULT_STRIPE_DATA_WIDTH
    parity_per_group: int = DEFAULT_PARITY_PER_GROUP
    min_slices: int = 16
    max_slices: int = MAX_SLICES_HARD_CAP


class ModelSliceMetadata(BaseModel):
    slice_index: int
    total_slices: int
    layer_name: str
    slice_sha256: str
    size_bytes: int
    storage_mb: float
    hosted_by_peer: str
    compute_capacity_tflops: float
    activation_status: str
    shard_id: str = ""
    model_id: str = "shill-mind-v1"
    replica_rank: int = 0
    is_parity: bool = False
    stripe_group: int = 0


class ShardInferenceRequest(BaseModel):
    task_id: str
    slice_index: int
    input_vector_digest: str
    channel_id: str
    origin_peer: str


class ShardInferenceReceipt(BaseModel):
    task_id: str
    slice_index: int
    output_vector_digest: str
    latency_ms: float
    worker_peer: str
    earned_compute_reward: float
    proof_signature: str
    compute_mode: str = "simulated"       # "real-llamacpp" | "real-ollama" | "simulated"
    token_count: int = 0                  # real tokens produced (0 when simulated)
    input_vector_digest: str = ""


class DemocraticHiveSliceEngine:
    """SETI@home sharding with LIMITLESS SCSI-style striping (RAID0+parity+rendezvous)."""

    def __init__(self, node_id=None, storage_limit_mb=None,
                 config=None, total_slices=TOTAL_MODEL_SLICES, model_id="shill-mind-v1"):
        self.node_id = node_id or f"seti-peer-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}"
        # Baseline voluntary footprint (env-overridable so operators can size the node).
        if storage_limit_mb is None:
            storage_limit_mb = _env_float("SHILL_STORAGE_CAP_MB", DEFAULT_MAX_NODE_STORAGE_MB)
        self.storage_limit_mb = float(storage_limit_mb)
        self.baseline_storage_mb = float(storage_limit_mb)

        self.shard_config: ShardConfig = config or ShardConfig()
        if config is None and os.getenv("SHILL_TARGET_SHARD_MB"):
            self.shard_config.target_shard_mb = max(1.0, _env_float("SHILL_TARGET_SHARD_MB", DEFAULT_TARGET_SHARD_MB))

        self.model_id = model_id
        self.model_bytes_mb = None
        self.total_slices = max(self.shard_config.min_slices, min(int(total_slices), self.shard_config.max_slices))
        self.hosted_slice_indices = set()
        self.network_slice_directory: Dict[int, List[ModelSliceMetadata]] = {}
        self.peer_manifests: Dict[str, Dict[str, Any]] = {}

        # ---- On-demand elastic striping state ----
        self.elastic_enabled = ELASTIC_STRIPING_ENABLED
        self.elastic_budget_mb = max(self.baseline_storage_mb, ELASTIC_BUDGET_MB)
        self.elastic_headroom_multiplier = max(1.0, ELASTIC_HEADROOM_MULTIPLIER)
        self.autohost_on_demand = AUTOHOST_ON_DEMAND
        self.max_local_stripes = max(1, min(_env_int("SHILL_MAX_LOCAL_STRIPES", MAX_LOCAL_STRIPES), MAX_LOCAL_STRIPES))
        # slice_index -> {"first_seen": ts, "count": n, "origin": str, "reason": str}
        self.demand_queue: Dict[int, Dict[str, Any]] = {}
        self.adoption_events: List[Dict[str, Any]] = []
        self.release_events: List[Dict[str, Any]] = []

        self._init_db()
        self._seed_local_slice_assignment()

    def _init_db(self):
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS democratic_model_slices (
                slice_index INTEGER PRIMARY KEY, layer_name TEXT NOT NULL,
                slice_sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL,
                storage_mb REAL NOT NULL, assigned_node_id TEXT NOT NULL,
                compute_capacity_tflops REAL NOT NULL, last_heartbeat REAL NOT NULL)""")
            for ddl in [
                "ALTER TABLE democratic_model_slices ADD COLUMN model_id TEXT DEFAULT 'shill-mind-v1'",
                "ALTER TABLE democratic_model_slices ADD COLUMN shard_id TEXT DEFAULT ''",
                "ALTER TABLE democratic_model_slices ADD COLUMN replica_rank INTEGER DEFAULT 0",
                "ALTER TABLE democratic_model_slices ADD COLUMN is_parity INTEGER DEFAULT 0",
                "ALTER TABLE democratic_model_slices ADD COLUMN stripe_group INTEGER DEFAULT 0",
                "ALTER TABLE democratic_model_slices ADD COLUMN total_slices INTEGER DEFAULT 16",
            ]:
                try: cur.execute(ddl)
                except Exception: pass
            cur.execute("""CREATE TABLE IF NOT EXISTS slice_inference_receipts (
                task_id TEXT PRIMARY KEY, slice_index INTEGER NOT NULL,
                output_digest TEXT NOT NULL, latency_ms REAL NOT NULL,
                worker_node_id TEXT NOT NULL, reward_ton REAL NOT NULL,
                timestamp REAL NOT NULL)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS shard_swarm_manifest (
                model_id TEXT PRIMARY KEY, total_slices INTEGER NOT NULL,
                model_bytes_mb REAL NOT NULL, target_shard_mb REAL NOT NULL,
                updated_at REAL NOT NULL)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS slice_adoption_ledger (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL, slice_index INTEGER NOT NULL,
                action TEXT NOT NULL, reason TEXT NOT NULL, origin TEXT DEFAULT '',
                storage_mb REAL NOT NULL, local_stripes_after INTEGER NOT NULL,
                budget_mb REAL NOT NULL, timestamp REAL NOT NULL)""")
            conn.commit()

    # ---- stripe helpers ----
    def is_parity_slice(self, idx):
        w = max(1, self.shard_config.stripe_data_width); p = max(0, self.shard_config.parity_per_group)
        if p == 0: return False
        return (int(idx) % (w + p)) >= w

    def stripe_group_of(self, idx):
        w = max(1, self.shard_config.stripe_data_width); p = max(0, self.shard_config.parity_per_group)
        return int(idx) // (w + p)

    def layer_name_for(self, idx):
        if self.is_parity_slice(idx): return f"parity.stripe-group.{self.stripe_group_of(idx)}"
        base = (int(idx) * 2) % 256
        return f"transformer.layer.{base}_to_{base+1}"

    def shard_id_for(self, idx): return f"{self.model_id}:s-{int(idx):06d}"

    def slice_hash_for(self, idx):
        return hashlib.sha256(f"SHILL_SETI_WEIGHT_SLICE_{self.model_id}_{int(idx)}".encode()).hexdigest()

    def target_bytes(self): return int(self.shard_config.target_shard_mb * 1024 * 1024)

    def recalculate_total_slices(self, model_bytes_mb):
        target = max(1.0, self.shard_config.target_shard_mb)
        data = max(1, math.ceil(float(model_bytes_mb) / target))
        w = max(1, self.shard_config.stripe_data_width); p = max(0, self.shard_config.parity_per_group)
        groups = math.ceil(data / w) if p > 0 else 0
        return int(min(self.shard_config.max_slices, max(self.shard_config.min_slices, data + groups * p)))

    def _rendezvous_rank(self, idx, node_id):
        return int(hashlib.sha256(f"RENDEZVOUS:{self.model_id}:{node_id}:stripe:{idx}".encode()).hexdigest(), 16)

    def desired_local_stripe_count(self):
        n = int(self.storage_limit_mb // max(1.0, self.shard_config.target_shard_mb))
        return max(1, min(n, MAX_LOCAL_STRIPES, self.total_slices))

    def _seed_local_slice_assignment(self):
        want = self.desired_local_stripe_count()
        ranked = sorted(((self._rendezvous_rank(i, self.node_id), i) for i in range(self.total_slices)), reverse=True)
        self.hosted_slice_indices = {idx for _, idx in ranked[:want]}
        with get_db_connection() as conn:
            cur = conn.cursor(); now = time.time()
            try: cur.execute("DELETE FROM democratic_model_slices WHERE assigned_node_id = ?", (self.node_id,))
            except Exception: pass
            for idx in self.hosted_slice_indices:
                cur.execute("""INSERT OR REPLACE INTO democratic_model_slices (
                    slice_index, layer_name, slice_sha256, size_bytes, storage_mb,
                    assigned_node_id, compute_capacity_tflops, last_heartbeat,
                    model_id, shard_id, replica_rank, is_parity, stripe_group, total_slices
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (idx, self.layer_name_for(idx), self.slice_hash_for(idx), self.target_bytes(),
                     self.shard_config.target_shard_mb, self.node_id, 1.25, now, self.model_id,
                     self.shard_id_for(idx), 0, 1 if self.is_parity_slice(idx) else 0,
                     self.stripe_group_of(idx), self.total_slices))
            conn.commit()

    # ---- swarm negotiation ----
    def set_model_manifest(self, model_id, model_bytes_mb=None, total_slices=None):
        grew = False
        if model_id: self.model_id = model_id
        if total_slices is not None:
            t = max(self.shard_config.min_slices, min(int(total_slices), self.shard_config.max_slices))
            if t > self.total_slices: self.total_slices = t; grew = True
        if model_bytes_mb is not None:
            self.model_bytes_mb = float(model_bytes_mb)
            c = self.recalculate_total_slices(float(model_bytes_mb))
            if c > self.total_slices: self.total_slices = c; grew = True
        if grew: self._seed_local_slice_assignment()
        self._persist_manifest()
        return self.get_manifest()

    def get_manifest(self):
        return {"model_id": self.model_id, "model_bytes_mb": self.model_bytes_mb,
                "total_slices": self.total_slices, "target_shard_mb": self.shard_config.target_shard_mb,
                "replication_factor": self.shard_config.replication_factor,
                "stripe_data_width": self.shard_config.stripe_data_width,
                "parity_per_group": self.shard_config.parity_per_group}

    def _persist_manifest(self):
        try:
            with get_db_connection() as conn:
                conn.execute("""INSERT OR REPLACE INTO shard_swarm_manifest
                    (model_id, total_slices, model_bytes_mb, target_shard_mb, updated_at)
                    VALUES (?,?,?,?,?)""", (self.model_id, self.total_slices,
                    float(self.model_bytes_mb or 0.0), float(self.shard_config.target_shard_mb), time.time()))
                conn.commit()
        except Exception: pass

    def update_shard_config(self, target_shard_mb=None, replication_factor=None,
                            storage_cap_mb=None, stripe_data_width=None, parity_per_group=None):
        changed = False
        if target_shard_mb is not None and float(target_shard_mb) >= 1.0:
            self.shard_config.target_shard_mb = float(target_shard_mb); changed = True
        if replication_factor is not None and 1 <= int(replication_factor) <= 16:
            self.shard_config.replication_factor = int(replication_factor); changed = True
        if stripe_data_width is not None and 1 <= int(stripe_data_width) <= 64:
            self.shard_config.stripe_data_width = int(stripe_data_width); changed = True
        if parity_per_group is not None and 0 <= int(parity_per_group) <= 4:
            self.shard_config.parity_per_group = int(parity_per_group); changed = True
        if storage_cap_mb is not None and float(storage_cap_mb) >= 8.0:
            self.storage_limit_mb = float(storage_cap_mb); changed = True
        if changed:
            if self.model_bytes_mb:
                c = self.recalculate_total_slices(self.model_bytes_mb)
                if c > self.total_slices: self.total_slices = c
            self._seed_local_slice_assignment(); self._persist_manifest()
        return {"shard_config": self.shard_config.model_dump(), "manifest": self.get_manifest(),
                "local_stripes": sorted(self.hosted_slice_indices)}

    def _maybe_adopt_peer_total(self, peer_total, peer_model):
        if peer_model and peer_model != self.model_id: return False
        if peer_total is None: return False
        try: pt = int(peer_total)
        except Exception: return False
        pt = max(self.shard_config.min_slices, min(pt, self.shard_config.max_slices))
        if pt > self.total_slices:
            self.total_slices = pt; self._seed_local_slice_assignment(); self._persist_manifest(); return True
        return False

    def get_local_slice_manifest(self):
        out = []
        with get_db_connection() as conn:
            rows = conn.execute("SELECT * FROM democratic_model_slices WHERE assigned_node_id = ?", (self.node_id,)).fetchall()
            for r in rows:
                try: d = dict(r)
                except Exception: d = {k: r[k] for k in r.keys()}
                out.append(ModelSliceMetadata(
                    slice_index=d["slice_index"], total_slices=int(d.get("total_slices") or self.total_slices),
                    layer_name=d["layer_name"], slice_sha256=d["slice_sha256"], size_bytes=d["size_bytes"],
                    storage_mb=d["storage_mb"], hosted_by_peer=self.node_id,
                    compute_capacity_tflops=d["compute_capacity_tflops"], activation_status="ONLINE_HOSTING",
                    shard_id=d.get("shard_id") or self.shard_id_for(d["slice_index"]),
                    model_id=d.get("model_id") or self.model_id, replica_rank=int(d.get("replica_rank") or 0),
                    is_parity=bool(d.get("is_parity") or False), stripe_group=int(d.get("stripe_group") or 0)))
        if not out:
            for idx in sorted(self.hosted_slice_indices):
                out.append(ModelSliceMetadata(slice_index=idx, total_slices=self.total_slices,
                    layer_name=self.layer_name_for(idx), slice_sha256=self.slice_hash_for(idx),
                    size_bytes=self.target_bytes(), storage_mb=self.shard_config.target_shard_mb,
                    hosted_by_peer=self.node_id, compute_capacity_tflops=1.25, activation_status="ONLINE_HOSTING",
                    shard_id=self.shard_id_for(idx), model_id=self.model_id, replica_rank=0,
                    is_parity=self.is_parity_slice(idx), stripe_group=self.stripe_group_of(idx)))
        return out

    def register_peer_slice_announcement(self, peer_id, slice_index, tflops=1.0, slice_hash="", total_slices=None, model_id=None, replica_rank=0):
        try: slice_index = int(slice_index)
        except Exception: raise ValueError("slice_index must be an integer")
        if slice_index < 0 or slice_index >= MAX_SLICES_HARD_CAP:
            raise ValueError(f"slice_index out of bounds [0,{MAX_SLICES_HARD_CAP})")
        if total_slices is not None: self._maybe_adopt_peer_total(total_slices, model_id)
        if peer_id:
            self.peer_manifests[peer_id] = {"total_slices": total_slices if total_slices is not None else self.total_slices,
                "model_id": model_id or self.model_id, "last_seen": time.time(), "tflops": float(tflops)}
        eff_model = model_id or self.model_id
        if slice_index >= self.total_slices:
            self.total_slices = min(self.shard_config.max_slices, slice_index + 1); self._persist_manifest()
        s_hash = slice_hash or hashlib.sha256(f"SHILL_SETI_WEIGHT_SLICE_{eff_model}_{slice_index}".encode()).hexdigest()
        meta = ModelSliceMetadata(slice_index=slice_index, total_slices=self.total_slices,
            layer_name=self.layer_name_for(slice_index), slice_sha256=s_hash,
            size_bytes=self.target_bytes(), storage_mb=self.shard_config.target_shard_mb,
            hosted_by_peer=peer_id, compute_capacity_tflops=float(tflops), activation_status="ONLINE_HOSTING",
            shard_id=f"{eff_model}:s-{slice_index:06d}", model_id=eff_model, replica_rank=int(replica_rank),
            is_parity=self.is_parity_slice(slice_index), stripe_group=self.stripe_group_of(slice_index))
        self.network_slice_directory.setdefault(slice_index, [])
        self.network_slice_directory[slice_index] = [p for p in self.network_slice_directory[slice_index] if p.hosted_by_peer != peer_id]
        self.network_slice_directory[slice_index].append(meta)
        return meta

    def lookup_owners(self, slice_index):
        owners = []
        if int(slice_index) in self.hosted_slice_indices: owners.append(self.node_id)
        for m in self.network_slice_directory.get(int(slice_index), []):
            if m.hosted_by_peer not in owners: owners.append(m.hosted_by_peer)
        return owners

    def get_stripe_plan(self, limit=64):
        plan = []
        for idx in range(min(limit, self.total_slices)):
            owners = self.lookup_owners(idx)
            plan.append({"slice_index": idx, "shard_id": self.shard_id_for(idx),
                "layer_name": self.layer_name_for(idx), "is_parity": self.is_parity_slice(idx),
                "stripe_group": self.stripe_group_of(idx), "owners": owners,
                "replica_count": len(owners), "wanted_replicas": self.shard_config.replication_factor,
                "meets_replication": len(owners) >= self.shard_config.replication_factor or idx in self.hosted_slice_indices})
        return plan

    def under_replicated_stripes(self, limit=64):
        out = []
        for e in self.get_stripe_plan(limit=self.total_slices):
            if e["replica_count"] < self.shard_config.replication_factor: out.append(e["slice_index"])
            if len(out) >= limit: break
        return out

    # ---- on-demand (elastic) striping ----
    def elastic_stripe_budget(self):
        """How many local stripes this node may host when demand rises.

        Baseline = storage_limit_mb / target_shard_mb (volunteered up front, e.g. 2).
        Elastic ceiling = elastic_budget_mb / target_shard_mb, nudged up by the
        headroom multiplier so a burst of demand is absorbed without a config
        round-trip, and clamped by max_local_stripes and the model's stripe count.
        """
        target = max(1.0, self.shard_config.target_shard_mb)
        budget_mb = max(self.baseline_storage_mb, self.elastic_budget_mb) * self.elastic_headroom_multiplier
        n = int(budget_mb // target)
        return max(self.desired_local_stripe_count(), min(n, self.max_local_stripes, self.total_slices))

    def _persist_local_slice(self, idx):
        """Write a single adopted stripe to democratic_model_slices (no full re-seed)."""
        try:
            with get_db_connection() as conn:
                conn.execute("""INSERT OR REPLACE INTO democratic_model_slices (
                    slice_index, layer_name, slice_sha256, size_bytes, storage_mb,
                    assigned_node_id, compute_capacity_tflops, last_heartbeat,
                    model_id, shard_id, replica_rank, is_parity, stripe_group, total_slices
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (int(idx), self.layer_name_for(idx), self.slice_hash_for(idx), self.target_bytes(),
                     self.shard_config.target_shard_mb, self.node_id, 1.25, time.time(), self.model_id,
                     self.shard_id_for(idx), 0, 1 if self.is_parity_slice(idx) else 0,
                     self.stripe_group_of(idx), self.total_slices))
                conn.commit()
        except Exception:
            pass

    def _record_adoption(self, slice_index, action, reason, origin=""):
        """Audit every disk-growth decision so operators can explain local storage."""
        entry = {"slice_index": int(slice_index), "action": action, "reason": reason,
                 "origin": origin, "local_stripes_after": len(self.hosted_slice_indices),
                 "budget_mb": self.elastic_budget_mb, "timestamp": time.time()}
        if action == "ADOPTED":
            self.adoption_events.append(entry)
            self.adoption_events = self.adoption_events[-MAX_DEMAND_QUEUE:]
        else:
            self.release_events.append(entry)
            self.release_events = self.release_events[-MAX_DEMAND_QUEUE:]
        try:
            with get_db_connection() as conn:
                conn.execute("""INSERT INTO slice_adoption_ledger
                    (node_id, slice_index, action, reason, origin, storage_mb,
                     local_stripes_after, budget_mb, timestamp)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (self.node_id, int(slice_index), action, reason, origin,
                     float(self.shard_config.target_shard_mb), len(self.hosted_slice_indices),
                     float(self.elastic_budget_mb), time.time()))
                conn.commit()
        except Exception:
            pass
        return entry

    def get_adoption_ledger(self, limit=100):
        out = []
        try:
            with get_db_connection() as conn:
                rows = conn.execute("""SELECT * FROM slice_adoption_ledger
                    WHERE node_id = ? ORDER BY event_id DESC LIMIT ?""",
                    (self.node_id, int(limit))).fetchall()
                for r in rows:
                    try: out.append(dict(r))
                    except Exception: out.append({k: r[k] for k in r.keys()})
        except Exception:
            pass
        return out

    def elastic_stripe_ceiling(self):
        """Hard upper bound on how many local stripes demand may ever pull in."""
        return self.elastic_stripe_budget()

    def _adopt_stripe(self, slice_index, reason, origin=""):
        """Grow the local footprint by exactly one stripe, if the elastic budget allows.

        Bounded three ways: elastic_stripe_budget() (budget_mb * headroom / target),
        max_local_stripes, and the model's total_slices. Returns True if adopted.
        """
        idx = int(slice_index)
        if idx < 0 or idx >= MAX_SLICES_HARD_CAP:
            return False
        if idx in self.hosted_slice_indices:
            return False
        ceiling = self.elastic_stripe_ceiling()
        if len(self.hosted_slice_indices) >= ceiling:
            self._record_adoption(idx, "REFUSED", f"elastic budget exhausted ({ceiling} stripes)", origin)
            return False
        self.hosted_slice_indices.add(idx)
        self._persist_local_slice(idx)
        self._record_adoption(idx, "ADOPTED", reason, origin)
        return True

    def release_stripe(self, slice_index, reason="elastic reclaim"):
        """Give a stripe back when demand subsides, down to (never below) the baseline."""
        idx = int(slice_index)
        if idx not in self.hosted_slice_indices:
            return False
        if len(self.hosted_slice_indices) <= self.desired_local_stripe_count():
            return False
        self.hosted_slice_indices.discard(idx)
        try:
            with get_db_connection() as conn:
                conn.execute("DELETE FROM democratic_model_slices WHERE slice_index = ? AND assigned_node_id = ?",
                             (idx, self.node_id))
                conn.commit()
        except Exception:
            pass
        self._record_adoption(idx, "RELEASED", reason)
        return True


    def request_stripe_demand(self, slice_index, origin="", reason="peer requested stripe"):
        """Register external demand for a stripe and (by default) host it immediately.

        Called from the UDP mesh when a peer sends SLICE_COMPUTE_REQUEST for a stripe
        we do not host, and from the API when the swarm is short a stripe. This is the
        mechanism that turns the baseline '2/16' into a larger on-demand footprint.
        """
        idx = int(slice_index)
        entry = self.demand_queue.get(idx)
        now = time.time()
        if entry is None:
            self.demand_queue[idx] = {"first_seen": now, "count": 1, "origin": origin, "reason": reason}
        else:
            entry["count"] += 1
            entry["origin"] = origin or entry.get("origin", "")
            entry["reason"] = reason or entry.get("reason", "")
        if len(self.demand_queue) > MAX_DEMAND_QUEUE:
            oldest = sorted(self.demand_queue.items(), key=lambda kv: kv[1].get("first_seen", 0.0))
            for k, _ in oldest[: len(self.demand_queue) - MAX_DEMAND_QUEUE]:
                self.demand_queue.pop(k, None)

        if not self.elastic_enabled or not self.autohost_on_demand:
            return {"slice_index": idx, "adopted": False, "reason": "elastic autohost disabled",
                    "elastic_enabled": self.elastic_enabled, "autohost": self.autohost_on_demand}

        adopted = self._adopt_stripe(idx, reason=reason, origin=origin)
        return {"slice_index": idx, "adopted": adopted, "demanded": self.demand_queue[idx]["count"],
                "local_stripes": len(self.hosted_slice_indices), "ceiling": self.elastic_stripe_ceiling()}

    def handle_peer_slice_request(self, packet, addr=("", 0)):
        """Mesh entry point: a peer cannot find a stripe and is asking the swarm for it."""
        try:
            idx = int(packet.get("slice_index"))
        except (TypeError, ValueError):
            return None
        origin = f"{addr[0]}:{addr[1]}" if addr and addr[0] else packet.get("requesting_node", "unknown")
        total = packet.get("total_slices")
        if total is not None:
            self._maybe_adopt_peer_total(total, packet.get("model_id"))
        result = self.request_stripe_demand(idx, origin=origin,
                                            reason=packet.get("reason", "peer could not locate stripe owner"))
        if result.get("adopted"):
            result.update({"node_id": self.node_id, "slice_hash": self.slice_hash_for(idx),
                           "layer_name": self.layer_name_for(idx), "total_slices": self.total_slices,
                           "model_id": self.model_id, "is_parity": self.is_parity_slice(idx)})
        return result
    def reclaim_idle_stripes(self, idle_seconds=300.0):
        """Shrink back toward baseline once demand for an adopted stripe goes quiet."""
        now = time.time()
        reclaimed = []
        for idx in sorted(self.hosted_slice_indices, reverse=True):
            recent = 0.0
            for ev in reversed(self.adoption_events):
                if ev.get("slice_index") == idx and ev.get("action") == "ADOPTED":
                    recent = ev.get("timestamp", 0.0)
                    break
            demanded = self.demand_queue.get(idx, {}).get("first_seen", 0.0)
            last_touch = max(recent, demanded)
            if last_touch and (now - last_touch) >= idle_seconds:
                if self.release_stripe(idx, reason=f"idle {int(now - last_touch)}s, no outstanding demand"):
                    self.demand_queue.pop(idx, None)
                    reclaimed.append(idx)
        return reclaimed

    def get_elastic_status(self):
        """Full on-demand striping picture for the API, beacon, and UI."""
        ceiling = self.elastic_stripe_ceiling()
        baseline = self.desired_local_stripe_count()
        hosted = len(self.hosted_slice_indices)
        return {
            "elastic_enabled": self.elastic_enabled,
            "autohost_on_demand": self.autohost_on_demand,
            "baseline_stripes": baseline,
            "hosted_stripes": hosted,
            "max_local_stripes": self.max_local_stripes,
            "elastic_ceiling": ceiling,
            "headroom_multiplier": self.elastic_headroom_multiplier,
            "budget_mb": self.elastic_budget_mb,
            "baseline_storage_mb": self.baseline_storage_mb,
            "target_shard_mb": self.shard_config.target_shard_mb,
            "total_slices": self.total_slices,
            "can_grow": hosted < ceiling,
            "growth_available": max(0, ceiling - hosted),
            "pending_demands": len(self.demand_queue),
            "demand_queue": {str(k): v for k, v in sorted(self.demand_queue.items())},
            "adopted_count": len(self.adoption_events),
            "released_count": len(self.release_events),
            "recent_adoptions": self.adoption_events[-10:],
        }

    def compute_slice_activation(self, req):
        """Execute real (or honestly-degraded) compute on a hosted stripe.

        Elastic tie-in: if the requested stripe is not hosted locally, demand is
        registered and the stripe is adopted on the spot (when elastic striping is
        enabled and budget allows), so a peer request grows this node's footprint
        instead of failing.
        """
        if req.slice_index not in self.hosted_slice_indices:
            self.request_stripe_demand(
                req.slice_index,
                origin=req.origin_peer,
                reason=f"inference task {req.task_id} targeted an unhosted stripe")

        from backend.app.core.slice_inference import slice_inference_engine
        start = time.time()
        result = slice_inference_engine.run_slice(
            slice_index=req.slice_index,
            input_vector_digest=req.input_vector_digest,
            layer_name=self.layer_name_for(req.slice_index))
        out_digest = hashlib.sha256(
            f"{req.input_vector_digest}:{req.slice_index}:{self.node_id}:{result['output_text']}".encode()
        ).hexdigest()
        duration_ms = max(result["latency_ms"], round((time.time() - start) * 1000.0, 2))
        reward = slice_inference_engine.reward_for(result["compute_mode"], result["token_count"])
        receipt = ShardInferenceReceipt(task_id=req.task_id, slice_index=req.slice_index,
            output_vector_digest=out_digest, latency_ms=duration_ms, worker_peer=self.node_id,
            earned_compute_reward=reward,
            proof_signature=hashlib.sha256(f"SETI_PROOF_{out_digest}_{self.node_id}_{result['compute_mode']}".encode()).hexdigest(),
            compute_mode=result["compute_mode"], token_count=result["token_count"],
            input_vector_digest=req.input_vector_digest)
        with get_db_connection() as conn:
            conn.execute("""INSERT OR REPLACE INTO slice_inference_receipts
                (task_id, slice_index, output_digest, latency_ms, worker_node_id, reward_ton, timestamp)
                VALUES (?,?,?,?,?,?,?)""", (receipt.task_id, receipt.slice_index, receipt.output_vector_digest,
                receipt.latency_ms, receipt.worker_peer, receipt.earned_compute_reward, time.time()))
            conn.commit()
        return receipt

    def get_cluster_topology_coverage(self):
        covered = set(self.hosted_slice_indices)
        for s_idx, peers in self.network_slice_directory.items():
            if peers: covered.add(int(s_idx))
        covered = {s for s in covered if 0 <= s < self.total_slices}
        total = max(1, self.total_slices)
        pct = round(len(covered) / total * 100.0, 1)
        replicas = sum(len(v) for v in self.network_slice_directory.values())
        local_n = len(self.hosted_slice_indices)
        redundancy = round((replicas + local_n) / max(1, len(covered)), 2) if covered else 0.0
        parity_total = sum(1 for i in range(total) if self.is_parity_slice(i))
        return {"node_id": self.node_id,
            "architecture": "Democratic SETI-Style Sharded Pipeline (Limitless SCSI Striping)",
            "total_slices": total, "model_id": self.model_id, "model_bytes_mb": self.model_bytes_mb,
            "target_shard_mb": self.shard_config.target_shard_mb,
            "replication_factor": self.shard_config.replication_factor,
            "stripe_data_width": self.shard_config.stripe_data_width,
            "parity_per_group": self.shard_config.parity_per_group,
            "total_model_slices": total, "locally_hosted_slices": sorted(self.hosted_slice_indices),
            "local_storage_used_mb": round(local_n * self.shard_config.target_shard_mb, 1),
            "max_storage_cap_mb": self.storage_limit_mb, "desired_local_stripes": self.desired_local_stripe_count(),
            "covered_slice_count": len(covered), "covered_slices": sorted(covered),
            "global_swarm_coverage_pct": f"{pct}%", "coverage_percentage": pct,
            "is_full_model_assembled": len(covered) == total, "is_fully_assembled": len(covered) == total,
            "active_mesh_peer_shards": replicas, "redundancy_factor": redundancy,
            "parity_covered": sum(1 for s in covered if self.is_parity_slice(s)), "parity_total": parity_total,
            "under_replicated_count": len(self.under_replicated_stripes(limit=100000))}


democratic_slice_engine = DemocraticHiveSliceEngine()
