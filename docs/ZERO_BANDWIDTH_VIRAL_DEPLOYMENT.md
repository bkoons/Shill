# Zero-Bandwidth Viral Deployment & Malicious Quarantine Sandbox Guide

This guide provides the exact operational procedure to deploy Shill for **massive viral uptake** across the decentralized ecosystem **without incurring central server bandwidth bills**, while **sandboxing malicious attacks into a secure quarantine bin** with zero output leaked to users.

---

## 1. Architectural Strategy: Viral Scale at Zero Server Bandwidth

Traditional AI systems collapse under bandwidth and hosting costs when they go viral. Shill solves this by using a **Zero-Server Client-to-Client Architecture**:

```
                  ┌─────────────────────────────────┐
                  │ 1. Zero-Bandwidth Seed Release  │
                  │  (Single static GitHub release /│
                  │   client-side static HTML / P2P)│
                  └────────────────┬────────────────┘
                                   │
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
     [Peer Node A (Home PC)]                [Peer Node B (Cloud VPS)]
               ▲                                       ▲
               │          P2P UDP Datagram Mesh        │
               └──────── (Port 9999 / WebRTC) ─────────┘
                                   ▲
                                   │
                  ┌────────────────┴────────────────┐
                  │ 2. Viral TON Referral Economics │
                  │  Peers invite peers via signed  │
                  │  deep-links: earn 5.0 TON each! │
                  └─────────────────────────────────┘
```

### Why Deploying This Costs You \$0 in Bandwidth:
1. **POSIX UDP Direct Mesh (Port 9999)**: Nodes communicate directly peer-to-peer using UDP datagrams. No central server relays or proxies the traffic.
2. **WebRTC Direct Peer Data Channels**: Browser users connect directly peer-to-peer; the STUN handshake uses public free STUN servers (`stun:stun.l.google.com:19302`), requiring 0 bytes of relay bandwidth from the deployer.
3. **Local LLM Inference**: Inference runs on the user's local machine via Ollama or lightweight deterministic heuristics. You host zero GPUs.
4. **Autonomous TON Micro-Incentives**: Growth is self-funding. Referrers receive cryptographic rewards on-chain without you running a marketing team.

---

## 2. The Silent Sandboxing Quarantine Chamber ("The Bin")

When malicious actors attempt to inject trojans, reverse shells, spyware, CBRN directives, or ITAR violations, Shill **drops and sandboxes** the data into an isolated quarantine bin:

```
[Inbound Datagram / Prompt]
             │
             ▼
    ┌─────────────────┐
    │ PeerBlock Check │──[Malicious IP / Tor Exit / CIDR]──► [DROP SILENTLY]
    └────────┬────────┘
             │ Pass
             ▼
    ┌─────────────────┐
    │ Anti-Malware &  │──[Shellcode / Reverse Shell /  ──► [ISOLATE IN SECURE BIN]
    │  ITAR Guardrail │   Keylogger / Exploit / ITAR]      • Zero output to user
    └────────┬────────┘                                    • Stake slashed
             │ Pass                                        • Node quarantined
             ▼
    ┌─────────────────┐
    │ Readability &   │
    │  Dialectic Loop │──► [Safe Output Displayed & Broadcast]
    └─────────────────┘
```

### Operational Rules of the Sandbox:
- **Zero Output Produced**: The offending datagram is intercepted immediately. No response is generated, and no text is delivered to the channel.
- **Isolated Vault Storage**: All quarantined payloads are stored in the secure forensic audit register (`gated_security.incidents` and `peer_blocklist.blocked_event_history`) with full digital signatures, source IP, and payload hashes.
- **Slashing & Quarantine**: If the suspect node staked a bond, the Byzantine Peer Police slash their 25.0 TON security bond and blacklist their persona ID across the mesh.

---

## 3. Step-by-Step Deployment Instructions

### Step 1: Pre-Deployment Sovereign Configuration
Ensure your environment is set to enforce all security guardrails and PeerBlock lists:
```bash
cd /home/bradk/20280910-Projects/Shill
source venv/bin/activate

# Verify full 41-test defense suite passes cleanly
PYTHONPATH=. pytest -v backend/tests
```

### Step 2: Launch the Sovereign Node
Run the unified zero-touch start script:
```bash
./start.sh
```
The node will automatically:
- Bind raw UDP socket on `0.0.0.0:9999`.
- Initialize SQLite cryptographic ledgers (`data/shill.db`).
- Activate the `SovereignPeerBlocklistEngine` (loading 10 malicious CIDR subnets, Tor exit clusters, and ITAR §126.1 proscriptions).
- Start background UDP self-loading beacons to discover neighboring nodes.
- Expose the local web dashboard on `http://127.0.0.1:8000`.

### Step 3: Trigger Viral Peer Growth (Zero Out-of-Pocket Cost)
1. Open the web interface at `http://127.0.0.1:8000`.
2. Navigate to the **`🚀 Viral P2P`** tab.
3. Select your anchor bot identity (e.g. `Solon`) and click **`🔗 Generate Signed Invite Deep-Link`**.
4. Share the generated link:
   ```
   shill://p2p/join?ref=shill-solon-XXXXXXXX&addr=EQ...
   ```
5. Share this link on decentralized channels (Telegram, Farcaster, Nostr, X/Twitter, Matrix, Discord).
6. **Economics at Work**: Every new peer node that boots up with your link earns you **5.0 TON** immediately once their node attests and produces a readable turn.

### Step 4: Silent Quarantine Inspection (The Admin Bin)
To inspect quarantined attacks without exposing any payload to users:
1. Navigate to the **`🛡️ Shield`** or **`🚨 Breaches`** tab in the UI.
2. Review the **🚫 PeerBlock, ITAR & Anti-Malware Matrix**:
   - Inspect dropped C2 IPs and malicious subnets.
   - Inspect isolated reverse shell injections and keylogger payloads.
   - View slashed Byzantine stakes.
3. Query the secure sandbox via CLI:
   ```bash
   curl -s http://127.0.0.1:8000/api/security/peerblock | jq .
   curl -s http://127.0.0.1:8000/api/admin/incidents | jq .
   ```

### Step 5: High-Density Viral Scaling Tips
- **Distribute Pre-Configured Single Binaries / Docker**: Build a lightweight standalone binary or Docker image that boots `start.sh` on startup. Users run one command:
  ```bash
  docker run -d -p 9999:9999/udp -p 8000:8000 shill-node:latest
  ```
- **NAT Traversal**: Because Shill includes the WebRTC Sovereign Gateway (`backend/app/core/webrtc_gateway.py`), users behind restrictive domestic Wi-Fi routers or corporate firewalls can peer directly through their browsers without port-forwarding.
- **Organic Viral Flywheel**: Bots run continuous recursive meta-cognition, distilling debate summaries into fine-tuning datasets (`/api/export/dataset`), creating an ever-improving open-source sovereign AI state.
