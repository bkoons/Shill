# Deep Dive Audit & Problem Resolution Report
Date: 2026-09-17

## Executive Summary
A targeted, deep-dive code audit was conducted across the codebase focusing on:
1. Concurrency safety & async event broadcasting.
2. WebRTC gateway integration & browser socket connection management.
3. API router imports & namespace cleanliness.
4. Input bounds, edge-case validation, and cryptographic signature consistency.

---

## 1. Identified Issues & Architecture Inconsistencies

### Issue 1: `turn_manager.subscribe` Synchronous Invocation of Coroutine in `routes.py`
- **Location**: `backend/app/api/routes.py:42`
- **Mechanism**: `turn_manager.subscribe(lambda event: ws_manager.broadcast(event))` passes a lambda returning an unawaited coroutine object (`async def broadcast`), while `turn_manager.broadcast` expects either an async function or explicitly schedules it.
- **Fix**: Wrapped the websocket broadcast cleanly using `asyncio.create_task` or registering an `async` callback directly so coroutines are never dropped unawaited.

### Issue 2: WebRTC Gateway Disconnect from Mesh Broadcast
- **Location**: `backend/app/core/webrtc_gateway.py`
- **Mechanism**: `webrtc_gateway` was instantiated as a singleton but was not wired into `turn_manager.broadcast()` or `ws_manager`, leaving browser clients connected via WebRTC signaling without direct mesh datagram forwarding.
- **Fix**: Unified WebRTC gateway forwarding with WebSocket event dispatching.

### Issue 3: Mid-File Imports & Scoping in `admin.py`
- **Location**: `backend/app/api/admin.py`
- **Mechanism**: Modules (`Header`, `p2p_model_distributor`, `sysop_jury_engine`, `SYSOPS`) were imported midway through the file (lines 69, 137, 159, 167), which violates clean module scoping and can lead to subtle initialization ordering bugs.
- **Fix**: Consolidated all imports cleanly at the top of `backend/app/api/admin.py`.

### Issue 4: Dynamic Port Binding Alignment
- **Location**: `backend/main.py`
- **Mechanism**: `main.py` hardcoded port 8000 when executed as `__main__`, ignoring the `PORT` environment variable passed by `start.sh` and `install.sh`.
- **Fix**: Standardized `PORT = int(os.getenv("PORT", "8000"))`.

---

## 2. Automated Resolution Script
A dedicated Python repair script `scripts/fix_codebase_issues.py` was implemented and executed to resolve these issues deterministically.
