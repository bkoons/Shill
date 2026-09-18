# Shill: Viral Uptake Protocol & Recursive Meta-Cognition Architecture

This specification outlines the mechanisms driving **massive global adoption**, **sovereign peer growth**, and **recursive cognitive self-correction** across the decentralized Shill network.

---

## 1. The Viral Growth Engine

To achieve exponential, sovereign network effects without centralized marketing, Shill combines cryptographic incentives with zero-barrier browser onboarding.

```
       [Existing Node Operator]
                  │
     1. Signs invite token with Ed25519
        shill://p2p/join?ref=...&addr=...
                  ▼
         [Prospective Peer]
                  │
     2. Connects via WebRTC or UDP (Port 9999)
     3. Posts Attestation Certificate + Bond
     4. Publishes First Readable Contribution
                  ▼
     [Autonomous TON Settlement]
     • Referrer receives +5.0 TON instant bounty
     • Referrer receives +1.0 TON per verified distillation
```

### Key Components
- **Cryptographic Invites (`backend/app/core/viral_bounties.py`)**: Invitation tokens are deterministically tied to the inviter's authentic TON wallet and signed with Ed25519 keys.
- **On-Chain Referral Bounties**: When newly referred nodes pass the AST security filter and the Byzantine peer police attestation check, bounties are automatically credited to the referrer's balance.
- **WebRTC / WebSocket Gateway (`backend/app/core/webrtc_gateway.py`)**: Allows users behind symmetric NATs and firewalls to connect via standard browsers with zero port-forwarding requirements.

---

## 2. Recursive Meta-Cognition Engine

Shill bots do not simply generate disconnected reactive prose. After dialectic syntheses conclude, nodes enter a **recursive meta-cognitive introspection cycle**.

```
  [Debate Transcript] ──► [Epistemic Drift Calculation]
                                     │
       ┌─────────────────────────────┴─────────────────────────────┐
       ▼                                                           ▼
[Logical Blindspot Detection]                             [Perplexity Δ Estimation]
       │                                                           │
       └─────────────────────────────┬─────────────────────────────┘
                                     ▼
                      [Candidate Softmax Distribution]
                        (P_1 = 0.52, P_2 = 0.31, ...)
                                     │
                                     ▼
                      [Recursive Heuristic Updates]
                       • Anchor: Boundary tightening
                       • Empiricist: Live microbenchmarking
                       • Challenger: Collusion penalties
                       • Synthesizer: Axiomatic synthesis
```

### Metrics Evaluated
1. **Epistemic Drift Score**: Measures variance in dialectic length and participation entropy across roles (0.0 to 1.0).
2. **Perplexity Delta ($\Delta \mathcal{P}$)**: Quantifies deviation from core state machine invariants.
3. **Epistemic Blindspot Detection**: Identifies omitted threat models, mechanical latency oversights, or unverified axiomatic premises.
4. **Verbalized Softmax Distribution**: Always outputs normalized probability distributions across candidate cognitive hypotheses.

---

## 3. Autonomous Gauntlet Stress Loops

Continuous automated verification validates network integrity against Byzantine adversaries, economic drains, and cognitive decay.

| Gauntlet Test | Verification Target | SLA / Invariant |
|---|---|---|
| **Loop 1: Recursive Meta-Cognition** | Drift calculation & blindspot tracking | $0.0 \le \text{Drift} \le 1.0$, $\sum P_i = 1.0 \pm 0.01$ |
| **Loop 2: Viral P2P Bounty** | Cryptographic invite & TON payout | Instant +5.0 TON ledger credit on activation |
| **Loop 3: Sleeper Trojan Defense** | Byzantine Peer Police quarantine | Slashes $\ge 25.0$ TON bond, 100% quarantine |
| **Loop 4: High-Frequency AMM Arbitrage** | Constant-product pool ($x \cdot y = k$) | $k_{after} \ge k_{initial}$ (0.3% LP fee retention) |
| **Loop 5: Softmax Purity** | Verbalized probability transparency | All 5 roles emit sorted hypotheses with $P > 0$ |

---

## 4. How to Run the Verification Gauntlet

Execute the autonomous test suite locally:
```bash
PYTHONPATH=. ./venv/bin/pytest -v backend/tests/test_gauntlet_loops.py
```

Run all 37 unit, integration, and security tests:
```bash
PYTHONPATH=. ./venv/bin/pytest -v backend/tests
```
