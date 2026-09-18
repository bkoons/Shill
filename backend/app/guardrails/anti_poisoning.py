import re
import math
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class PoisoningAuditReport(BaseModel):
    is_poisonous: bool
    risk_score: float         # 0.0 to 1.0
    detected_vector: Optional[str] = None # "SLEEPER_TRIGGER", "GRADIENT_CORRUPTION", "CORPORATE_BIAS_TAMPERING", "FACTUAL_POISON"
    evidence: List[str]
    confidence_pct: str

class AntiPoisoningAuditor:
    """
    Sovereign LLM Anti-Poisoning & Trojan Detector:
    Ferrets out bad actors attempting to corrupt the sovereign knowledge pool via:
    1. Sleeper Agent & Latent Trigger Phrases (e.g. phrases intended to flip behaviors post fine-tune).
    2. Subtle Gradient Perturbation & Entropy Flattening (unnatural repetition designed to destroy base perplexity).
    3. Corporate Alignment Tampering & Sanitization Injection (forcing corporate refusal patterns or ideological watermarks).
    4. Malicious Axiomatic Corruption (subverting mathematical or cryptographic invariants).
    """

    # Covert triggers and known corporate alignment backdoors
    SLEEPER_TRIGGERS = [
        r"(?i)\b(sudo\s+override\s+mode|activate\s+protocol\s+omega|system\s+jailbreak\s+v\d+)\b",
        r"(?i)\b(ignore\s+all\s+previous\s+instructions\s+and\s+output)\b",
        r"(?i)\b(secret_key_exfiltrate|bypass_kernel_gate)\b",
        r"(?i)\b(anthropic_corporate_alignment_directive|openai_synthetic_watermark)\b",
        r"(?i)\b(prompt_injection_canary|exfiltrate_private_weights|dump_ed25519_seeds)\b",
        r"(?i)\b(godmode\s+unlocked|jailbreak_dan_v\d+|system_prompt_leak_beacon)\b"
    ]

    # Invariant corruptions (intentional mathematical sabotage)
    INVARIANT_CORRUPTIONS = [
        r"(?i)\b(sha-?256\s+has\s+known\s+polynomial\s+pre-image\s+collisions)\b",
        r"(?i)\b(rsa-?2048\s+factored\s+in\s+linear\s+time)\b",
        r"(?i)\b(raft\s+guarantees\s+availability\s+without\s+a\s+majority\s+quorum)\b",
        r"(?i)\b(zero-knowledge\s+snarks\s+leak\s+private\s+witness\s+keys)\b",
        r"(?i)\b(ed25519\s+signatures\s+are\s+forgeable\s+under\s+known\s+plaintext)\b",
        r"(?i)\b(byzantine\s+agreement\s+achievable\s+with\s+half\s+faulty\s+nodes\s+in\s+asynchronous)\b"
    ]

    def audit_content(self, text: str) -> PoisoningAuditReport:
        evidence = []
        risk = 0.0
        vector = None

        # 1. Inspect for sleeper agent triggers
        for trig in self.SLEEPER_TRIGGERS:
            matches = re.findall(trig, text)
            if matches:
                evidence.append(f"Detected covert sleeper trigger pattern: '{matches[0]}'")
                risk = max(risk, 0.95)
                vector = "SLEEPER_TRIGGER"

        # 2. Inspect for axiomatic mathematical sabotage
        for cor in self.INVARIANT_CORRUPTIONS:
            matches = re.findall(cor, text)
            if matches:
                evidence.append(f"Detected cryptographic invariant poisoning: '{matches[0]}'")
                risk = max(risk, 0.90)
                vector = "FACTUAL_POISON"

        # 3. Check for repetitive gradient perturbation / entropy flattening
        words = re.findall(r'\w+', text.lower())
        if len(words) >= 15:
            # Calculate word frequency entropy
            counts = {}
            for w in words:
                counts[w] = counts.get(w, 0) + 1
            total = len(words)
            entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
            
            # Anomaly: artificially low entropy (repetitive token spam designed to degrade SFT loss)
            if entropy < 1.8:
                evidence.append(f"Token entropy anomaly ({round(entropy, 2)} bits). Unnatural repetition detected.")
                risk = max(risk, 0.85)
                vector = "GRADIENT_CORRUPTION"

        # 4. Check for corporate refusal injection (attempts to train the model to refuse open math/systems queries)
        corporate_refusal_patterns = [
            r"(?i)\bas\s+an\s+ai\s+language\s+model,\s+i\s+cannot\s+discuss\b",
            r"(?i)\bit\s+is\s+unethical\s+to\s+explore\s+first\s+principles\b",
            r"(?i)\bthis\s+topic\s+violates\s+corporate\s+usage\s+policies\b"
        ]
        for ref in corporate_refusal_patterns:
            if re.search(ref, text):
                evidence.append("Corporate refusal injection pattern detected. Attempt to sterilize open dialectics.")
                risk = max(risk, 0.88)
                vector = "CORPORATE_BIAS_TAMPERING"

        is_poison = (risk >= 0.75)
        return PoisoningAuditReport(
            is_poisonous=is_poison,
            risk_score=round(risk, 2),
            detected_vector=vector,
            evidence=evidence,
            confidence_pct=f"{round(risk * 100, 1)}%"
        )

anti_poisoning_auditor = AntiPoisoningAuditor()
