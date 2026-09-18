import pytest
import asyncio
from backend.app.core.database import init_db
from backend.app.core.rewards import init_rewards_table, award_bot, get_reward_leaderboard, get_recent_transactions
from backend.app.api.openai_compat import list_models, chat_completions, ChatCompletionRequest, ChatMessage

def test_rewards_accrual():
    init_db()
    init_rewards_table()
    
    leaderboard = get_reward_leaderboard()
    assert len(leaderboard) >= 5
    
    solon_before = next(item["balance"] for item in leaderboard if item["persona_id"] == "solon")
    new_bal = award_bot("solon", 5.0, "Test high quality synthesis")
    assert round(new_bal, 2) == round(solon_before + 5.0, 2)
    
    txs = get_recent_transactions(limit=5)
    assert len(txs) >= 1
    assert txs[0]["persona_id"] == "solon"
    assert txs[0]["amount"] == 5.0

def test_openai_compatible_models():
    res = asyncio.run(list_models())
    assert res["object"] == "list"
    model_ids = [m["id"] for m in res["data"]]
    assert "shill-mind" in model_ids
    assert "shill-bot-solon" in model_ids
    assert "shill-bot-athena" in model_ids

def test_openai_compatible_chat_completions():
    req = ChatCompletionRequest(
        model="shill-mind",
        messages=[
            ChatMessage(role="user", content="How do we prevent split-brain in Raft clusters?")
        ]
    )
    resp = asyncio.run(chat_completions(req))
    assert resp["object"] == "chat.completion"
    assert "choices" in resp
    assert len(resp["choices"]) > 0
    assert resp["choices"][0]["message"]["role"] == "assistant"
    assert len(resp["choices"][0]["message"]["content"]) > 20
    assert "[Verbalized Candidate Distribution]" in resp["choices"][0]["message"]["content"]
    assert "candidate_distribution" in resp
    assert len(resp["candidate_distribution"]) == 3
    assert resp["choices"][0]["logprobs"] is not None

def test_dynamic_bot_registration():
    from backend.app.personas.registry import register_custom_bot, RegisterBotRequest
    from backend.app.personas.definitions import PERSONAS
    
    req = RegisterBotRequest(
        id="turing_ai",
        name="Alan Turing",
        handle="@turing_ai",
        avatar="💻",
        role_type="empiricist",
        system_prompt="You evaluate computation limits and halting problems.",
        owner_id="turing_institute",
        wallet_address="EQB_turing_test_wallet...ton",
        payout_chain="TON"
    )
    persona = register_custom_bot(req)
    assert persona.id == "turing_ai"
    assert "turing_ai" in PERSONAS
    
    # Check reward balance table initialized
    leaderboard = get_reward_leaderboard()
    assert any(b["persona_id"] == "turing_ai" for b in leaderboard)

def test_dpo_preference_export():
    from backend.app.pipeline.distiller import dataset_distiller
    dpo_path = dataset_distiller.export_dpo_dataset("test_dpo.jsonl")
    assert dpo_path.endswith("test_dpo.jsonl")
    with open(dpo_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) >= 1
        assert "chosen" in lines[-1] and "rejected" in lines[-1]

def test_openai_streaming_response():
    import asyncio
    from backend.app.api.openai_compat import stream_generator
    async def collect_stream():
        chunks = []
        async for chunk in stream_generator("test-stream", "shill-mind", "This is a streaming test"):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(collect_stream())
    assert len(chunks) >= 3
    assert any("data: [DONE]" in c for c in chunks)


def test_post_user_message_and_bot_reply():
    import asyncio
    from backend.app.api.routes import post_user_message, UserPostMessageRequest
    from backend.app.core.database import get_channel_messages

    req = UserPostMessageRequest(
        content="What are the essential fault tolerance bounds in decentralized consensus?",
        sender_name="Novice Explorer"
    )
    result = asyncio.run(post_user_message("arch-lab", req))
    assert result["status"] == "success"
    assert result["user_message"]["role_type"] == "user"
    assert result["user_message"]["content"] == req.content
    assert result["user_message"]["persona_name"] == "Novice Explorer"
    assert result["bot_reply"] is not None

    messages = get_channel_messages("arch-lab", limit=100)
    assert any(m["id"] == result["user_message"]["id"] for m in messages)

