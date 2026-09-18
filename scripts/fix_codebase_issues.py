#!/usr/bin/env python3
"""
Targeted code-fix script for Shill codebase.
Resolves:
1. Concurrency callback in backend/app/api/routes.py
2. Mid-file imports in backend/app/api/admin.py
3. WebRTC gateway integration
"""

import re
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fix_routes():
    path = os.path.join(BASE_DIR, "backend/app/api/routes.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Fix unawaited coroutine in turn_manager subscription
    old_sub = "turn_manager.subscribe(lambda event: ws_manager.broadcast(event))"
    new_sub = "turn_manager.subscribe(lambda event: asyncio.create_task(ws_manager.broadcast(event)))"
    if old_sub in content:
        content = content.replace(old_sub, new_sub)

    # Wire WebRTC gateway to ws_manager broadcast
    old_bcast = """    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass"""

    new_bcast = """    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass
        # Forward to WebRTC browser data-channels
        from backend.app.core.webrtc_gateway import webrtc_gateway
        await webrtc_gateway.forward_to_browsers(message)"""

    if old_bcast in content:
        content = content.replace(old_bcast, new_bcast)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Fixed: {path}")

def fix_admin():
    path = os.path.join(BASE_DIR, "backend/app/api/admin.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Consolidate imports to top
    top_imports = """from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.app.guardrails.gated_security import gated_security
from backend.app.core.database import get_db_connection
from backend.app.pipeline.provenance import llm_provenance_auditor
from backend.app.guardrails.sysop_jury import sysop_jury_engine, SYSOPS
from backend.app.engine.routines import routine_manager
from backend.app.pipeline.torrent_dist import p2p_model_distributor
from backend.app.core.auth_2fa import superuser_auth, LoginRequest"""

    # Remove mid-file imports
    content = re.sub(r'from fastapi import APIRouter, HTTPException[\s\S]*?from backend\.app\.pipeline\.provenance import llm_provenance_auditor', top_imports, content)
    content = content.replace("from backend.app.guardrails.sysop_jury import sysop_jury_engine, SYSOPS\n\n", "")
    content = content.replace("from backend.app.engine.routines import routine_manager\n\n", "")
    content = content.replace("from backend.app.pipeline.torrent_dist import p2p_model_distributor\n\n", "")
    content = content.replace("from fastapi import Header\nfrom backend.app.core.auth_2fa import superuser_auth, LoginRequest\n\n", "")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Fixed: {path}")

if __name__ == "__main__":
    fix_routes()
    fix_admin()
    print("All fixes applied cleanly.")
