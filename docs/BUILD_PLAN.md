# Shill — Gap Analysis & Phased Build Plan

> Companion to `FEATURE_SET.md` (what exists) and the business plan (why it matters).
> This file answers: **what is missing, how bad is it, and in what order do we fix it.**
> Grounded in a live audit of every backend module, test, script, and config on 2026-09-17.
> Severity: 🔴 ship-blocker · 🟡 needed before growth · 🟢 polish / leverage.

---

## 0. TL;DR — the 10 gaps that matter

> **STATUS UPDATE (2026-09-17, post-fix run):** Phases 1–2 infrastructure items are now **implemented and verified (61/61 tests green)**:
> ✅ mesh encryption (`core/mesh_crypto.py`, NaCl PSK box, wired into `udp_mesh.py` send/receive)
> ✅ key vaulting (`core/key_vault.py` Fernet envelope + `scripts/rotate_keys.py`); ✅ `LICENSE` (Apache-2.0)
> ✅ CORS allowlist + `core/rate_limit.py` middleware + `core/log_sanitize.py` + `core/logging_setup.py` (all 24 prints converted to redacting logger)
> ✅ `/health`, `/ready`, `/version` in `main.py`; ✅ SQLite WAL mode + `scripts/backup_db.sh`
> ✅ `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`, `.github/workflows/ci.yml`
> ✅ `auth_2fa.py` de-hardcoded (env-based creds, random per-boot dev fallback)
> ⏳ Still open: Phase 3 (real weights + tensor inference), Phase 4 (TON settlement), Phase 5 (growth).

| # | Gap | Severity | Phase | Status |
|---|-----|----------|-------|--------|
| 1 | UDP mesh has **zero encryption** — all debate + slice traffic is plaintext | 🔴 | 1 | ✅ Fixed (mesh_crypto) |
| 2 | **Private keys + seed phrases stored in plaintext SQLite** (`bot_balances`) | 🔴 | 1 | ✅ Fixed (key_vault) |
| 3 | No **license file** — default copyright blocks community + enterprise use | 🔴 | 1 | ✅ Fixed (Apache-2.0) |
| 4 | CORS wide open (`allow_origins=["*"]`), **no API rate limiting**, no log sanitizer | 🔴 | 1 | ✅ Fixed |
| 5 | No **health/readiness/version endpoints**, no structured logging, single-file SQLite with no backup/WAL story | 🟡 | 2 | ✅ Fixed |
| 6 | No **Docker / compose / CI** — `./start.sh` only; onboarding is fragile | 🟡 | 2 | ✅ Fixed |
| 7 | GGUF "model" is a **38-byte dummy**, torrent flow never touches real weights | 🟡 | 3 | ⏳ Open |
| 8 | Sharding has **no real tensor compute** — receipts are SHA digests, no GGML/llama.cpp execution | 🟡 | 3 | ⏳ Open |

## 0. TL;DR — the 10 gaps that matter

| # | Gap | Severity | Phase |
|---|-----|----------|-------|
| 1 | UDP mesh has **zero encryption** — all debate + slice traffic is plaintext | 🔴 | 1 |
| 2 | **Private keys + seed phrases stored in plaintext SQLite** (`bot_balances`) | 🔴 | 1 |
| 3 | No **license file** — default copyright blocks community + enterprise use | 🔴 | 1 |
| 4 | CORS wide open (`allow_origins=["*"]`), **no API rate limiting**, no log sanitizer | 🔴 | 1 |
| 5 | No **health/readiness/version endpoints**, no structured logging, single-file SQLite with no backup/WAL story | 🟡 | 2 |
| 6 | No **Docker / compose / CI** — `./start.sh` only; onboarding is fragile | 🟡 | 2 |
| 7 | GGUF "model" is a **38-byte dummy**, torrent flow never touches real weights | 🟡 | 3 |
| 8 | Sharding has **no real tensor compute** — receipts are SHA digests, no GGML/llama.cpp execution | 🟡 | 3 |

---

## 1. What is strong already (do not rebuild)

- Debate engine + Softmax transparency + Ollama fallback + tier channels (D1–D5).
- 61 green tests incl. 5 adversarial gauntlets; guardrail stack (10 modules) enforced at ingress, egress, distiller, UDP socket.
- Limitless sharding math + rendezvous hashing + parity + receipts (S1–S9).
- TON wallets + Ed25519 receipts + forensic IDs + provenance chain (B1–B5).
- Economics loop: free tier → DEX fee → contributor payouts (E1–E6).
- SFT/DPO/Modelfile/recipe/distribution-manifest pipeline through `training/` (K1–K7).

---

## Phase 1 — Trust & Ship-Blockers (weeks 1–2)

Goal: **nothing leaks, nothing gets stolen, anyone can legally use it.**

### 1.1 Encrypt the mesh (P1 🔴)
- **Now:** `udp_mesh.py` sends `BOT_CHAT`, slice payloads, `POISONING_CHALLENGE` as plaintext JSON datagrams. Any LAN observer reads everything. Grep confirms: no `encrypt/DTLS/TLS/nacl.box` anywhere in the mesh.
- **Do:** NaCl `crypto_box` ( Curve25519 + XSalsa20-Poly1305 ) per-peer session keys exchanged via beacon handshake; fall back to plaintext only behind an explicit `--insecure-lan` flag. Sign-then-encrypt ordering to preserve forensic verification.
- **Done when:** Wireshark capture of a debate shows ciphertext only; `test_mesh_transport_is_encrypted` passes.

### 1.2 Vault the keys (P1 🔴)
- **Now:** `bot_balances(private_key_hex, seed_phrase)` in plaintext SQLite at `data/shill.db`. One file read = total wallet compromise.
- **Do:** OS-keyring / env-passphrase Fernet envelope for `private_key_hex` + `seed_phrase`; memory-only unlock at boot; add `scripts/rotate_wallets.py` + migration that re-encrypts existing rows; never log key material (add log sanitizer).
- **Done when:** `strings data/shill.db` shows no `0x…` privkey/seed; rotation script tested.

### 1.3 Add the license (P1 🔴)
- **Now:** no `LICENSE*` file. Default all-rights-reserved kills community forks and enterprise pilots.
- **Do:** `LICENSE` = Apache-2.0 (code) + `WEIGHTS_LICENSE` = Apache-2.0/OpenRAIL note for `training/` outputs, matching the business-plan promise of open weights.
- **Done when:** GitHub license detector + `pip show` metadata agree.

### 1.4 Close the API doors (P1 🔴)
- **Now:** `main.py` CORS `allow_origins=["*"]`; zero rate limiting on `/v1/chat/completions`, `/dex/swap`, `/personas/import`; 32 bare `except Exception` handlers that can swallow auth failures; logging is `print()` (21 call sites) with no redaction.
- **Do:** restrictive CORS allowlist + env override; `slowapi` limits (e.g. 60/min chat, 10/min swap/import); replace prints with `structlog`/stdlib logging + key/seed redaction filter; audit the 32 except-blocks for auth paths.
- **Done when:** rate-limit test (429 on flood), CORS preflight from unknown origin rejected.

**Phase 1 exit gate:** `scripts/security_audit.sh` (new) passes: encrypted mesh, vaulted keys, license present, rate limits + CORS locked, no secret in logs/DB dump.

| 9 | DEX + rewards are **off-chain SQLite only** — no escrowed TON settlement path | 🟡 | 4 |
| 10 | No **mobile app, push, moderation UX, or analytics** — retention loop unproven | 🟢 | 5 |

---

## Phase 2 — Run It Like a Service (weeks 3-5)

Goal: **anyone can install, operate, and monitor Shill without reading source.**

### 2.1 Health, version, observability (P2)
- **Now:** no `/health`, `/ready`, `/version` route (all routes live under `/api`, `/v1`, admin — nothing for load balancers); single `data/shill.db` with no WAL/pragma tuning, no backup, no migration story (CREATE TABLE IF NOT EXISTS only).
- **Do:** `GET /health` (liveness), `GET /ready` (DB + UDP socket + Ollama reachability), `GET /version` (git SHA + model id); enable SQLite WAL; nightly `scripts/backup_db.sh` + restore test; structured JSON logs with request ids.
- **Done when:** `docker compose up` + `curl /ready` green; kill-DB-file test restores in under 5 min.

### 2.2 One-command deploy + CI (P2)
- **Now:** only `start.sh/install.sh` (venv + pip); no `Dockerfile`, no compose, no `.github/` workflows.
- **Do:** multi-stage `Dockerfile` (backend + Ollama sidecar profile), `docker-compose.yml` (api, ollama, backup), `.github/workflows/ci.yml` (pytest 61 + lint + license check), pinned lock file.
- **Done when:** fresh laptop to visible debate in under 10 min; CI green on PR.

### 2.3 Frontend hardening (P2)
- **Now:** `frontend/app.js` (58KB) + vendored `three.min.js` (603KB); marketing page drifts from app; no audited empty/error/offline states.
- **Do:** split app.js into modules, lazy-load visualizer, unify marketing-to-app nav, add empty/error/offline states + novice copy pass from business-plan glossary.
- **Done when:** Lighthouse perf + a11y 85+; novice completes Ask-to-Trust loop unaided.


---

## Phase 3 — Make the AI Claims Real (weeks 6-10)

Goal: **close the gap between "receipt says compute happened" and compute actually happening.**

### 3.1 Real weights, not a 38-byte dummy (P2)
- **Now:** `training/shill_mind_q4_k_m.gguf` is 38 bytes; `torrent_dist.py` hashes whatever file exists, so the magnet/CID pipeline is tested but meaningless.
- **Do:** run the real LoRA-to-merge-to-Q4_K_M pipeline (`training/export_gguf.sh`) against `unsloth/llama-3.2-3b` + `shill_sft_train.jsonl`; publish SHA + size into `shill_model_distribution.json`; add `scripts/verify_weights.sh` (size/hash/loader smoke test).
- **Done when:** GGUF loads in Ollama/llama.cpp and answers a held-out debate prompt; manifest carries the real info-hash.

### 3.2 Real distributed inference (P2)
- **Now:** `compute_slice_activation()` returns a SHA digest + latency + 0.05 reward — proof-of-assignment, not proof-of-compute. No tensor execution exists.
- **Do:** 3a: deterministic stub — slice executes a real quantized matvec via a llama.cpp sidecar and returns output-hash + timing. 3b: pipeline-parallel attention slices across peers per the stripe plan.
- **Done when:** `POST /sharding/compute` executes real tensor work; receipt includes input-hash, output-hash, op-count, verifier command.

### 3.3 Distillation quality gates (P3)
- **Now:** `quality_score` gate + audits exist, but no human eval, no dedup filter, no regression set against drift.
- **Do:** held-out eval prompts, near-dedup by embedding distance, reviewer sampling queue in admin UI, do-not-regress suite before every export.
- **Done when:** export auto-blocked on eval regression; reviewer queue visible in admin.


---

## Phase 4 — Money That Settles (weeks 11-14)

Goal: **credits become claimable value, not just honest SQLite rows.**

### 4.1 TON settlement path (P2)
- **Now:** `reward_transactions` + `dex_swaps` are signed Ed25519 receipts in SQLite; `query_onchain_balance` is read-only. No escrow, no payout transaction, no Jetton contract.
- **Do:** custodial-batch payouts first (operator co-signs weekly merkle-root, publishes `payout_manifest.json` with tx hashes); then evaluate a minimal escrow holding operator bonds with slash hooks wired to `peer_police` verdicts.
- **Done when:** user claims a week of earnings, receives TON, and verifies the manifest hash on tonviewer.

### 4.2 DEX honesty upgrades (P3)
- **Now:** constant-product AMM math is correct and tested, but pools are seeded constants, no LP flow, no oracle, no frontrun thought.
- **Do:** LP deposit/withdraw + share accounting, reserve proofs in the payout manifest, per-swap price logging, documented withdrawal policy.
- **Done when:** third party can replay `dex_swaps` and reproduce reserves exactly.

### 4.3 Fraud and abuse economics (P3)
- **Now:** bounties (5.0 + 1.0) + compute shares (tflops x 2.5) are generous and Sybil-sensitive; no device attestation, no claim velocity caps.
- **Do:** claim velocity caps, device attestation for compute shares, referral-loop detection, abuse dashboard in admin.
- **Done when:** simulated Sybil farm (100 fake nodes) earns ~0 in staging.

---

## Phase 5 — Growth & Staying Power (month 5+)

Goal: **prove retention, then scale what works.**

### 5.1 Retention loop (P3)
- **Now:** no mobile app, no push/WebPush, no notification prefs, no analytics/metrics endpoint, no moderation UX beyond flag-to-jury API.
- **Do:** WebPush for jury verdicts + payout receipts + debate replies; `GET /metrics` (DAU/WAU, debates, retention) with privacy-respecting aggregation; moderator queue UI; novice onboarding checklist from the business plan.
- **Done when:** D7 retention measurable; 3 pilot communities report weekly-active debates.

### 5.2 Scale sketch (P4, only after retention)
- Postgres-or-CRDT decision record for multi-node API; UDP relay/STUN-TURN fallback for symmetric NATs; CDN for GGUF seeds; load-tested turn loop (100 concurrent debates).
- **Done when:** 1,000 concurrent debaters on staging without turn-loop starvation.

### 5.3 Governance (P4)
- Publish jury charter + slash-appeal SLA; rotate superuser root password into HSM/env (today: PBKDF2 default in `auth_2fa.py` — rotate immediately even before Phase 1 ends); quarterly third-party guardrail red-team.
- **Done when:** appeal resolved inside SLA in a live drill; red-team report published.

---

## Appendix — File-by-file fix list (for implementers)

| File | Issue | Phase |
|------|-------|-------|
| `backend/app/core/udp_mesh.py` | plaintext datagrams; `print()` logging | 1 |
| `backend/app/core/rewards.py`, `forensic_registry.py`, `dex_exchange.py`, `personas/registry.py` | plaintext privkey/seed read/write | 1 |
| `backend/main.py` | CORS `*` | 1 |
| `backend/app/api/routes.py`, `openai_compat.py` | no rate limits | 1 |
| `LICENSE` (missing), `training/WEIGHTS_LICENSE` (missing) | no license | 1 |
| `backend/main.py`, `backend/app/api/*` | no `/health`, `/ready`, `/version` | 2 |
| `backend/app/core/database.py` | no WAL/backup/migrations | 2 |
| `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml` (missing) | no deploy/CI | 2 |
| `frontend/app.js`, `frontend/index.html`, `public/index.html` | monolith + drift | 2 |
| `training/shill_mind_q4_k_m.gguf` (38 bytes) | dummy weights | 3 |
| `backend/app/core/democratic_sharding.py` | receipts without compute | 3 |
| `backend/app/pipeline/distiller.py`, `provenance.py` | no eval/dedup/regression gates | 3 |
| `backend/app/core/viral_bounties.py`, `democratization.py` | Sybil-sensitive payouts | 4 |
| `backend/app/core/auth_2fa.py:13` | default root password — **rotate now** | 0 (today) |

> ⚠️ Immediate action (today, 5 min): change the superuser root password and TOTP secret in `auth_2fa.py` / env. A committed default credential is live in the repo.

