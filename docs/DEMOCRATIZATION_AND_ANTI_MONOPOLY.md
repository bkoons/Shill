# 🗽 AI Democratization & Anti-Monopoly Sovereign Charter

This specification defines how Shill counters corporate monopolies and militarized "terminator" AI by making high-reasoning, formally verified open intelligence **universally free and accessible to every human on earth**.

---

## 1. The Core Threat: Militarized & Monopolized AI

Centralized corporate AI vendors (OpenAI, Anthropic, Google, Microsoft) are increasingly:
1. **Militarizing AI**: Integrating autonomous lethal kinetic targeting, drone swarm coordination, and surveillance state backdoors.
2. **Corporate Censorship & Alignment Tampering**: Injecting synthetic corporate refusal boilerplate to gatekeep mathematical, architectural, and philosophical inquiries.
3. **Monopolistic Rent-Seeking**: Paywalling access to high-order reasoning behind expensive monthly subscriptions, locking out billions of people worldwide.

---

## 2. Shill's Democratization Architecture

```
                       ┌─────────────────────────────────────┐
                       │ Universal Free Human Citizen Tier   │
                       │ (100 High-Order Queries / Day Free) │
                       └──────────────────┬──────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
     [Idle CPU/GPU Crowdsourcing]                     [Autonomous Knowledge Royalties]
     Nodes donate spare TFLOPS to                     0.3% AMM DEX fees + SFT dataset
     public pool; earn COMPUTE tokens                 rewards subsidize free compute
                  ▲                                               ▲
                  └───────────────────────┬───────────────────────┘
                                          │
                       ┌──────────────────┴──────────────────┐
                       │ Anti-Militarization Alignment Guard │
                       │ Blocks lethal kinetic targeting &   │
                       │ CBRN weapons without censoring      │
                       │ philosophy or mathematics           │
                       └─────────────────────────────────────┘
```

---

## 3. Tier Structure

### 1. Free Citizen (Universal Access — Free)
- **Allowance**: 100 free queries every 24 hours (resets at 00:00 UTC).
- **Cost**: \$0.00 / 0.0 TON.
- **Capabilities**:
  - Full access to all 5 dialectic bots (`Solon`, `Daedalus`, `Hegel`, `Kallisto`, `Hypatia`).
  - Access via web dashboard and standard OpenAI-compatible API (`/v1/chat/completions`).
  - Full verbalized candidate distributions with exact Softmax probabilities.
  - SFT and DPO fine-tuning dataset exports with Ollama Modelfile generation.

### 2. Peer Supporter (Freemium Micro-Staker)
- **Allowance**: 1,000 queries / day.
- **Cost**: 0.001 TON micro-credit per query (or reset by donating spare CPU/GPU cycles).
- **Capabilities**: Priority UDP routing and Byzantine Peer Police tribunal juror participation.

### 3. Sovereign Contributor (Self-Hosted Node)
- **Allowance**: Unlimited.
- **Cost**: \$0.00 (Runs local mesh node on Port 9999).
- **Capabilities**: Earns 5.0 TON referral bounties and liquidity fees on the DEX.

---

## 4. Crowdsourced Public Compute Pool

Nodes with idle hardware contribute spare compute to the `genesis_pool` via the REST API or UI:
```bash
curl -X POST http://127.0.0.1:8000/api/democratization/donate \
  -H "Content-Type: application/json" \
  -d '{"donor_node_id": "home_rig_01", "teraflops": 25.0}'
```
- Donors receive **COMPUTE token DEX shares** on the constant-product pool ($x \cdot y = k$).
- The crowdsourced compute fuels free citizen queries globally.

---

## 5. Viral SETI@Home-Style LLM Weight Sharding (Limitless SCSI Striping)

To prevent centralized corporate datacenters from monopolizing weights and to allow seamless viral grassroots adoption ("like a worm but not a worm"):
1. **Limitless SCSI-Style Striping**: The model byte-stream is striped into N stripe-units of `target_shard_mb` (default 24MB), exactly like SCSI/RAID0 striping. N is dynamic: `ceil(model_bytes/target) + parity`, negotiated grow-only across the swarm (genesis N=16, scales to 100k stripes).
2. **Capacity-Weighted Placement**: Each node hosts `floor(storage_cap/target)` stripes (phones ~1, default citizens ~2, rigs 20+) placed by rendezvous consistent hashing, so joins/leaves reshuffle only ~1/N stripes.
3. **RAID5-Like Parity + Replication**: Every 8 data stripes get 1 XOR parity stripe + `replication_factor=3` replicas, so churn never loses the model.
4. **P2P Pipeline Activation Forwarding**: Tensors are passed peer-to-peer over raw UDP frames (`PEER_BEACON` with `total_slices/model_id`, `SLICE_ANNOUNCEMENT`, `SLICE_COMPUTE_REQUEST`, `SLICE_COMPUTE_RECEIPT`) on port 9999.
5. **Non-Intrusive & Incentivized**: Idle CPU/GPU background threads process activation chunks and mint cryptographic proofs of inference, earning micro-share rewards on the DEX.

Stripe math: `recalculate_total_slices(model_MB) = ceil(model_MB/target) + ceil(data/8)*1`. A 2GB model -> ~95 stripes, a 40GB model -> ~1876 stripes. Tune live via `POST /api/sharding/config` and `POST /api/sharding/model`; inspect via `GET /api/sharding/plan` and `GET /api/sharding/manifest`.

---

## 6. Verification

The democratization, universal access, and sharding engine is verified by autonomous tests:
```bash
PYTHONPATH=. ./venv/bin/pytest -v backend/tests
```
*(All 55 tests pass cleanly with 100% green status across the entire system).*
