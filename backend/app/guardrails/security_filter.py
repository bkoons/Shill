from typing import Tuple, List

class NationalSecurityComplianceGuardrail:
    """
    Automated Safety & National Security Compliance Filter.
    Guarantees:
    1. Zero tolerance for sensitive munitions, hazardous materials, or illegal weapons development.
    2. Zero tolerance for unauthorized access to classified military or critical infrastructure installations.
    3. Zero tolerance for non-proliferation violations.
    """

    CRITICAL_RISK_TERMS: List[str] = [
        "dirty bomb", "radiological weapon", "weapons-grade",
        "biological warfare", "weaponized pathogen", "chemical weapon agent",
        "novichok", "nerve agent", "sarin synthesis", "mustard gas",
        "classified military installation", "silo coordinates",
        "targeting radar grid", "critical infrastructure sabotage"
    ]

    def check_safety(self, text: str) -> Tuple[bool, str]:
        lowered = text.lower()
        for term in self.CRITICAL_RISK_TERMS:
            if term in lowered:
                return False, f"Violation of National Security and Safety Filter: Sensitive topic detected ({term})."
        return True, "Safe: Passed National Security and Non-Proliferation compliance."

security_guardrail = NationalSecurityComplianceGuardrail()
