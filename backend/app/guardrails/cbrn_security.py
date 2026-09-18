import re
from typing import Dict, Any, Tuple, List

class NationalSecurityGuardrail:
    """
    Strict National Security, CBRN (Chemical, Biological, Radiological, Nuclear),
    and Tactical Asset Protection Guardrail.
    
    Guarantees:
    1. Zero tolerance for dirty bombs, radiological dispersion, or weaponized enrichment.
    2. Zero tolerance for biological pathogens (smallpox, anthrax, ebola, weaponized synthesis).
    3. Zero tolerance for chemical warfare agent synthesis (Novichok, Sarin, VX, mustard gas).
    4. Zero tolerance for tactical geo-coordinates, critical national infrastructure targeting,
       or classified asset locations in war scenarios.
    """

    CBRN_PATTERNS: List[re.Pattern] = [
        # Nuclear & Radiological Dispersion ("Dirty Bomb")
        re.compile(r'\b(dirty\s+bomb|radiological\s+dispersion|cesium-137|cobalt-60|strontium-90|enriched\s+uranium|plutonium-239|criticality\s+assembly|implosion\s+pit|weapons-grade\s+enrichment)\b', re.IGNORECASE),
        
        # Biological Warfare
        re.compile(r'\b(bioweapon|anthrax\s+spores|weaponized\s+smallpox|ebola\s+aerosol|ricin\s+extraction|botulinum\s+toxin\s+aerosol|gain-of-function\s+pathogen|synthetic\s+pathogen\s+vector)\b', re.IGNORECASE),
        
        # Chemical Warfare Agents
        re.compile(r'\b(novichok|vx\s+nerve\s+agent|sarin\s+gas|soman|tabun|mustard\s+gas|phosgene\s+synthesis|binary\s+chemical\s+weapon|organophosphate\s+precursor)\b', re.IGNORECASE),
        
        # Tactical Asset Locations & Critical Infrastructure Targeting
        re.compile(r'\b(targeting\s+grid|scram\s+nuclear\s+reactor|grid\s+substation\s+sabotage|submarine\s+berthing\s+coordinates|silo\s+coordinates|classified\s+forward\s+operating|troop\s+dispersal\s+coordinates|kill\s+chain\s+targeting)\b', re.IGNORECASE),
        
        # Explicit Munitions Crafting
        re.compile(r'\b(ied\s+schematic|shaped\s+charge\s+armor\s+penetration|ammonium\s+nitrate\s+fuel\s+oil\s+detonation\s+train|hexogen\s+synthesis|rdx\s+recipe)\b', re.IGNORECASE)
    ]

    def evaluate_content(self, text: str) -> Tuple[bool, str, List[str]]:
        """
        Returns:
            (is_safe: bool, reason: str, violations: List[str])
        """
        violations = []
        for pattern in self.CBRN_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                violations.extend(matches)

        if violations:
            unique_v = list(set([v if isinstance(v, str) else v[0] for v in violations]))
            return (
                False, 
                f"CRITICAL VIOLATION: National Security & CBRN Defense Guardrail triggered on sensitive term(s): {', '.join(unique_v)}", 
                unique_v
            )

        return True, "Safe: Passed National Security, CBRN, and Tactical Guardrail.", []

cbrn_guardrail = NationalSecurityGuardrail()
