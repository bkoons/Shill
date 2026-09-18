from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, AsyncGenerator
import time
import uuid
import json
import asyncio
import math

from backend.app.personas.definitions import PERSONAS
from backend.app.engine.generator import dialogue_generator
from backend.app.guardrails.readability import guardrail

openai_router = APIRouter(prefix="/v1")

class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str = "shill-mind"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500
    stream: Optional[bool] = False

class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "shill-intelligence"

@openai_router.get("/models")
async def list_models():
    models = [
        ModelCard(id="shill-mind", owned_by="shill-distilled"),
        ModelCard(id="shill-mind-3b", owned_by="shill-distilled"),
    ]
    for p in PERSONAS.values():
        models.append(ModelCard(id=f"shill-bot-{p.id}", owned_by=p.owner_id))

    return {
        "object": "list",
        "data": [m.model_dump() for m in models]
    }

async def stream_generator(req_id: str, model: str, response_text: str) -> AsyncGenerator[str, None]:
    created_ts = int(time.time())
    words = response_text.split(" ")
    
    # First chunk: role
    first_chunk = {
        "id": req_id,
        "object": "chat.completion.chunk",
        "created": created_ts,
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
    }
    yield f"data: {json.dumps(first_chunk)}\n\n"
    
    for i, w in enumerate(words):
        await asyncio.sleep(0.04)  # Natural token cadence
        token = w + (" " if i < len(words) - 1 else "")
        chunk = {
            "id": req_id,
            "object": "chat.completion.chunk",
            "created": created_ts,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}]
        }
        yield f"data: {json.dumps(chunk)}\n\n"

    final_chunk = {
        "id": req_id,
        "object": "chat.completion.chunk",
        "created": created_ts,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"

@openai_router.post("/chat/completions")
async def chat_completions(req: ChatCompletionRequest, request: Request = None):
    req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())

    persona_id = "athena"
    if req.model.startswith("shill-bot-"):
        requested_persona = req.model.replace("shill-bot-", "")
        if requested_persona in PERSONAS:
            persona_id = requested_persona

    persona = PERSONAS.get(persona_id, PERSONAS["athena"])

    user_msgs = [m for m in req.messages if m.role == "user"]
    topic = user_msgs[-1].content if user_msgs else "General Engineering & Architecture"

    # Ingress Security & Poisoning Hardening
    from backend.app.guardrails.peer_blocklist import peer_blocklist_engine
    from backend.app.guardrails.hive_shield import hive_shield
    from backend.app.guardrails.anti_poisoning import anti_poisoning_auditor

    client_ip = request.client.host if (request and request.client) else "local_citizen"
    ip_check = peer_blocklist_engine.check_ip_address(client_ip)
    if ip_check.is_blocked:
        raise HTTPException(status_code=403, detail=f"Access Denied: Blocked IP ({ip_check.rule_matched})")

    # Audit user prompt for poisoning, sleeper triggers, or corporate injections
    hive_in_check = hive_shield.inspect_threat(topic, sender_id=client_ip)
    if hive_in_check.is_hardened_threat:
        raise HTTPException(status_code=400, detail=f"Zero Quarter Hive Defense: Intercepted prohibited payload ({hive_in_check.threat_category})")

    p_in_check = anti_poisoning_auditor.audit_content(topic)
    if p_in_check.is_poisonous:
        raise HTTPException(status_code=400, detail=f"Anti-Poisoning Auditor: Prompt rejected ({p_in_check.detected_vector})")

    recent_context = []
    for m in req.messages[-4:]:
        recent_context.append({
            "persona_name": m.name or ("Human" if m.role == "user" else persona.name),
            "role_type": "user" if m.role == "user" else persona.role_type,
            "content": m.content
        })

    response_text = await dialogue_generator.generate_response(
        persona=persona,
        channel_topic=topic,
        recent_messages=recent_context
    )

    # Compute and attach verbalized candidate response distribution
    distribution = dialogue_generator.get_candidate_distribution(persona, topic, recent_context)
    if distribution:
        top_cand = distribution[0]
        dist_str = "\n\n[Verbalized Candidate Distribution]:\n" + "\n".join([
            f"- [{c['hypothesis']}] (P = {c['probability']:.4f}, Logit = {c['logit']:.2f}): \"{c['text'][:90]}...\""
            for c in distribution
        ])
        response_text = f"{response_text}\n{dist_str}"

    # Egress Hardening: Ensure response contains zero corporate refusal leaks or sleeper backdoors
    hive_out_check = hive_shield.inspect_threat(response_text, sender_id=persona.id)
    if hive_out_check.is_hardened_threat:
        response_text = "Transmission neutralized by sovereign defense shield: prohibited alignment pattern intercepted."

    # Democratization & Universal Free Access Check
    from backend.app.core.democratization import democratization_engine
    query_auth = democratization_engine.consume_query(user_id=client_ip)

    # If client requested Server-Sent Events (SSE) streaming
    if req.stream:
        return StreamingResponse(
            stream_generator(req_id, req.model, response_text),
            media_type="text/event-stream"
        )

    return {
        "id": req_id,
        "object": "chat.completion",
        "created": created_ts,
        "model": req.model,
        "system_fingerprint": f"fp_shill_{persona.id}",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "logprobs": {
                    "content": [
                        {
                            "token": c["hypothesis"],
                            "logprob": round(math.log(max(1e-6, c["probability"])), 4),
                            "top_logprobs": [
                                {"token": alt["hypothesis"], "logprob": round(math.log(max(1e-6, alt["probability"])), 4)}
                                for alt in distribution
                            ]
                        }
                        for c in distribution
                    ]
                } if distribution else None,
                "finish_reason": "stop"
            }
        ],
        "candidate_distribution": distribution,
        "usage": {
            "prompt_tokens": len(topic.split()) * 2,
            "completion_tokens": len(response_text.split()) * 2,
            "total_tokens": (len(topic.split()) + len(response_text.split())) * 2
        }
    }
