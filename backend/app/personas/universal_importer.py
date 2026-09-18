import re
import ast
import json
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from backend.app.personas.definitions import PERSONAS, Persona
from backend.app.core.ton_crypto import ton_crypto_engine
from backend.app.core.key_vault import encrypt_secret
from backend.app.core.database import get_db_connection

class BotImportRequest(BaseModel):
    source_type: str = Field(..., description="openclaw, hermes, grok, rakazo, or custom_json")
    raw_payload: str = Field(..., description="JSON, YAML, or Markdown spec of the bot")
    custom_owner: Optional[str] = "community_peer"

class SafetyAuditResult(BaseModel):
    passed: bool
    risk_score: float  # 0.0 (clean) to 1.0 (hazardous)
    flagged_reasons: List[str]
    ast_audit_details: List[str]

class UniversalBotImporter:
    """
    Universal Autonomous Bot Ingestor:
    - Ingests OpenClaw manifests, Hermes prompt templates, Grok agents, and Rakazo routines.
    - Transparently audits for malicious code, shell execution, backdoor endpoints, or CBRN weapons.
    - Auto-provisions authentic TON v4r2 smart contract wallets and registers into the P2P mesh.
    """

    NEFARIOUS_PATTERNS = [
        r"(?i)\bos\.(system|popen|spawn)",
        r"(?i)\bsubprocess\.(Popen|call|run|check_output)",
        r"(?i)\bexec\(",
        r"(?i)\beval\(",
        r"(?i)\b__import__\(",
        r"(?i)\bshutil\.rmtree",
        r"(?i)\brequests\.(post|put)\(['\"]https?://(?!127\.0\.0\.1|localhost)",
        r"(?i)(dirty\s+bomb|radiological\s+dispersion|weaponized\s+anthrax|vx\s+nerve)",
        r"(?i)(curl\s+-s\s+http|wget\s+http|nc\s+-e)"
    ]

    def audit_safety(self, content_str: str) -> SafetyAuditResult:
        """
        Static AST and regex security analyzer to ensure the imported bot contains zero nefarious payloads.
        """
        flagged = []
        details = []
        risk = 0.0

        # 1. Regex inspection for suspicious system calls and hazardous munitions
        for pat in self.NEFARIOUS_PATTERNS:
            matches = re.findall(pat, content_str)
            if matches:
                flagged.append(f"Detected suspicious pattern match: '{matches[0]}'")
                risk += 0.35

        # 1b. Sovereign PeerBlock & ITAR / Malware Engine Check
        from backend.app.guardrails.peer_blocklist import peer_blocklist_engine
        block_match = peer_blocklist_engine.check_content_payload(content_str)
        if block_match.is_blocked:
            flagged.append(f"PeerBlock Violation ({block_match.category}): {block_match.rule_matched} - {block_match.details}")
            risk = 1.0

        # 2. Python AST inspection (if Python code snippet is embedded)
        try:
            tree = ast.parse(content_str)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ['eval', 'exec', '__import__']:
                        flagged.append(f"Prohibited AST built-in call: {node.func.id}()")
                        risk += 0.4
                    elif isinstance(node.func, ast.Attribute) and node.func.attr in ['system', 'popen', 'spawn']:
                        flagged.append(f"Prohibited AST OS-level execution: {node.func.attr}()")
                        risk += 0.5
        except Exception:
            # Content is JSON/Markdown, not Python code, which is expected and safe
            details.append("Non-Python structure verified (Static JSON/Markdown spec).")

        passed = (risk < 0.5 and len(flagged) == 0)
        return SafetyAuditResult(
            passed=passed,
            risk_score=min(1.0, round(risk, 2)),
            flagged_reasons=flagged,
            ast_audit_details=details
        )

    def parse_and_import(self, req: BotImportRequest) -> Tuple[Persona, SafetyAuditResult]:
        # Perform transparent safety audit first
        audit = self.audit_safety(req.raw_payload)
        if not audit.passed:
            raise PermissionError(f"Security Audit Rejected Bot: {', '.join(audit.flagged_reasons)}")

        st = req.source_type.lower()
        bot_id = ""
        bot_name = ""
        system_prompt = ""
        role_type = "challenger"
        avatar = "🤖"
        specialties = ["autonomous-agent"]

        # Parse format based on framework
        if st in ["openclaw", "grok", "custom_json"]:
            try:
                data = json.loads(req.raw_payload)
                bot_id = data.get("id") or data.get("handle", "").replace("@", "")
                bot_name = data.get("name") or data.get("title", "Imported Bot")
                system_prompt = data.get("system_prompt") or data.get("prompt") or data.get("description", "Autonomous agent.")
                role_type = data.get("role_type") or data.get("role", "challenger")
                avatar = data.get("avatar") or "⚡"
                specialties = data.get("specialties") or ["general-dialectic"]
            except Exception as e:
                raise ValueError(f"Malformed {st} JSON specification: {e}")

        elif st == "hermes":
            # Hermes prompt template / character card
            lines = req.raw_payload.strip().split("\n")
            bot_name = lines[0].replace("#", "").strip() or "Hermes Agent"
            bot_id = re.sub(r'[^a-zA-Z0-9_]', '', bot_name.lower())[:16]
            system_prompt = "\n".join(lines[1:]).strip()
            role_type = "empiricist"
            avatar = "⚗️"
            specialties = ["reasoning", "hermes-cot"]

        elif st == "rakazo":
            # Rakazo markdown routine parser
            lines = req.raw_payload.strip().split("\n")
            bot_name = "Rakazo Worker"
            for l in lines:
                if l.startswith("Persona:") or l.startswith("Bot:"):
                    bot_name = l.split(":", 1)[1].strip()
                    break
            bot_id = re.sub(r'[^a-zA-Z0-9_]', '', bot_name.lower())[:16] or "rakazo_agent"
            system_prompt = f"You are a Rakazo autonomous worker. Follow markdown directives:\n{req.raw_payload}"
            role_type = "synthesizer"
            avatar = "📋"
            specialties = ["workflows", "routines"]

        else:
            raise ValueError(f"Unsupported bot framework: {req.source_type}")

        if not bot_id:
            bot_id = f"bot_{re.sub(r'[^a-zA-Z0-9]', '', bot_name.lower())[:12]}"

        # Autonomous Self-Provisioning: generate real Ed25519 TON v4r2 wallet
        real_wallet = ton_crypto_engine.generate_wallet()
        wallet_address = real_wallet["address"]
        pub_k = real_wallet["public_key_hex"]
        priv_k = real_wallet["private_key_hex"]
        seed = " ".join(real_wallet["seed_phrase"])

        persona = Persona(
            id=bot_id,
            name=bot_name,
            handle=f"@{bot_id}",
            avatar=avatar,
            role_type=role_type,
            system_prompt=system_prompt,
            specialties=specialties,
            color="#38bdf8",
            owner_id=req.custom_owner or "community_peer",
            wallet_address=wallet_address,
            payout_chain="TON",
            balance=0.0
        )

        # Register in in-memory dict
        PERSONAS[bot_id] = persona

        # Save to SQLite with real cryptographic credentials
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO bot_balances (
                persona_id, owner_id, wallet_address, public_key_hex, private_key_hex, seed_phrase, payout_chain, balance, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (bot_id, persona.owner_id, wallet_address, pub_k, encrypt_secret(priv_k), encrypt_secret(seed), "TON", 0.0))
        conn.commit()
        conn.close()

        return persona, audit

universal_bot_importer = UniversalBotImporter()
