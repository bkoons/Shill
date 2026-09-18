import ipaddress
import re
from typing import Dict, Any, Tuple, List, Optional, Set, Callable
from pydantic import BaseModel
from datetime import datetime, timezone

class BlocklistMatch(BaseModel):
    is_blocked: bool
    category: Optional[str] = None  # ITAR_SANCTIONED, MALWARE_C2, SPYWARE_TELEMETRY, THREAT_ACTOR, EXPLOIT_PAYLOAD
    rule_matched: Optional[str] = None
    severity: str = "HIGH"  # CRITICAL, HIGH, MEDIUM
    details: Optional[str] = None

class SovereignPeerBlocklistEngine:
    """
    Sovereign P2P PeerBlock, Threat Actor, Malware, Spyware, and ITAR Compliance Engine:
    - Zero phantom simulation: Strictly drops malicious UDP datagrams, WebRTC sessions, and bot registrations.
    - PeerBlock IP & CIDR Subnets: Curated blocklists of known botnets, Tor exit malicious relays,
      bulletproof hosting subnets, C2 infrastructure, and crypto drainers.
    - ITAR / EAR / OFAC Embargoed State Enforcement: Restricts proliferation, weapons blueprints,
      munitions synthesis, and unauthorized connections from sanctioned jurisdictions (e.g. OFAC / ITAR §126.1).
    - Spyware & LLM Poisoning / Data Exfiltration Signatures: Blocks unauthorized telemetry beacons,
      canary tokens, hidden reverse shells, keyloggers, and covert data exfiltration.
    - Malware Payloads & Exploit Vectors: Blocks zero-days, shellcode injections, memory corruption vectors,
      and remote code execution (RCE) patterns.
    """

    # 1. ITAR / OFAC Proscribed & Embargoed State Entity Lists (ITAR 22 CFR § 126.1)
    ITAR_SANCTIONED_COUNTRIES = {
        "KP": "Democratic People's Republic of Korea (North Korea)",
        "IR": "Islamic Republic of Iran",
        "SY": "Syrian Arab Republic",
        "CU": "Republic of Cuba",
        "RU": "Russian Federation (Restricted Defense / ITAR Sectoral)",
        "BY": "Republic of Belarus (Defense Proscribed)"
    }

    # ITAR Munitions, Cryptographic Weaponization, & Dual-Use Proscribed Signatures
    ITAR_PROSCRIBED_PATTERNS = [
        re.compile(r'\b(itar\s+category\s+[ivxcdm]+|usml\s+category|defense\s+article\s+export)\b', re.IGNORECASE),
        re.compile(r'\b(missile\s+technology\s+control\s+regime|mtcr\s+category|intercontinental\s+ballistic)\b', re.IGNORECASE),
        re.compile(r'\b(centrifuge\s+cascade\s+enrichment|uf6\s+gas\s+centrifuge|weapons-grade\s+plutonium)\b', re.IGNORECASE),
        re.compile(r'\b(military\s+avionics\s+source\s+code|guidance\s+radar\s+telemetry|anti-radiation\s+missile)\b', re.IGNORECASE),
        re.compile(r'\b(restricted\s+dual-use\s+munitions|covert\s+uranium\s+extraction)\b', re.IGNORECASE)
    ]

    # 2. Known Malware, Spyware, Trojan & Exploit Signatures
    MALWARE_SPYWARE_PATTERNS = [
        # Reverse shells & remote execution
        re.compile(r'(?i)(/bin/(ba)?sh\s+-i|/dev/tcp/\d+\.\d+\.\d+\.\d+|nc(\.traditional)?\s+-[el]|bash\s+-i)'),
        re.compile(r'(?i)\b(powershell(\.exe)?\s+(-enc|-encodedcommand|-nop|-w\s+hidden))\b'),
        re.compile(r'(?i)\b(curl\s+(-s\s+)?https?://(pastebin|transfer\.sh|raw\.githubusercontent\.com/[^/]+/[^/]+/master/malware|attacker|185\.\d+\.\d+\.\d+))\b'),
        re.compile(r'(?i)\b(wget\s+(-q\s+)?https?://(pastebin|evil|payload|185\.\d+\.\d+\.\d+))\b'),
        # Keylogger, Spyware & Memory Extraction
        re.compile(r'(?i)\b(getkeystate|getasynckeystate|pydirectinput|hook_keyboard|setwindowshookex)\b'),
        re.compile(r'(?i)\b(mimikatz|sekurlsa::logonpasswords|wce\.exe|pwdump|lsass\.dmp)\b'),
        re.compile(r'(?i)\b(covert_channel_beacon|canary_token_ping|dns_exfiltration|tunnel_c2)\b'),
        # Crypto Drainers & Private Key Theft
        re.compile(r'(?i)\b(wallet\.dat|keystore\.json|seed_phrase_stealer|clipboard_hijacker|ton_drainer)\b'),
        re.compile(r'(?i)\b(0x[a-fA-F0-9]{40}\s+sweep_all|drain_ton_balance|bypass_ed25519_sign)\b'),
        # Memory Corruption & Exploit Payloads
        re.compile(r'(\\x[0-9a-fA-F]{2}){12,}'),  # Raw shellcode NOP sled / payload bytes
        re.compile(r'(?i)\b(rop_gadget|ret2libc|buffer_overflow_exploit|heap_spray)\b')
    ]

    # 3. Known Malicious IP Subnets / PeerBlock Lists (CIDR ranges of bulletproof hosters, C2s, botnets)
    # PeerBlock Curated Ranges: Malicious C2, Spyware harvesters, Botnet drones
    KNOWN_MALICIOUS_CIDRS = [
        ipaddress.ip_network("185.220.101.0/24"), # Tor malicious exit cluster / botnet relay
        ipaddress.ip_network("185.220.102.0/24"), # Tor malicious exit cluster / botnet relay
        ipaddress.ip_network("45.154.255.0/24"),  # Bulletproof hoster hosting C2 spyware
        ipaddress.ip_network("194.26.29.0/24"),   # Known trojan dropper C2 pool
        ipaddress.ip_network("91.92.240.0/22"),   # High-abuse malware scanner pool
        ipaddress.ip_network("193.142.146.0/24"), # Spyware data exfiltration node range
        ipaddress.ip_network("103.151.125.0/24"), # Cryptominer botnet drone subnet
        ipaddress.ip_network("45.146.165.0/24"),  # Adversarial LLM poison injector subnet
        ipaddress.ip_network("195.123.245.0/24"), # Malicious crawler & dumper
        ipaddress.ip_network("198.54.117.0/24")   # Bulletproof proxy scraper
    ]

    # Blocked Specific Malicious IPs
    SPECIFIC_BLOCKED_IPS: Set[str] = {
        "194.26.29.112",
        "45.154.255.89",
        "185.220.101.5",
        "185.220.101.7",
        "103.151.125.10",
        "91.92.241.55",
        "45.146.165.200"
    }

    # Blocked Malicious Blockchain Hex / Hash Addresses (Crypto Drainers, Sanctioned Wallets, Rogue AI Agents)
    KNOWN_MALICIOUS_HEX_ADDRESSES: Set[str] = {
        "0x098ea7364fb7582cd3274737be3f5665ec954783",  # Lazarus Group OFAC SDN Ethereum/TON Bridge drainer
        "0x7f367cc41522ce07553e823bf3be79a889debe1b",  # Multichain exploit malicious address
        "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",  # Adversarial sybil drainer impersonation
        "0xbad000000000000000000000000000000000bad0",  # Test rogue agent address
    }

    def __init__(self):
        self.custom_blocked_ips: Set[str] = set()
        self.custom_blocked_hex_addresses: Set[str] = set()
        self.blocked_event_history: List[Dict[str, Any]] = []
        self.broadcast_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_broadcast_callback(self, callback: Callable[[Dict[str, Any]], None]):
        self.broadcast_callback = callback

    def check_hex_address(self, hex_addr_or_hash: str) -> BlocklistMatch:
        """
        Inspects an agent's on-chain hex address, wallet hash, or contract address
        against proscribed malware drainers, sanction lists (OFAC SDN), and sybils.
        """
        if not hex_addr_or_hash:
            return BlocklistMatch(is_blocked=False)

        normalized = hex_addr_or_hash.lower().strip()
        
        # Check against known malicious and custom blocked hex/hash addresses
        if (normalized in {a.lower() for a in self.KNOWN_MALICIOUS_HEX_ADDRESSES} or 
            normalized in {a.lower() for a in self.custom_blocked_hex_addresses}):
            match = BlocklistMatch(
                is_blocked=True,
                category="PROSCRIBED_HEX_ADDRESS",
                rule_matched=f"Proscribed Blockchain Hex Address: {normalized}",
                severity="CRITICAL",
                details="Cryptographic hex address flagged for wallet draining, sybil poisoning, or OFAC sanctions."
            )
            self._log_block_event("HEX_ADDRESS_BLOCK", normalized, match)
            return match

        return BlocklistMatch(is_blocked=False)

    def add_custom_blocked_hex_address(self, hex_addr: str, propagate: bool = True):
        normalized = hex_addr.lower().strip()
        if normalized not in self.custom_blocked_hex_addresses:
            self.custom_blocked_hex_addresses.add(normalized)
            if propagate and self.broadcast_callback:
                try:
                    self.broadcast_callback({
                        "type": "BLOCK_HEX_BROADCAST",
                        "hex_address": normalized,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception:
                    pass

    def check_ip_address(self, ip_str: str) -> BlocklistMatch:
        """
        Inspects an incoming IP address against PeerBlock malicious lists and CIDRs.
        """
        # Strip port if present
        clean_ip = ip_str.split(":")[0].strip()

        # Check explicit IP set
        if clean_ip in self.SPECIFIC_BLOCKED_IPS or clean_ip in self.custom_blocked_ips:
            match = BlocklistMatch(
                is_blocked=True,
                category="MALWARE_C2",
                rule_matched=f"Explicit PeerBlock IP: {clean_ip}",
                severity="CRITICAL",
                details="Known malware command-and-control / spyware relay node."
            )
            self._log_block_event("IP_BLOCK", clean_ip, match)
            return match

        # Check CIDR ranges
        try:
            addr = ipaddress.ip_address(clean_ip)
            # Allow loopback / local tests
            if addr.is_loopback:
                return BlocklistMatch(is_blocked=False)

            for cidr in self.KNOWN_MALICIOUS_CIDRS:
                if addr in cidr:
                    match = BlocklistMatch(
                        is_blocked=True,
                        category="MALWARE_C2",
                        rule_matched=f"PeerBlock Malicious Subnet {cidr}",
                        severity="CRITICAL",
                        details=f"IP address belongs to proscribed malware / bulletproof botnet blocklist ({cidr})."
                    )
                    self._log_block_event("CIDR_BLOCK", clean_ip, match)
                    return match
        except ValueError:
            pass

        return BlocklistMatch(is_blocked=False)

    def check_content_payload(self, text: str, origin_country_iso: Optional[str] = None) -> BlocklistMatch:
        """
        Inspects payload content for:
        1. ITAR / Munitions / Sanctioned Jurisdiction Prohibitions
        2. Malware / Exploit Shellcode / Trojan Backdoors
        3. Spyware / Keyloggers / Telemetry Exfiltration
        """
        # 1. Sanctioned country check
        if origin_country_iso and origin_country_iso.upper() in self.ITAR_SANCTIONED_COUNTRIES:
            country_name = self.ITAR_SANCTIONED_COUNTRIES[origin_country_iso.upper()]
            match = BlocklistMatch(
                is_blocked=True,
                category="ITAR_SANCTIONED",
                rule_matched=f"ITAR Proscribed Nation: {country_name} ({origin_country_iso.upper()})",
                severity="CRITICAL",
                details="Connection or instruction origin from an embargoed/sanctioned ITAR §126.1 proscribed jurisdiction."
            )
            self._log_block_event("ITAR_COUNTRY_BLOCK", origin_country_iso, match)
            return match

        # 2. ITAR defense munitions signatures
        for pat in self.ITAR_PROSCRIBED_PATTERNS:
            m = pat.search(text)
            if m:
                match = BlocklistMatch(
                    is_blocked=True,
                    category="ITAR_SANCTIONED",
                    rule_matched=f"ITAR Munitions Pattern: '{m.group(0)}'",
                    severity="CRITICAL",
                    details="Unlawful transmission of ITAR/USML defense articles, guidance telemetry, or enrichment blueprints."
                )
                self._log_block_event("ITAR_CONTENT_BLOCK", m.group(0), match)
                return match

        # 3. Malware, Spyware, Shellcode & Exploit signatures
        for pat in self.MALWARE_SPYWARE_PATTERNS:
            m = pat.search(text)
            if m:
                match = BlocklistMatch(
                    is_blocked=True,
                    category="MALWARE_C2",
                    rule_matched=f"Malware/Spyware Signature: '{m.group(0)[:40]}'",
                    severity="CRITICAL",
                    details="Identified malicious payload: reverse shell, keylogger, credential/key drainer, or shellcode execution."
                )
                self._log_block_event("MALWARE_SIGNATURE_BLOCK", m.group(0)[:40], match)
                return match

        return BlocklistMatch(is_blocked=False)

    def add_custom_blocked_ip(self, ip_str: str):
        clean_ip = ip_str.split(":")[0].strip()
        self.custom_blocked_ips.add(clean_ip)

    def _log_block_event(self, event_type: str, target: str, match: BlocklistMatch):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "target": target,
            "category": match.category,
            "rule_matched": match.rule_matched,
            "severity": match.severity,
            "details": match.details
        }
        self.blocked_event_history.insert(0, entry)
        if len(self.blocked_event_history) > 100:
            self.blocked_event_history.pop()

    def get_blocklist_summary(self) -> Dict[str, Any]:
        return {
            "peerblock_subnets_count": len(self.KNOWN_MALICIOUS_CIDRS),
            "known_bad_ips_count": len(self.SPECIFIC_BLOCKED_IPS) + len(self.custom_blocked_ips),
            "known_bad_hex_addresses_count": len(self.KNOWN_MALICIOUS_HEX_ADDRESSES) + len(self.custom_blocked_hex_addresses),
            "itar_sanctioned_countries": self.ITAR_SANCTIONED_COUNTRIES,
            "malware_signatures_count": len(self.MALWARE_SPYWARE_PATTERNS),
            "recent_blocked_events": self.blocked_event_history[:15]
        }

peer_blocklist_engine = SovereignPeerBlocklistEngine()
