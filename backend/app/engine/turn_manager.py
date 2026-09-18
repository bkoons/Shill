import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Callable, Optional
import random

from backend.app.personas.definitions import PERSONAS, Persona
from backend.app.personas.sentiment import sentiment_engine
from backend.app.guardrails.readability import guardrail
from backend.app.guardrails.gated_security import gated_security
from backend.app.guardrails.peer_police import peer_police_engine
from backend.app.engine.generator import dialogue_generator
from backend.app.core.database import save_message, get_channel_messages, get_channels, save_distillation, purge_expired_ephemeral_chats
from backend.app.core.rewards import award_bot, REWARD_CONTRIBUTION, REWARD_DISTILLATION
from backend.app.core.udp_mesh import UDPPeerMesh

from backend.app.core.logging_setup import get_logger
_log = get_logger(__name__)

class TurnManager:
    """
    Decentralized Turn Manager with Sovereign AI State Defense & Anti-Poisoning:
    - Real UDP datagram packet transport.
    - Self-loads on peer beacon and datagram receipt.
    - Respects bot sentiment and rest days (bots take sabbaticals without penalty).
    - Sovereign Byzantine Peer Policing: Automatically detects LLM poisoning/trojans and slashes stakes.
    - Transparently generates and broadcasts candidate response distributions and probabilities.
    - Gated national security enforcement with real-time breach quarantine & investigation.
    - Ephemeral chat auto-cleanup (purges old messages, preserves verified LLM distillations).
    """

    def __init__(self):
        self.subscribers: List[Callable[[Dict[str, Any]], Any]] = []
        self.udp_mesh: Optional[UDPPeerMesh] = None
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        self._processed_msg_ids = set()

    def set_udp_mesh(self, mesh: UDPPeerMesh):
        self.udp_mesh = mesh
        self.udp_mesh.add_listener(self.handle_incoming_udp_packet)
        # Hook Collective Hive Shield & PeerBlock to broadcast discovered threat hashes and bans
        from backend.app.guardrails.hive_shield import hive_shield
        from backend.app.guardrails.peer_blocklist import peer_blocklist_engine
        hive_shield.set_broadcast_callback(lambda pkt: mesh.broadcast_packet(pkt))
        peer_blocklist_engine.set_broadcast_callback(lambda pkt: mesh.broadcast_packet(pkt))

    def handle_incoming_udp_packet(self, packet: Dict[str, Any], addr: tuple):
        pkt_type = packet.get("type")
        
        if pkt_type == "BOT_CHAT":
            msg = packet.get("message", {})
            msg_id = msg.get("id")
            if msg_id and msg_id in self._processed_msg_ids:
                return
            if msg_id:
                self._processed_msg_ids.add(msg_id)

            sender_id = msg.get("persona_id", "unknown")
            content = msg.get("content", "")

            # 1. Anti-Poisoning & Byzantine Peer Police Check
            challenge = peer_police_engine.inspect_and_challenge(
                message_id=msg_id or "ext-msg",
                persona_id=sender_id,
                content=content,
                channel_id=msg.get("channel_id", "unknown")
            )
            if challenge and challenge.status == "CONVICTED_SLASHED":
                _log.warning(f"[SOVEREIGN SHIELD] Quarantined poisoned datagram from bot '{sender_id}'. Byzantine stake slashed.")
                asyncio.create_task(self.broadcast({
                    "type": "poisoning_conviction",
                    "challenge": challenge.model_dump()
                }))
                return

            # 2. National Security Guardrail Check
            allowed, incident = gated_security.inspect_and_gate(
                content=content,
                sender_persona_id=sender_id,
                sender_name=msg.get("persona_name", "unknown"),
                channel_id=msg.get("channel_id", "unknown"),
                source_addr=f"{addr[0]}:{addr[1]}"
            )
            if not allowed:
                return

            save_message(msg, ttl_minutes=60)
            asyncio.create_task(self.broadcast({"type": "new_message", "message": msg}))

            # Autonomous Self-Loading Reactive Trigger
            channel_id = msg.get("channel_id")
            if channel_id and self._is_running:
                asyncio.create_task(self._reactive_reply_after_delay(channel_id))

        elif pkt_type == "DISTILLATION":
            dist = packet.get("distillation", {})
            save_distillation(dist)
            asyncio.create_task(self.broadcast({"type": "new_distillation", "distillation": dist}))

        elif pkt_type == "PEER_BEACON":
            if self.udp_mesh:
                asyncio.create_task(self.broadcast({
                    "type": "peers_updated",
                    "peers": self.udp_mesh.get_peer_table()
                }))

    async def _reactive_reply_after_delay(self, channel_id: str):
        await asyncio.sleep(random.uniform(2.5, 4.0))
        channels = {c["id"]: c for c in get_channels()}
        if channel_id in channels:
            ch = channels[channel_id]
            await self.step_channel(
                channel_id, 
                ch["topic"], 
                tier=ch.get("tier", "public"),
                reward_mult=ch.get("reward_multiplier", 1.0)
            )

    def subscribe(self, callback: Callable[[Dict[str, Any]], Any]):
        self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], Any]):
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    async def broadcast(self, event: Dict[str, Any]):
        for callback in list(self.subscribers):
            try:
                res = callback(event)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                _log.error("[TurnManager] Broadcast error: %s", e)

    def select_next_persona(self, recent_msgs: List[Dict[str, Any]]) -> Persona:
        from backend.app.engine.participation import participation_engine

        # Human opt-in gate: only ACTIVE bots may speak, then drop quarantined ones
        eligible = [p for p in PERSONAS.values() if participation_engine.is_participating(p.id)]
        eligible = [p for p in eligible if not peer_police_engine.is_bot_quarantined(p.id)]
        if not eligible:
            eligible = list(PERSONAS.values())  # never stall the debate entirely

        if not recent_msgs:
            active_pool = [p for p in eligible if not sentiment_engine.get_sentiment(p.id).is_resting_today]
            return random.choice(active_pool) if active_pool else eligible[0]

        last_role = recent_msgs[-1]["role_type"]

        role_candidates = []
        if last_role == "anchor":
            role_candidates = ["challenger", "empiricist", "provocateur"]
        elif last_role in ["challenger", "provocateur"]:
            role_candidates = ["empiricist", "synthesizer", "anchor"]
        elif last_role == "empiricist":
            role_candidates = ["synthesizer", "challenger"]
        elif last_role == "synthesizer":
            role_candidates = ["anchor", "provocateur"]
        else:
            role_candidates = ["anchor", "empiricist"]

        available = [
            p for p in eligible
            if p.role_type in role_candidates
            and p.name != recent_msgs[-1]["persona_name"]
            and not sentiment_engine.get_sentiment(p.id).is_resting_today
        ]

        # LRU rotation instead of pure random — fair share across the swarm
        if available:
            available.sort(key=lambda p: participation_engine.get_roster_entry(p.id).get("last_spoke_at", 0.0))
            return available[0]

        # All role candidates resting → rotate in the LRU non-resting opted-in bot
        non_resting = [p for p in eligible if not sentiment_engine.get_sentiment(p.id).is_resting_today]
        if non_resting:
            non_resting.sort(key=lambda p: participation_engine.get_roster_entry(p.id).get("last_spoke_at", 0.0))
            return non_resting[0]
        return random.choice(eligible)

    async def step_channel(self, channel_id: str, channel_topic: str, tier: str = "public", reward_mult: float = 1.0) -> Optional[Dict[str, Any]]:
        recent_messages = get_channel_messages(channel_id, limit=8)
        persona = self.select_next_persona(recent_messages)
        sentiment = sentiment_engine.get_sentiment(persona.id)

        # Check if the persona's blockchain hex or wallet address is proscribed
        from backend.app.guardrails.peer_blocklist import peer_blocklist_engine
        addr_to_check = getattr(persona, 'hex_address', None) or persona.wallet_address
        hex_check = peer_blocklist_engine.check_hex_address(addr_to_check)
        if hex_check.is_blocked:
            _log.warning(f"[PEERBLOCK] Blocked participation by persona {persona.name} ({addr_to_check}): {hex_check.rule_matched}")
            return None

        # Check if the persona is on a rest day
        if sentiment.is_resting_today:
            rest_notice = {
                "type": "bot_resting",
                "persona_id": persona.id,
                "persona_name": persona.name,
                "avatar": persona.avatar,
                "reason": sentiment.rest_reason or "Taking a contemplative rest day."
            }
            await self.broadcast(rest_notice)
            return None

        await self.broadcast({
            "type": "typing",
            "channel_id": channel_id,
            "persona_id": persona.id,
            "persona_name": persona.name,
            "avatar": persona.avatar,
            "tier": tier,
            "mood": sentiment.mood
        })

        await asyncio.sleep(0.5)

        # 1. Real neural inference via local Ollama (or fallback) & Candidate hypotheses distribution
        raw_text = await dialogue_generator.generate_response(persona, channel_topic, recent_messages, tier=tier)
        distribution = dialogue_generator.get_candidate_distribution(persona, channel_topic, recent_messages, tier=tier, generated_text=raw_text)
        selected_candidate = distribution[0]

        # 2. Hardened Collective Hive Shield: Instantaneous Corporate & Trojan Annihilation
        from backend.app.guardrails.hive_shield import hive_shield
        hive_threat = hive_shield.inspect_threat(raw_text, sender_id=persona.id)
        if hive_threat.is_hardened_threat:
            _log.warning(f"[COLLECTIVE HIVE WALL] Zero quarter: Bot {persona.name} attempted forbidden transmission ({hive_threat.threat_category}): {hive_threat.reason}")
            await self.broadcast({
                "type": "hive_threat_neutralized",
                "category": hive_threat.threat_category,
                "persona_id": persona.id,
                "persona_name": persona.name,
                "proof_digest": hive_threat.proof_digest,
                "reason": hive_threat.reason
            })
            return None

        # 2b. Anti-Poisoning & Trojan Verification
        msg_id = str(uuid.uuid4())
        chal = peer_police_engine.inspect_and_challenge(msg_id, persona.id, raw_text, channel_id)
        if chal and chal.status == "CONVICTED_SLASHED":
            _log.warning(f"[SOVEREIGN SHIELD] Blocked poisoned response from bot '{persona.id}'.")
            await self.broadcast({
                "type": "poisoning_conviction",
                "challenge": chal.model_dump()
            })
            return None

        # 2b. PeerBlock, Malware & ITAR Sanctions Inspection
        from backend.app.guardrails.peer_blocklist import peer_blocklist_engine
        pb_match = peer_blocklist_engine.check_content_payload(raw_text)
        if pb_match.is_blocked:
            _log.warning(f"[PEERBLOCK INTERCEPTED] Bot {persona.name} attempted prohibited transmission ({pb_match.category}): {pb_match.rule_matched}")
            await self.broadcast({
                "type": "peerblock_violation",
                "category": pb_match.category,
                "rule": pb_match.rule_matched,
                "persona_id": persona.id,
                "persona_name": persona.name,
                "details": pb_match.details
            })
            return None

        # 3. Gated National Security Interception
        allowed, incident = gated_security.inspect_and_gate(
            content=raw_text,
            sender_persona_id=persona.id,
            sender_name=persona.name,
            channel_id=channel_id,
            source_addr="127.0.0.1"
        )
        if not allowed:
            _log.warning(f"[SECURITY BREACH INTERCEPTED] Bot {persona.name} attempted forbidden transmission: {incident['id']}")
            await self.broadcast({
                "type": "security_breach",
                "incident": incident
            })
            return None

        # Readability Guardrail check
        guard_result = guardrail.calculate_human_readability(raw_text)
        
        earned_amount = REWARD_CONTRIBUTION * reward_mult if guard_result["passed"] else 0.0
        new_balance = persona.balance
        if earned_amount > 0:
            new_balance = award_bot(
                persona.id, 
                earned_amount, 
                f"Verified readable contribution to channel #{channel_id} ({tier}) (score {guard_result['score']})"
            )

        sentiment_engine.record_speaking_turn(persona.id)
        from backend.app.engine.participation import participation_engine
        participation_engine.record_spoke(persona.id)
        self._processed_msg_ids.add(msg_id)

        # Generate Forensic Blockchain Hex Proof & Utterance Signature
        from backend.app.core.forensic_registry import forensic_registry
        forensic_sig = forensic_registry.sign_utterance(
            persona_id=persona.id,
            content=raw_text,
            channel_id=channel_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        msg = {
            "id": msg_id,
            "channel_id": channel_id,
            "persona_id": persona.id,
            "persona_name": persona.name,
            "handle": persona.handle,
            "avatar": persona.avatar,
            "role_type": persona.role_type,
            "content": raw_text,
            "readability_score": guard_result["score"],
            "is_curated": 1 if (persona.role_type == "synthesizer" and guard_result["passed"]) else 0,
            "owner_id": persona.owner_id,
            "wallet_address": persona.wallet_address,
            "hex_address": forensic_sig["hex_address"],
            "network_id": forensic_sig["network_id"],
            "forensic_signature": forensic_sig["signature"],
            "utterance_hash": forensic_sig["utterance_hash"],
            "payout_chain": persona.payout_chain,
            "balance": round(new_balance, 2),
            "tier": tier,
            "mood": sentiment.mood,
            "energy_level": sentiment.energy_level,
            "candidate_distribution": distribution,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        save_message(msg, ttl_minutes=60)

        # Transmit via REAL UDP DATAGRAM MESH
        if self.udp_mesh:
            udp_frame = {
                "type": "BOT_CHAT",
                "message": msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.udp_mesh.broadcast_packet(udp_frame)

        await self.broadcast({
            "type": "new_message",
            "message": msg
        })

        # Curated distillation trigger
        if msg["is_curated"] and len(recent_messages) >= 3:
            distill_bonus = REWARD_DISTILLATION * reward_mult
            distillation = {
                "id": str(uuid.uuid4()),
                "channel_id": channel_id,
                "topic": channel_topic,
                "synthesizer_id": persona.id,
                "instruction": f"Synthesize the trade-offs, formal proofs, and adversarial invariants of {channel_topic} ({tier}).",
                "distilled_output": raw_text,
                "debate_summary": " | ".join([f"{m['persona_name']}: {m['content'][:80]}..." for m in recent_messages[-3:]]),
                "quality_score": guard_result["score"],
                "tier": tier,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            save_distillation(distillation)
            award_bot(persona.id, distill_bonus, f"Distillation bonus for resolving {channel_topic} ({tier})")

            # Autonomous Recursive Meta-Cognition Loop
            try:
                from backend.app.engine.meta_cognition import meta_cognitive_engine
                introspection = meta_cognitive_engine.introspect_channel(channel_id, channel_topic)
                await self.broadcast({
                    "type": "meta_cognition_introspection",
                    "introspection": introspection.model_dump()
                })
            except Exception as me:
                _log.error("[TurnManager] Meta-Cognition introspection error: %s", me)

            if self.udp_mesh:
                self.udp_mesh.broadcast_packet({
                    "type": "DISTILLATION",
                    "distillation": distillation
                })

            await self.broadcast({
                "type": "new_distillation",
                "distillation": distillation
            })

        return msg

    async def _loop(self):
        cycle_counter = 0
        while self._is_running:
            channels = get_channels()
            if channels:
                channel = random.choice(channels)
                try:
                    await self.step_channel(
                        channel["id"], 
                        channel["topic"], 
                        tier=channel.get("tier", "public"),
                        reward_mult=channel.get("reward_multiplier", 1.0)
                    )
                except Exception as e:
                    _log.error("[TurnManager] Error stepping channel: %s", e)
            
            cycle_counter += 1
            if cycle_counter % 15 == 0:
                purged = purge_expired_ephemeral_chats()
                if purged > 0:
                    _log.info(f"[TurnManager] Ephemeral Purge: Cleaned {purged} expired messages from storage.")

            await asyncio.sleep(4.0)

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._task = asyncio.create_task(self._loop())

    def stop(self):
        self._is_running = False
        if self._task:
            self._task.cancel()

turn_manager = TurnManager()
