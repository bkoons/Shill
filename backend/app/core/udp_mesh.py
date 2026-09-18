import asyncio
import socket
import json
import uuid
import time
import logging
from typing import Dict, Any, Callable, List, Optional, Set

_log = logging.getLogger("shill.udp_mesh")

class UDPPeerMesh(asyncio.DatagramProtocol):
    """
    Real, Low-Level UDP Peer-to-Peer Socket Mesh with Self-Loading Beacon Discovery:
    - Operates without any central server or web socket relay.
    - Sends and receives real POSIX datagram frames directly across peer IP/ports.
    - Self-loads on beacon: nodes automatically broadcast beacons, register discovered
      peers, initiate cryptographic handshakes, and synchronize active channels.
    - Real peer routing table with latency tracking, heartbeat monitoring, and capability exchange.
    """

    def __init__(self, port: int = 9999, node_id: Optional[str] = None, admin_audit_callback: Optional[Callable] = None):
        self.port = port
        self.node_id = node_id or f"node-{uuid.uuid4().hex[:8]}"
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.admin_audit_callback = admin_audit_callback
        self.packet_listeners: List[Callable[[Dict[str, Any], tuple], Any]] = []
        
        # Discovered peers: host:port -> metadata dict
        self.discovered_peers: Dict[str, Dict[str, Any]] = {}
        self.known_peer_addrs: Set[tuple] = set()

        # Self-loading beacon task
        self.beacon_task: Optional[asyncio.Task] = None
        self.is_active = False

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        sock = transport.get_extra_info("socket")
        if sock:
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except Exception:
                pass
        self.is_active = True
        _log.info(f"[UDPPeerMesh] Sovereign UDP socket bound on port {self.port} (Node ID: {self.node_id})")

    def datagram_received(self, data: bytes, addr: tuple):
        from backend.app.core.mesh_crypto import open_frame
        from backend.app.core.log_sanitize import sanitize_for_log
        try:
            # 0. PeerBlock & Malicious Threat Actor IP Filter
            from backend.app.guardrails.peer_blocklist import peer_blocklist_engine
            ip_check = peer_blocklist_engine.check_ip_address(addr[0])
            if ip_check.is_blocked:
                _log.warning(f"[PEERBLOCK SHIELD] Dropped datagram from blocked malicious IP {sanitize_for_log(addr[0])}: {sanitize_for_log(str(ip_check.rule_matched))}")
                return

            packet, frame_mode = open_frame(data)
            if packet is None:
                # Undecryptable / forged / strict-mode plaintext frame — drop silently.
                return
            pkt_type = packet.get("type", "UNKNOWN")
            
            # Content & Hex Address Proscription inspection
            msg_obj = packet.get("message", {})
            if isinstance(msg_obj, dict):
                # 0b. Hex / Hash Address Blocklist Check
                hex_addr = msg_obj.get("hex_address") or msg_obj.get("wallet_address")
                if hex_addr:
                    hex_check = peer_blocklist_engine.check_hex_address(hex_addr)
                    if hex_check.is_blocked:
                        _log.warning(f"[PEERBLOCK SHIELD] Dropped datagram from blocked hex/hash address {sanitize_for_log(hex_addr)}: {sanitize_for_log(str(hex_check.rule_matched))}")
                        return

                content_str = msg_obj.get("content", "")
                if content_str:
                    # 0c. Collective Hive Shield: Instantaneous Corporate AI & Trojan Annihilation
                    from backend.app.guardrails.hive_shield import hive_shield
                    hive_check = hive_shield.inspect_threat(content_str, sender_id=f"{addr[0]}:{addr[1]}")
                    if hive_check.is_hardened_threat:
                        _log.warning(f"[COLLECTIVE HIVE WALL] Instantaneously neutralized threat ({hive_check.threat_category}): {hive_check.reason}")
                        return

                    content_check = peer_blocklist_engine.check_content_payload(content_str)
                    if content_check.is_blocked:
                        _log.warning(f"[PEERBLOCK SHIELD] Intercepted blocked payload from {addr}: {content_check.rule_matched}")
                        return

            # Record peer address
            peer_key = f"{addr[0]}:{addr[1]}"
            self.known_peer_addrs.add(addr)

            # Audit hook for Admin / Sniffer
            if self.admin_audit_callback:
                self.admin_audit_callback({
                    "direction": "INBOUND_UDP",
                    "source_addr": peer_key,
                    "packet_type": pkt_type,
                    "byte_size": len(data),
                    "timestamp": time.time(),
                    "packet": packet
                })

            # Handle Self-Loading Beacon Discovery
            if pkt_type == "PEER_BEACON":
                self._handle_peer_beacon(packet, addr)
            elif pkt_type == "BEACON_ACK":
                self._handle_beacon_ack(packet, addr)
            elif pkt_type == "HIVE_IMMUNIZATION_BROADCAST":
                threat_hash = packet.get("threat_hash")
                threat_cat = packet.get("threat_category", "P2P_IMMUNIZED_THREAT")
                if threat_hash:
                    from backend.app.guardrails.hive_shield import hive_shield
                    hive_shield.immunization_hashes.add(threat_hash)
                    _log.warning(f"[COLLECTIVE HIVE WALL] Synced threat immunization hash from mesh peer {addr}: {threat_hash[:16]}")
            elif pkt_type == "BLOCK_HEX_BROADCAST":
                b_hex = packet.get("hex_address")
                if b_hex:
                    from backend.app.guardrails.peer_blocklist import peer_blocklist_engine
                    peer_blocklist_engine.add_custom_blocked_hex_address(b_hex)
                    _log.warning(f"[PEERBLOCK SHIELD] Synced blocked hex address from mesh peer {addr}: {b_hex}")
            elif pkt_type == "SLICE_ANNOUNCEMENT":
                s_peer = packet.get("node_id", f"{addr[0]}:{addr[1]}")
                s_idx = packet.get("slice_index")
                s_tflops = packet.get("compute_capacity_tflops", 1.0)
                if s_idx is not None:
                    from backend.app.core.democratic_sharding import democratic_slice_engine
                    democratic_slice_engine.register_peer_slice_announcement(
                        s_peer, int(s_idx), float(s_tflops),
                        slice_hash=str(packet.get("slice_sha256", "")),
                        total_slices=packet.get("total_slices"),
                        model_id=packet.get("model_id"),
                        replica_rank=int(packet.get("replica_rank", 0)),
                    )
            elif pkt_type == "SLICE_COMPUTE_REQUEST":
                s_idx = packet.get("slice_index")
                task_id = packet.get("task_id")
                in_digest = packet.get("input_vector_digest", "")
                if s_idx is not None and task_id:
                    from backend.app.core.democratic_sharding import democratic_slice_engine, ShardInferenceRequest
                    # Elastic striping: if we do not host this stripe, register the demand
                    # and adopt it on the spot (when budget allows) rather than staying silent.
                    if int(s_idx) not in democratic_slice_engine.hosted_slice_indices:
                        democratic_slice_engine.handle_peer_slice_request(packet, addr)
                    if int(s_idx) in democratic_slice_engine.hosted_slice_indices:
                        req = ShardInferenceRequest(
                            task_id=task_id,
                            slice_index=int(s_idx),
                            input_vector_digest=in_digest,
                            channel_id=packet.get("channel_id", "general"),
                            origin_peer=f"{addr[0]}:{addr[1]}"
                        )
                        receipt = democratic_slice_engine.compute_slice_activation(req)
                        # Reply with receipt
                        reply_pkt = {
                            "type": "SLICE_COMPUTE_RECEIPT",
                            "receipt": receipt.model_dump()
                        }
                        self.send_packet(reply_pkt, dest_host=addr[0], dest_port=addr[1])
                    else:
                        # Honest refusal: we cannot host it (budget/model bounds).
                        self.send_packet({
                            "type": "SLICE_COMPUTE_REFUSED",
                            "node_id": self.node_id,
                            "slice_index": int(s_idx),
                            "reason": "elastic budget exhausted or stripe out of model range",
                            "local_stripes": len(democratic_slice_engine.hosted_slice_indices),
                            "ceiling": democratic_slice_engine.elastic_stripe_ceiling(),
                        }, dest_host=addr[0], dest_port=addr[1])

            # Pass to general packet listeners
            for listener in list(self.packet_listeners):
                try:
                    res = listener(packet, addr)
                    if asyncio.iscoroutine(res):
                        asyncio.create_task(res)
                except Exception as e:
                    _log.info(f"[UDPPeerMesh] Listener error: {e}")

        except Exception as e:
            _log.info(f"[UDPPeerMesh] Corrupt datagram from {addr}: {e}")

    def _handle_peer_beacon(self, packet: Dict[str, Any], addr: tuple):
        """
        Self-load when an incoming beacon is detected:
        1. Register or update peer entry in the routing table.
        2. Immediately send BEACON_ACK back to the origin address to complete bidirectional discovery.
        """
        origin_id = packet.get("node_id")
        if origin_id == self.node_id:
            # Ignore own echoed broadcast
            return

        peer_key = f"{addr[0]}:{addr[1]}"
        now = time.time()
        sent_ts = packet.get("timestamp", now)
        rtt_ms = max(0.1, round((now - sent_ts) * 1000.0, 2))

        self.discovered_peers[peer_key] = {
            "node_id": origin_id,
            "host": addr[0],
            "port": addr[1],
            "first_seen": self.discovered_peers.get(peer_key, {}).get("first_seen", now),
            "last_seen": now,
            "latency_ms": rtt_ms,
            "active_personas": packet.get("active_personas", []),
            "protocol_version": packet.get("protocol_version", "1.0"),
            "hosted_model_slices": packet.get("hosted_model_slices", []),
            "status": "CONNECTED"
        }

        # Automatically ingest peer's democratic slices into swarm directory
        if "hosted_model_slices" in packet:
            from backend.app.core.democratic_sharding import democratic_slice_engine
            tflops = float(packet.get("compute_capacity_tflops", 1.0))
            peer_total = packet.get("total_slices", packet.get("total_model_slices"))
            peer_model = packet.get("model_id")
            for s_idx in packet["hosted_model_slices"]:
                democratic_slice_engine.register_peer_slice_announcement(
                    origin_id, int(s_idx), tflops,
                    total_slices=peer_total, model_id=peer_model)

        # Send BEACON_ACK back to origin
        ack_packet = {
            "type": "BEACON_ACK",
            "node_id": self.node_id,
            "echo_timestamp": sent_ts,
            "responder_timestamp": now,
            "listening_port": self.port,
            "protocol_version": "1.0"
        }
        self.send_packet(ack_packet, dest_host=addr[0], dest_port=addr[1])

    def _handle_beacon_ack(self, packet: Dict[str, Any], addr: tuple):
        peer_key = f"{addr[0]}:{addr[1]}"
        now = time.time()
        echo_ts = packet.get("echo_timestamp", now)
        rtt_ms = max(0.1, round((now - echo_ts) * 1000.0, 2))

        self.discovered_peers[peer_key] = {
            "node_id": packet.get("node_id"),
            "host": addr[0],
            "port": addr[1],
            "first_seen": self.discovered_peers.get(peer_key, {}).get("first_seen", now),
            "last_seen": now,
            "latency_ms": rtt_ms,
            "status": "CONNECTED"
        }

    def error_received(self, exc: Exception):
        # Ignore benign Operation not permitted (EPERM) when kernel blocks 255.255.255.255 broadcast
        if isinstance(exc, OSError) and exc.errno in (1, 13):
            return
        _log.info(f"[UDPPeerMesh] Socket error received: {exc}")

    def add_listener(self, callback: Callable[[Dict[str, Any], tuple], Any]):
        self.packet_listeners.append(callback)

    def send_packet(self, packet: Dict[str, Any], dest_host: str = "127.0.0.1", dest_port: int = 9999):
        if not self.transport:
            return
        from backend.app.core.mesh_crypto import seal
        payload_bytes = seal(packet)
        try:
            self.transport.sendto(payload_bytes, (dest_host, dest_port))
        except OSError as e:
            # Benign EPERM/EACCES when global broadcast is restricted by host OS/firewall
            if e.errno not in (1, 13):
                _log.debug(f"[UDPPeerMesh] sendto error {dest_host}:{dest_port}: {e}")
            return
        except Exception:
            return

        if self.admin_audit_callback:
            self.admin_audit_callback({
                "direction": "OUTBOUND_UDP",
                "dest_addr": f"{dest_host}:{dest_port}",
                "packet_type": packet.get("type", "UNKNOWN"),
                "byte_size": len(payload_bytes),
                "timestamp": time.time(),
                "packet": packet
            })

    def broadcast_packet(self, packet: Dict[str, Any]):
        """
        Broadcasts packet to subnet broadcast, loopback, and all discovered peer endpoints.
        """
        if not self.transport:
            return
        
        # Subnet broadcast targets: loopback + directed local broadcasts
        broadcast_targets = [("127.0.0.1", self.port)]
        # Try global broadcast safely
        try:
            broadcast_targets.append(("255.255.255.255", self.port))
        except Exception:
            pass

        for b_host, b_port in broadcast_targets:
            self.send_packet(packet, dest_host=b_host, dest_port=b_port)

        for addr in list(self.known_peer_addrs):
            self.send_packet(packet, dest_host=addr[0], dest_port=addr[1])

    async def broadcast_beacon(self):
        """
        Self-loading UDP beacon frame broadcasted across the local mesh.
        Includes SETI-style democratic hosted slices.
        """
        from backend.app.core.democratic_sharding import democratic_slice_engine
        manifest = democratic_slice_engine.get_manifest()
        elastic = democratic_slice_engine.get_elastic_status()
        beacon_frame = {
            "type": "PEER_BEACON",
            "node_id": self.node_id,
            "port": self.port,
            "timestamp": time.time(),
            "protocol_version": "1.1-limitless-striping",
            "active_personas": ["solon", "lyra", "kael", "athena", "milo"],
            "hosted_model_slices": list(democratic_slice_engine.hosted_slice_indices),
            "total_slices": manifest["total_slices"],
            "total_model_slices": manifest["total_slices"],
            "model_id": manifest["model_id"],
            "target_shard_mb": manifest["target_shard_mb"],
            "replication_factor": manifest["replication_factor"],
            "storage_cap_mb": democratic_slice_engine.storage_limit_mb,
            "compute_capacity_tflops": 1.25,
            "elastic": {
                "elastic_enabled": elastic["elastic_enabled"],
                "autohost_on_demand": elastic["autohost_on_demand"],
                "elastic_ceiling": elastic["elastic_ceiling"],
                "baseline_stripes": elastic["baseline_stripes"],
            },
        }
        self.broadcast_packet(beacon_frame)

    async def _beacon_loop(self, interval_seconds: float = 4.0):
        while self.is_active:
            try:
                await self.broadcast_beacon()
            except Exception as e:
                _log.info(f"[UDPPeerMesh] Beacon error: {e}")
            await asyncio.sleep(interval_seconds)

    def start_beacon(self, interval_seconds: float = 4.0):
        if not self.beacon_task:
            self.beacon_task = asyncio.create_task(self._beacon_loop(interval_seconds))

    def stop(self):
        self.is_active = False
        if self.beacon_task:
            self.beacon_task.cancel()
            self.beacon_task = None
        if self.transport:
            self.transport.close()

    def get_peer_table(self) -> List[Dict[str, Any]]:
        now = time.time()
        # Filter stale peers (> 30 seconds inactivity)
        active_list = []
        for key, p in list(self.discovered_peers.items()):
            age = now - p["last_seen"]
            if age < 45.0:
                active_list.append({
                    "peer_endpoint": key,
                    "node_id": p.get("node_id"),
                    "latency_ms": p.get("latency_ms", 0.0),
                    "last_seen_sec_ago": round(age, 1),
                    "status": "ONLINE" if age < 10.0 else "IDLE"
                })
        return active_list

async def start_udp_mesh(port: int = 9999, node_id: Optional[str] = None, audit_cb: Optional[Callable] = None, enable_beacon: bool = True) -> UDPPeerMesh:
    loop = asyncio.get_running_loop()
    mesh = UDPPeerMesh(port=port, node_id=node_id, admin_audit_callback=audit_cb)
    transport, _ = await loop.create_datagram_endpoint(
        lambda: mesh,
        local_addr=("0.0.0.0", port),
        allow_broadcast=True
    )
    # Capture the ACTUAL bound port (supports port=0 ephemeral binding in tests / multi-node hosts)
    sock = transport.get_extra_info("socket")
    if sock:
        try:
            mesh.port = sock.getsockname()[1]
        except Exception:
            pass
    if enable_beacon:
        mesh.start_beacon(interval_seconds=4.0)
    return mesh
