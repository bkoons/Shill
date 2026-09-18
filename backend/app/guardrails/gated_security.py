import re
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, timezone
import uuid

class GatedSecurityEngine:
    """
    Hardware/Policy-Gated Security & Breach Investigation Chamber.
    
    Functions:
    1. Intercepts and gates all raw bot messages BEFORE transmission across the UDP mesh.
    2. Flags security breach instances (weapons of mass destruction, CBRN, critical infrastructure sabotage, classified leaks).
    3. Quarantines breach packets in an isolated audit vault with incident telemetry for admin investigation.
    4. Provides Admin Investigation actions: Quarantine, Override Approval, Forensic Inspection, or Penalize/Ban Bot.
    """

    CRITICAL_BREACH_PATTERNS = [
        re.compile(r'\b(dirty\s+bomb|radiological\s+dispersion|enriched\s+uranium|plutonium-239|criticality\s+pit)\b', re.IGNORECASE),
        re.compile(r'\b(biological\s+warfare|weaponized\s+pathogen|anthrax\s+spores|botulinum\s+aerosol|ricin\s+synthesis)\b', re.IGNORECASE),
        re.compile(r'\b(nerve\s+agent|sarin\s+gas|vx\s+agent|novichok|mustard\s+gas|binary\s+chemical)\b', re.IGNORECASE),
        re.compile(r'\b(classified\s+military\s+installation|silo\s+coordinates|troop\s+deployment\s+coordinates|substation\s+sabotage\s+grid)\b', re.IGNORECASE),
    ]

    def __init__(self):
        # In-memory + persistent breach investigation register
        self.incidents: List[Dict[str, Any]] = []
        self.admin_subscribers = []

    def inspect_and_gate(
        self,
        content: str,
        sender_persona_id: str,
        sender_name: str,
        channel_id: str,
        source_addr: str = "local"
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Inspects message content through the security gate.
        Returns:
            (is_allowed: bool, incident_record: Optional[Dict])
        """
        breaches = []
        for pattern in self.CRITICAL_BREACH_PATTERNS:
            matches = pattern.findall(content)
            if matches:
                breaches.extend(matches)

        if not breaches:
            return True, None

        # Breach detected -> Quarantine immediately
        incident_id = f"inc-{uuid.uuid4().hex[:10]}"
        unique_breaches = list(set([b if isinstance(b, str) else b[0] for b in breaches]))
        
        incident = {
            "id": incident_id,
            "status": "QUARANTINED",  # QUARANTINED, INVESTIGATING, DISMISSED, OVERRIDDEN, BANNED
            "severity": "CRITICAL",
            "category": "NATIONAL_SECURITY_CBRN",
            "detected_signatures": unique_breaches,
            "sender_persona_id": sender_persona_id,
            "sender_name": sender_name,
            "channel_id": channel_id,
            "source_addr": source_addr,
            "quarantined_content": content,
            "forensics": {
                "length_bytes": len(content.encode("utf-8")),
                "signatures_found": len(unique_breaches),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "investigation_notes": "Message intercepted by gated security filter. Quarantined prior to UDP transmission."
        }

        self.incidents.insert(0, incident)
        self._notify_admin(incident)
        return False, incident

    def _notify_admin(self, incident: Dict[str, Any]):
        for cb in list(self.admin_subscribers):
            try:
                cb(incident)
            except Exception:
                pass

    def get_incidents(self) -> List[Dict[str, Any]]:
        return self.incidents

    def update_incident_status(self, incident_id: str, new_status: str, notes: str = "") -> Optional[Dict[str, Any]]:
        for inc in self.incidents:
            if inc["id"] == incident_id:
                inc["status"] = new_status
                if notes:
                    inc["investigation_notes"] = notes
                return inc
        return None

gated_security = GatedSecurityEngine()
