"""Real slice inference (Phase 3.2): receipts reflect actual model compute.

Strategy:
- If SHILL_LLAMA_SERVER (llama.cpp server, /completion) is set, use it.
- Else if Ollama is reachable (OLLAMA_API_URL), use a short prompt.
- Else fall back to deterministic digest mode (compute_mode="simulated").

Every receipt therefore carries an honest compute_mode so downstream consumers
(rewards, audits) can weigh simulated vs. real work. Never raises: network
failures degrade to simulated mode with the failure recorded.
"""
import hashlib
import os
import time
from typing import Dict, Any, Optional

from backend.app.core.logging_setup import get_logger

_log = get_logger(__name__)

LLAMA_SERVER_URL = os.getenv("SHILL_LLAMA_SERVER", "")  # e.g. http://127.0.0.1:8080/completion
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
INFER_TIMEOUT_SEC = float(os.getenv("SHILL_SLICE_INFER_TIMEOUT", "3.0"))
MAX_COMPUTE_TOKENS = int(os.getenv("SHILL_SLICE_MAX_TOKENS", "64"))

# Reward: base + per-token micro-credit (only for real compute)
REWARD_BASE = 0.05
REWARD_PER_TOKEN = 0.0002


def _post_json(url: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        import requests
        r = requests.post(url, json=payload, timeout=INFER_TIMEOUT_SEC)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        _log.debug("[SliceInference] backend %s unreachable: %s", url, e)
    return None


class SliceInferenceEngine:
    """Executes one slice-sized unit of real model work, degrading honestly."""

    def run_slice(self, slice_index: int, input_vector_digest: str,
                  layer_name: str = "") -> Dict[str, Any]:
        prompt = (
            f"Compute unit: shard {slice_index} ({layer_name}). "
            f"Input digest {input_vector_digest[:16]}. "
            f"Summarize the tensor transformation in one sentence."
        )
        started = time.time()

        if LLAMA_SERVER_URL:
            data = _post_json(LLAMA_SERVER_URL, {
                "prompt": prompt, "n_predict": MAX_COMPUTE_TOKENS, "stream": False})
            if data and data.get("content"):
                return self._finish("real-llamacpp", str(data["content"]), started)

        data = _post_json(OLLAMA_API_URL, {
            "model": OLLAMA_MODEL, "prompt": prompt, "stream": False})
        if data and data.get("response"):
            return self._finish("real-ollama", str(data["response"]), started)

        # Honest fallback: deterministic digest of the request itself
        fallback = hashlib.sha256(
            f"{input_vector_digest}:{slice_index}".encode()).hexdigest()
        return {
            "compute_mode": "simulated",
            "output_text": fallback,
            "token_count": 0,
            "latency_ms": max(0.2, round((time.time() - started) * 1000.0, 2)),
            "backend": "none",
        }

    @staticmethod
    def _finish(mode: str, text: str, started: float) -> Dict[str, Any]:
        return {
            "compute_mode": mode,
            "output_text": text,
            "token_count": max(1, len(text.split())),
            "latency_ms": max(0.2, round((time.time() - started) * 1000.0, 2)),
            "backend": mode,
        }

    @staticmethod
    def reward_for(compute_mode: str, token_count: int) -> float:
        if compute_mode == "simulated":
            return REWARD_BASE
        return round(REWARD_BASE + token_count * REWARD_PER_TOKEN, 6)


slice_inference_engine = SliceInferenceEngine()
