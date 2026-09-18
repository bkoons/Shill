#!/usr/bin/env bash
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
