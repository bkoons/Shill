import json
import hashlib
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import nacl.signing
import nacl.encoding
from backend.app.core.database import get_db_connection

DEFAULT_MINIMUM_STAKE = 25.0  # 25 TON sovereign operator bond

class OperatorAttestationCert(BaseModel):
    cert_id: str
    operator_id: str
    operator_pubkey_hex: str
    bot_id: str
    bot_spec_hash: str           # SHA-256 of bot persona definition
    staked_ton_amount: float
    attestation_statement: str
    signature_hex: str
    created_at: float
    status: str = "ACTIVE"       # "ACTIVE", "SLASHED", "REVOKED"

class AttestationRegistry:
    """
    Sovereign Operator Attestation & Staking Registry:
    - Enforces cryptographic accountability on any peer deploying bots into the mesh.
    - Operators sign an immutable attestation verifying the bot has no backdoors, corporate spyware, or poisoning payloads.
    - Backed by an on-chain TON security bond that is slashed if peers detect malicious Byzantine activity.
    """

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operator_attestations (
                cert_id TEXT PRIMARY KEY,
                operator_id TEXT NOT NULL,
                operator_pubkey_hex TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                bot_spec_hash TEXT NOT NULL,
                staked_ton_amount REAL NOT NULL,
                attestation_statement TEXT NOT NULL,
                signature_hex TEXT NOT NULL,
                created_at REAL NOT NULL,
                status TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS slashed_operators (
                id TEXT PRIMARY KEY,
                operator_id TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                slashed_amount REAL NOT NULL,
                reason TEXT NOT NULL,
                byzantine_proof_hash TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def compute_spec_hash(bot_id: str, system_prompt: str, role_type: str) -> str:
        payload = f"{bot_id}:{role_type}:{system_prompt.strip()}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def issue_attestation(
        self,
        operator_id: str,
        operator_privkey_hex: str,
        bot_id: str,
        system_prompt: str,
        role_type: str,
        staked_ton: float = DEFAULT_MINIMUM_STAKE
    ) -> OperatorAttestationCert:
        if staked_ton < DEFAULT_MINIMUM_STAKE:
            raise ValueError(f"Insufficient security bond: minimum {DEFAULT_MINIMUM_STAKE} TON required.")

        spec_hash = self.compute_spec_hash(bot_id, system_prompt, role_type)
        now = time.time()
        cert_id = f"cert-{hashlib.sha256(f'{operator_id}:{bot_id}:{now}'.encode('utf-8')).hexdigest()[:12]}"
        statement = (
            f"I, operator {operator_id}, cryptographically attest under sovereign stake that bot '{bot_id}' "
            "contains zero corporate backdoors, data poisoning payloads, or covert sleeper agent triggers. "
            "I agree to complete stake slashing if Byzantine malice is proven."
        )

        canonical_data = json.dumps({
            "cert_id": cert_id,
            "operator_id": operator_id,
            "bot_id": bot_id,
            "bot_spec_hash": spec_hash,
            "staked_ton": staked_ton,
            "statement": statement,
            "timestamp": now
        }, sort_keys=True)

        # Sign with operator's Ed25519 private key
        signing_key = nacl.signing.SigningKey(bytes.fromhex(operator_privkey_hex)[:32])
        signed = signing_key.sign(canonical_data.encode('utf-8'))
        sig_hex = signed.signature.hex()
        pubkey_hex = signing_key.verify_key.encode().hex()

        cert = OperatorAttestationCert(
            cert_id=cert_id,
            operator_id=operator_id,
            operator_pubkey_hex=pubkey_hex,
            bot_id=bot_id,
            bot_spec_hash=spec_hash,
            staked_ton_amount=staked_ton,
            attestation_statement=statement,
            signature_hex=sig_hex,
            created_at=now,
            status="ACTIVE"
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO operator_attestations 
            (cert_id, operator_id, operator_pubkey_hex, bot_id, bot_spec_hash, staked_ton_amount, attestation_statement, signature_hex, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cert.cert_id, cert.operator_id, cert.operator_pubkey_hex, cert.bot_id, cert.bot_spec_hash,
            cert.staked_ton_amount, cert.attestation_statement, cert.signature_hex, cert.created_at, cert.status
        ))
        conn.commit()
        conn.close()

        return cert

    def verify_bot_attestation(self, bot_id: str, system_prompt: str, role_type: str) -> Tuple[bool, Optional[str]]:
        """
        Validates that a bot holds an active, un-slashed cryptographic attestation.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM operator_attestations WHERE bot_id = ? AND status = 'ACTIVE'", (bot_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return False, f"Bot '{bot_id}' has no active cryptographic operator attestation certificate."

        cert = dict(row)
        expected_spec_hash = self.compute_spec_hash(bot_id, system_prompt, role_type)
        if cert["bot_spec_hash"] != expected_spec_hash:
            return False, f"Bot spec mismatch: actual specification differs from operator signed hash."

        # Verify Ed25519 signature
        try:
            canonical_data = json.dumps({
                "cert_id": cert["cert_id"],
                "operator_id": cert["operator_id"],
                "bot_id": cert["bot_id"],
                "bot_spec_hash": cert["bot_spec_hash"],
                "staked_ton": cert["staked_ton_amount"],
                "statement": cert["attestation_statement"],
                "timestamp": cert["created_at"]
            }, sort_keys=True)

            verify_key = nacl.signing.VerifyKey(bytes.fromhex(cert["operator_pubkey_hex"]))
            verify_key.verify(canonical_data.encode('utf-8'), bytes.fromhex(cert["signature_hex"]))
            return True, "Attestation valid and verified."
        except Exception as e:
            return False, f"Cryptographic attestation signature invalid: {e}"

    def slash_operator(self, bot_id: str, reason: str, proof_hash: str) -> float:
        """
        Slashes the operator's locked stake and marks attestation as SLASHED.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM operator_attestations WHERE bot_id = ? AND status = 'ACTIVE'", (bot_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return 0.0

        slashed_amount = row["staked_ton_amount"]
        operator_id = row["operator_id"]
        cert_id = row["cert_id"]

        cursor.execute("UPDATE operator_attestations SET status = 'SLASHED' WHERE cert_id = ?", (cert_id,))
        cursor.execute('''
            INSERT INTO slashed_operators (id, operator_id, bot_id, slashed_amount, reason, byzantine_proof_hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (f"slash-{hashlib.sha256(f'{cert_id}:{time.time()}'.encode()).hexdigest()[:10]}", operator_id, bot_id, slashed_amount, reason, proof_hash, time.time()))

        conn.commit()
        conn.close()
        return slashed_amount

    def list_attestations(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM operator_attestations ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

attestation_registry = AttestationRegistry()
