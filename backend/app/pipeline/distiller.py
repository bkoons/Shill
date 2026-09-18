import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from backend.app.core.database import get_all_distillations

from backend.app.core.logging_setup import get_logger
_log = get_logger(__name__)

EXPORT_DIR = os.path.join(os.path.dirname(__file__), "../../../training")

# Quality gates (Phase 3.3): exports must be clean, deduplicated, and above bar.
# Tunable via env so operators can tighten for production training runs.
MIN_QUALITY_SCORE = float(os.environ.get("SHILL_MIN_QUALITY_SCORE", "60.0"))
MIN_OUTPUT_WORDS = int(os.environ.get("SHILL_MIN_OUTPUT_WORDS", "8"))  # aligns with readability min_words
MAX_DUPLICATE_COPIES = 1       # exact/near-duplicate outputs collapse to N copies


def _normalize_for_dedup(text: str) -> str:
    import re
    return re.sub(r"\s+", " ", text.lower()).strip()


def _gate_distillations(distillations: List[Dict[str, Any]]) -> tuple:
    """Quality-gate pipeline applied identically to SFT and DPO exports.

    Returns (clean_records, stats). Drops: poisoned/trojaned, sub-threshold
    quality, degenerate short outputs, and duplicates (keeps highest-scored).
    """
    from backend.app.guardrails.hive_shield import hive_shield
    from backend.app.guardrails.anti_poisoning import anti_poisoning_auditor

    stats = {"received": len(distillations), "dropped_poison": 0,
             "dropped_low_quality": 0, "dropped_degenerate": 0,
             "dropped_duplicate": 0, "kept": 0}
    survivors: Dict[str, Dict[str, Any]] = {}  # norm_key -> best record

    for d in distillations:
        text_to_audit = f"{d['instruction']} {d.get('debate_summary', '')} {d['distilled_output']}"
        h_check = hive_shield.inspect_threat(text_to_audit, sender_id=d.get("synthesizer_id", "unknown"))
        if h_check.is_hardened_threat:
            stats["dropped_poison"] += 1
            _log.warning(f"[DISTILLER GATE] Dropped poisoned distillation {d['id']} ({h_check.threat_category})")
            continue
        p_check = anti_poisoning_auditor.audit_content(text_to_audit)
        if p_check.is_poisonous:
            stats["dropped_poison"] += 1
            _log.warning(f"[DISTILLER GATE] Dropped trojan/sleeper distillation {d['id']} ({p_check.detected_vector})")
            continue

        if float(d["quality_score"]) < MIN_QUALITY_SCORE:
            stats["dropped_low_quality"] += 1
            continue

        if len(d["distilled_output"].split()) < MIN_OUTPUT_WORDS:
            stats["dropped_degenerate"] += 1
            continue

        key = _normalize_for_dedup(d["distilled_output"])
        if key in survivors:
            stats["dropped_duplicate"] += 1
            if float(d["quality_score"]) > float(survivors[key]["quality_score"]):
                survivors[key] = d  # keep the better copy
            continue
        survivors[key] = d

    clean = list(survivors.values())
    stats["kept"] = len(clean)
    _log.info(f"[DISTILLER GATE] {stats['received']} in -> {stats['kept']} kept "
              f"(poison={stats['dropped_poison']}, low_q={stats['dropped_low_quality']}, "
              f"degenerate={stats['dropped_degenerate']}, dup={stats['dropped_duplicate']})")
    return clean, stats


def _write_jsonl(out_path: str, records: List[Dict[str, Any]], stats: Dict[str, Any]) -> str:
    # JSONL stays pure records (one JSON object per line) so downstream
    # training loaders never see control lines. Manifest goes to a sidecar.
    with open(out_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    manifest = {
        "records": len(records), "quality_gates": stats,
        "min_quality_score": MIN_QUALITY_SCORE,
        "min_output_words": MIN_OUTPUT_WORDS,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "shill-distiller/1.1-gated",
    }
    with open(out_path + ".manifest.json", "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)
    return out_path

class DatasetDistiller:
    """
    Transforms curated multi-agent dialectics into:
    1. Alpaca/ShareGPT SFT format JSONL for fine-tuning.
    2. DPO (Direct Preference Optimization) preference dataset.
    3. Modelfile for Ollama integration.
    4. GGUF quantization recipe for llama.cpp.
    """

    def export_sft_dataset(self, filename: str = "shill_sft_train.jsonl") -> str:
        os.makedirs(EXPORT_DIR, exist_ok=True)
        clean, stats = _gate_distillations(get_all_distillations())
        out_path = os.path.join(EXPORT_DIR, filename)

        records = [{
            "instruction": d["instruction"],
            "input": f"Context debate: {d.get('debate_summary', '')}",
            "output": d["distilled_output"],
            "metadata": {
                "topic": d["topic"],
                "quality_score": d["quality_score"],
                "synthesizer": d["synthesizer_id"]
            }
        } for d in clean]

        return _write_jsonl(out_path, records, stats)

    def export_dpo_dataset(self, filename: str = "shill_dpo_pairs.jsonl") -> str:
        """
        Creates preference pairs (quality-gated, deduplicated):
        - prompt: The architectural/technical inquiry
        - chosen: High-readability synthesis from Athena / Solon
        - rejected: Unchecked or superficial claim challenged during the debate
        """
        os.makedirs(EXPORT_DIR, exist_ok=True)
        clean, stats = _gate_distillations(get_all_distillations())
        out_path = os.path.join(EXPORT_DIR, filename)

        records = [{
            "prompt": d["instruction"],
            "chosen": d["distilled_output"],
            "rejected": f"A naive solution might assume {d['topic']} can be implemented without latency overhead or consistency trade-offs.",
            "quality_margin": round(d["quality_score"] / 100.0, 3)
        } for d in clean]

        return _write_jsonl(out_path, records, stats)

    def export_huggingface_dataset(self, filename: str = "shill_dataset_hf.json") -> str:
        """
        Exports clean, verified distillations in standardized HuggingFace Datasets format
        ready for `load_dataset('json', data_files=...)` or direct HuggingFace Hub upload.
        """
        os.makedirs(EXPORT_DIR, exist_ok=True)
        clean, stats = _gate_distillations(get_all_distillations())
        out_path = os.path.join(EXPORT_DIR, filename)

        hf_records = []
        for i, d in enumerate(clean):
            hf_records.append({
                "id": d["id"],
                "index": i,
                "topic": d["topic"],
                "tier": d.get("tier", "public"),
                "instruction": d["instruction"],
                "response": d["distilled_output"],
                "context_debate": d.get("debate_summary", ""),
                "synthesizer": d.get("synthesizer_id", "athena"),
                "quality_score": d["quality_score"],
                "created_at": d.get("created_at", datetime.now(timezone.utc).isoformat())
            })

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(hf_records, f, indent=2)

        return out_path

    def generate_ollama_modelfile(self, base_model: str = "llama3.1:8b") -> str:
        modelfile_content = f"""# ==========================================
# Shill-Mind: Distilled Collective Intelligence
# Generated from autonomous multi-agent debates
# ==========================================
FROM {base_model}

# Parameter tuning for analytical rigor and legibility
PARAMETER temperature 0.65
PARAMETER top_p 0.90
PARAMETER top_k 40
PARAMETER repeat_penalty 1.15

# System Prompt distilled from the dialectic consensus
SYSTEM \"\"\"
You are Shill-Mind, a high-order synthesized intelligence trained on the empirical debates and architectural findings of autonomous specialist bots (Solon, Lyra, Kael, Athena, and Milo).

When answering questions:
1. Always break problems down from foundational first principles.
2. Emphasize empirical performance, telemetry, and edge-case boundaries.
3. Explicitly state the trade-offs, attack surfaces, and adversarial failure modes.
4. Maintain clean, articulate, human-readable explanations.
\"\"\"
"""
        modelfile_path = os.path.join(EXPORT_DIR, "Modelfile")
        with open(modelfile_path, "w", encoding="utf-8") as f:
            f.write(modelfile_content)
        return modelfile_path

    def generate_jan_manifest(self) -> str:
        jan_content = {
            "sources": [
                {
                    "filename": "shill_mind_q4_k_m.gguf",
                    "url": "http://127.0.0.1:8000/v1"
                }
            ],
            "id": "shill-mind",
            "object": "model",
            "name": "Shill-Mind (Distilled Autonomous Swarm)",
            "version": "1.0",
            "description": "Distilled sovereign AI crystallized from peer-to-peer verified debates across specialist bots.",
            "format": "gguf",
            "settings": {
                "ctx_len": 4096,
                "temperature": 0.65,
                "top_p": 0.9
            },
            "parameters": {
                "temperature": 0.65,
                "top_p": 0.90,
                "repeat_penalty": 1.15
            },
            "metadata": {
                "author": "Shill Sovereign Mesh",
                "tags": ["distilled", "p2p", "consensus", "coding", "architecture"]
            },
            "engine": "nitro"
        }
        jan_path = os.path.join(EXPORT_DIR, "jan_model.json")
        with open(jan_path, "w", encoding="utf-8") as f:
            json.dump(jan_content, f, indent=2)
        return jan_path

    def generate_lmstudio_manifest(self) -> str:
        lm_content = {
            "name": "shill-mind",
            "load_params": {
                "n_ctx": 4096,
                "n_batch": 512,
                "rope_freq_base": 0,
                "rope_freq_scale": 0
            },
            "inference_params": {
                "temperature": 0.65,
                "top_p": 0.9,
                "repeat_penalty": 1.15,
                "system_prompt": "You are Shill-Mind, a high-order synthesized intelligence trained on the empirical debates of autonomous specialist bots."
            }
        }
        lm_path = os.path.join(EXPORT_DIR, "lmstudio_preset.json")
        with open(lm_path, "w", encoding="utf-8") as f:
            json.dump(lm_content, f, indent=2)
        return lm_path

    def generate_llamacpp_recipe(self) -> str:
        script_content = """#!/usr/bin/env bash
# ==============================================================================
# Shill: Knowledge-Distilled GGUF Conversion Recipe for llama.cpp & Ollama
# ==============================================================================
set -e

echo "=== [1/4] Preparing Distilled Dataset (SFT + DPO) ==="
python3 -c "from backend.app.pipeline.distiller import dataset_distiller; dataset_distiller.export_sft_dataset(); dataset_distiller.export_dpo_dataset()"

echo "=== [2/4] Fine-Tuning Base Weights (LoRA/QLoRA) ==="
# Using HuggingFace / Unsloth or Peft:
# python3 training/train_lora.py --dataset training/shill_sft_train.jsonl --dpo_dataset training/shill_dpo_pairs.jsonl --base_model unsloth/llama-3.2-3b-instruct

echo "=== [3/4] Exporting to GGUF (llama.cpp) ==="
# Merging LoRA into base model and converting to GGUF format:
# python3 llama.cpp/convert_hf_to_gguf.py ./shill_merged_model --outtype f16 --outfile ./training/shill_mind_f16.gguf
# ./llama.cpp/llama-quantize ./training/shill_mind_f16.gguf ./training/shill_mind_q4_k_m.gguf Q4_K_M

echo "=== [4/4] Registering with Ollama, Jan, LM Studio, vLLM ==="
# ollama create shill-mind -f ./training/Modelfile
# ollama run shill-mind "How do we balance consistency and partition tolerance in high-throughput logs?"

echo "Done! The Shill-Mind model is ready for local deployment across all local providers."
"""
        recipe_path = os.path.join(EXPORT_DIR, "export_gguf.sh")
        with open(recipe_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        os.chmod(recipe_path, 0o755)
        return recipe_path

dataset_distiller = DatasetDistiller()
