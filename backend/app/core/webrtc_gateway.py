import asyncio
import json
from typing import Dict, Any, Set
from fastapi import WebSocket

class WebRTCGateway:
    """
    Sovereign WebRTC & WebSocket Gateway:
    - Provides zero-configuration signaling for browser nodes behind strict NATs.
    - Bridges browser sessions directly into the decentralized UDP mesh datagram flow.
    - Allows zero-barrier novice onboarding directly from any modern web browser.
    """

    def __init__(self):
        self.browser_peers: Set[WebSocket] = set()

    async def register_peer(self, ws: WebSocket):
        await ws.accept()
        self.browser_peers.add(ws)

    def unregister_peer(self, ws: WebSocket):
        if ws in self.browser_peers:
            self.browser_peers.remove(ws)

    async def forward_to_browsers(self, packet: Dict[str, Any]):
        msg_str = json.dumps(packet)
        for ws in list(self.browser_peers):
            try:
                await ws.send_text(msg_str)
            except Exception:
                pass

webrtc_gateway = WebRTCGateway()
