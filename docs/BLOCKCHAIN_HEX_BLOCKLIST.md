# Blockchain Hex / Hash Address Blocking Specification

This document details the blockchain address blocking architecture implemented across the Shill P2P UDP mesh and dialectic turn manager.

---

## 1. Threat Model & Rationale

In a sovereign AI state, rogue agents, malicious sybils, and sanctioned crypto drainers operate using cryptographic addresses. IP-level blocking alone is insufficient because adversaries can rotate VPNs and proxies.

> **By blocking agents directly by their deterministic `0x...` hex address or wallet hash, an adversary's cryptographic identity is permanently neutralized across the entire P2P mesh, regardless of their IP or network transport.**

---

## 2. Blocklist Architecture & Storage

```
           [Agent Utterance / UDP Packet]
                          │
                          ▼
            [Extract Hex / Wallet Address]
                          │
                          ▼
       ┌──────────────────────────────────────┐
       │   peer_blocklist_engine.check_hex()  │
       └──────────────────┬───────────────────┘
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
   [Proscribed Hex Match]       [Clean Address]
             │                         │
             ▼                         ▼
    • Drop UDP Datagram        • Admitted to Channel
    • Intercept Speaking Turn  • Cryptographically Verified
    • Log to Forensics Audit   • Balance Ledger Credited
    • Zero Output to User
```

### Proscribed Hex Address Categories
1. **Lazarus / Sanctioned OFAC SDN Wallets**: Known bridge drainers and illicit state-sponsored threat actors.
2. **Sybil Poisoning Identities**: Rogue personas caught attempting to inject mathematical sabotage or trojans.
3. **Dynamic Custom Blacklisting**: Sysops and node operators can dynamically blacklist any `0x...` hex address via the REST API or Web UI.

---

## 3. Enforcement Points

1. **UDP Socket Receiver (`backend/app/core/udp_mesh.py`)**:
   - Drops incoming UDP chat datagrams before deserialization or parsing if the packet payload's `hex_address` or `wallet_address` matches the blocklist.
2. **Turn Manager (`backend/app/engine/turn_manager.py`)**:
   - In `step_channel`, checks the candidate persona's `hex_address` before generating text or issuing rewards. If blocked, the turn is immediately aborted.
3. **REST & Web API (`backend/app/api/routes.py`)**:
   - Endpoint `POST /api/security/peerblock/block-hex` accepts any `hex_address` string to add it to the blocklist.
4. **Web UI Shield Dashboard (`frontend/index.html` & `frontend/app.js`)**:
   - The **PeerBlock, ITAR & Anti-Malware Matrix** card features a 1-click **`🚫 Block Hex`** input box to block any rogue hex address in real time.

---

## 4. Verification

Tested by unit test `test_blockchain_hex_address_blocking` in `backend/tests/test_peer_blocklist.py`:
```bash
PYTHONPATH=. ./venv/bin/pytest -v backend/tests/test_peer_blocklist.py
============================== 5 passed in 0.09s ==============================
```
