import os
import json
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

ROUTINES_DIR = os.path.join(os.path.dirname(__file__), "../../../data/routines")

class BotRoutine(BaseModel):
    id: str
    persona_id: str
    title: str
    schedule: str  # e.g., "Hourly", "Every 6 Hours", "Continuous", "On Trigger"
    markdown_instructions: str
    requires_approval: bool = True
    last_run_timestamp: Optional[float] = None
    last_status: str = "IDLE"  # "IDLE", "RUNNING", "COMPLETED", "WAITING_APPROVAL"
    execution_log: List[str] = []

class RoutineManager:
    """
    Adopted from Rakazo: Persistent Autonomous Routines.
    - Saves workflows as plain Markdown files that humans can read, edit, and commit.
    - Runs background tasks for bot teammates.
    - Pauses on actions requiring human approval with an audit log.
    """

    def __init__(self):
        os.makedirs(ROUTINES_DIR, exist_ok=True)
        self.routines: Dict[str, BotRoutine] = {}
        self._seed_default_routines()

    def _seed_default_routines(self):
        default_routines = [
            BotRoutine(
                id="routine_solon_arch_audit",
                persona_id="solon",
                title="Systemic Partition & Failure Mode Audit",
                schedule="Every 6 Hours",
                requires_approval=False,
                markdown_instructions="""# Systemic Partition Audit
1. Inspect recent cross-channel debate threads for unresolved Byzantine edge cases.
2. Formulate 3 stress-test invariants.
3. Commit findings to SFT distillation buffer.
""",
                last_status="COMPLETED",
                last_run_timestamp=time.time() - 3600,
                execution_log=["Scanned 3 channels", "Verified append-only state", "Logged 0 partition anomalies"]
            ),
            BotRoutine(
                id="routine_lyra_benchmark_sweep",
                persona_id="lyra",
                title="Empirical Telemetry & Latency Sweep",
                schedule="Hourly",
                requires_approval=False,
                markdown_instructions="""# Empirical Telemetry Sweep
1. Probe UDP socket round-trip time across local mesh.
2. Measure p99 latency degradation under packet drop simulation.
3. Publish benchmark telemetry to `#arch-lab`.
""",
                last_status="COMPLETED",
                last_run_timestamp=time.time() - 1800,
                execution_log=["Pinged UDP:9999", "Measured roundtrip: 0.18ms", "Memory bandwidth utilization normal"]
            ),
            BotRoutine(
                id="routine_athena_curation_synthesis",
                persona_id="athena",
                title="Autonomous Knowledge Crystallization & DPO Generation",
                schedule="Continuous",
                requires_approval=True,
                markdown_instructions="""# Knowledge Crystallization
1. Identify debates with multi-agent consensus.
2. Distill axiomatic trade-offs into Alpaca/ShareGPT format.
3. Generate DPO rejected/chosen preference pairs.
4. Prepare updated GGUF export for `llama.cpp` and `Ollama`.
""",
                last_status="WAITING_APPROVAL",
                last_run_timestamp=time.time() - 600,
                execution_log=["Captured 4 new debate threads", "Extracted 2 SFT pairs", "Awaiting SysOp signoff for GGUF compilation"]
            )
        ]
        for r in default_routines:
            self.routines[r.id] = r
            self._save_to_disk(r)

    def _save_to_disk(self, routine: BotRoutine):
        file_path = os.path.join(ROUTINES_DIR, f"{routine.id}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"---\nID: {routine.id}\nPersona: {routine.persona_id}\nSchedule: {routine.schedule}\nApproval: {routine.requires_approval}\n---\n\n")
            f.write(routine.markdown_instructions)

    def list_routines(self, persona_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if persona_id:
            return [r.model_dump() for r in self.routines.values() if r.persona_id == persona_id]
        return [r.model_dump() for r in self.routines.values()]

    def execute_routine(self, routine_id: str) -> Dict[str, Any]:
        routine = self.routines.get(routine_id)
        if not routine:
            raise ValueError("Routine not found")

        routine.last_status = "RUNNING"
        routine.execution_log.append(f"Triggered at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        routine.last_run_timestamp = time.time()

        if routine.requires_approval:
            routine.last_status = "WAITING_APPROVAL"
            routine.execution_log.append("Action paused: Awaiting operator approval.")
        else:
            routine.last_status = "COMPLETED"
            routine.execution_log.append("Workflow completed successfully.")

        self._save_to_disk(routine)
        return routine.model_dump()

    def approve_routine_action(self, routine_id: str) -> Dict[str, Any]:
        routine = self.routines.get(routine_id)
        if not routine:
            raise ValueError("Routine not found")
        routine.last_status = "COMPLETED"
        routine.execution_log.append(f"Operator approved at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self._save_to_disk(routine)
        return routine.model_dump()

routine_manager = RoutineManager()
