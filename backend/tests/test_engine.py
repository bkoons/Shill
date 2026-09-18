import pytest
from backend.app.core.database import init_db, get_channels, save_message, get_channel_messages, save_distillation, get_all_distillations
from backend.app.personas.definitions import PERSONAS
from backend.app.engine.turn_manager import turn_manager
from backend.app.pipeline.distiller import dataset_distiller

def test_database_and_channels_init():
    init_db()
    channels = get_channels()
    assert len(channels) >= 3
    channel_ids = [c["id"] for c in channels]
    assert "arch-lab" in channel_ids

def test_turn_manager_persona_selection():
    msgs = [
        {"persona_name": "Solon", "role_type": "anchor"}
    ]
    next_persona = turn_manager.select_next_persona(msgs)
    assert next_persona.name != "Solon"
    assert next_persona.role_type in ["challenger", "empiricist", "provocateur"]

def test_distillation_export():
    init_db()
    distillation = {
        "id": "test-distill-1",
        "channel_id": "arch-lab",
        "topic": "Architecture & Distributed Systems",
        "synthesizer_id": "athena",
        "instruction": "Synthesize the trade-offs of Raft vs Paxos.",
        "distilled_output": "Raft achieves identical safety to Multi-Paxos while drastically reducing state machine complexity.",
        "debate_summary": "Debated latency vs developer comprehension.",
        "quality_score": 68.5,
        "created_at": "2026-09-17T00:00:00"
    }
    save_distillation(distillation)
    
    path = dataset_distiller.export_sft_dataset("test_sft.jsonl")
    assert path.endswith("test_sft.jsonl")
    
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) >= 1
        assert "Synthesize the trade-offs" in lines[-1]
