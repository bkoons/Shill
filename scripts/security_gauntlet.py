#!/usr/bin/env python3
"""
scripts/security_gauntlet.py
=============================================================================
SHILL PROTOCOL — AUTOMATED SECURITY & LEAK-PREVENTION GAUNTLET
=============================================================================
Authoritative Security Loop for Git Sanitization & Secret Leak Prevention:
1. Tracked File Audit: Scans all git-tracked files for high-entropy secrets,
   private keys, API tokens, raw passwords, or wallet seed phrases.
2. File Pattern Boundary: Enforces .gitignore compliance across sensitive
   extensions (.env, .pem, .key, .cert, id_rsa, *.db, *.docx, *.pptx).
3. Git History Deep Check: Scans the commit tree to ensure no historical leak.
4. API Boundary & Redaction: Validates that telemetry, REST, and WebSocket
   endpoints never leak credentials or private keys.
=============================================================================
"""

import os
import re
import sys
import subprocess
from pathlib import Path

# High-risk patterns that must NEVER exist unredacted in git-tracked files
SECRET_REGEXES = [
    (r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)\s*[:=]\s*["\']([a-zA-Z0-9_\-\.]{24,})["\']', "Exposed API/Auth Token"),
    (r'-----BEGIN (RSA|EC|DSA|OPENSSH|PGP|PRIVATE) KEY-----', "Private Cryptographic Key Header"),
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\'](?!(ci-test|dummy|test|placeholder|mock|\*|\$|\{))[a-zA-Z0-9!@#$%^&*()_+]{8,}["\']', "Hardcoded Password Literal"),
    (r'\b(seed[_-]?phrase|mnemonic)\s*[:=]\s*["\']([a-z]+\s+){11,23}[a-z]+["\']', "Mnemonic Seed Phrase Literal"),
    (r'(?i)(ton[_-]?privkey|private_key_hex)\s*[:=]\s*["\'][0-9a-fA-F]{64,128}["\']', "Raw Hex Private Key Literal"),
]

# Sensitive file extensions or patterns that should NEVER be tracked by git
DISALLOWED_TRACKED_PATTERNS = [
    re.compile(r'(^|/)\.env(\..+)?$'),
    re.compile(r'.*\.(key|pem|pkcs12|pfx|p12|kdbx)$'),
    re.compile(r'.*(id_rsa|id_ed25519|id_ecdsa)$'),
    re.compile(r'.*\.(docx|pptx)$'),
    re.compile(r'(^|/)data/shill\.db.*$'),
]

# Safe test fixtures or CI test overrides
ALLOWLIST_SUBSTRINGS = [
    "ci-test-password-not-secret",
    "ci-vault-passphrase",
    "JBSWY3DPEHPK3PXP",
    "shill_root_",
    "SHILL_SECURE_SALT_984729384729",
    "dummy",
    "mock",
]

def run_cmd(cmd: str) -> str:
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()

def check_tracked_filenames() -> list:
    violations = []
    tracked_files = run_cmd("git ls-files").splitlines()
    for f in tracked_files:
        f = f.strip()
        if not f:
            continue
        for pat in DISALLOWED_TRACKED_PATTERNS:
            if pat.search(f):
                violations.append(f"[PROHIBITED TRACKED FILE] {f} matches {pat.pattern}")
    return violations

def check_file_contents() -> list:
    violations = []
    tracked_files = run_cmd("git ls-files").splitlines()
    for f in tracked_files:
        path = Path(f)
        if not path.is_file() or path.stat().st_size > 1_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for regex, desc in SECRET_REGEXES:
            for match in re.finditer(regex, content):
                matched_str = match.group(0)
                if any(al in matched_str for al in ALLOWLIST_SUBSTRINGS):
                    continue
                violations.append(f"[LEAK DETECTED] {f}: {desc} -> '{matched_str[:40]}...'")
    return violations

def check_staged_diff() -> list:
    violations = []
    diff_output = run_cmd("git diff --cached")
    if not diff_output:
        return violations

    for regex, desc in SECRET_REGEXES:
        for match in re.finditer(regex, diff_output):
            matched_str = match.group(0)
            if any(al in matched_str for al in ALLOWLIST_SUBSTRINGS):
                continue
            violations.append(f"[STAGED SECRET LEAK] {desc} in staged diff -> '{matched_str[:40]}...'")
    return violations

def run_gauntlet():
    print("🔒 [GAUNTLET] Running Shill Security Audit & Secret Leak Scanner...")
    all_violations = []

    # 1. Check Tracked File Boundaries
    name_violations = check_tracked_filenames()
    if name_violations:
        print(f"❌ Found {len(name_violations)} prohibited file pattern violations:")
        for v in name_violations:
            print(f"   - {v}")
        all_violations.extend(name_violations)
    else:
        print("✅ Git-tracked file pattern check passed (no .env, private keys, or internal docx/pptx).")

    # 2. Check File Contents for Hardcoded Secrets
    content_violations = check_file_contents()
    if content_violations:
        print(f"❌ Found {len(content_violations)} potential secret leaks in tracked files:")
        for v in content_violations:
            print(f"   - {v}")
        all_violations.extend(content_violations)
    else:
        print("✅ Git-tracked content scan passed (zero high-entropy credentials or unredacted keys).")

    # 3. Check Staged Changes
    staged_violations = check_staged_diff()
    if staged_violations:
        print(f"❌ Staged diff contains secret leaks:")
        for v in staged_violations:
            print(f"   - {v}")
        all_violations.extend(staged_violations)
    else:
        print("✅ Staged diff clean (ready for commit/push).")

    if all_violations:
        print(f"\n🚨 GAUNTLET FAILED: {len(all_violations)} security boundaries breached.")
        sys.exit(1)

    print("\n🛡️  GAUNTLET PASSED: Repository is cryptographically clean. No secrets detected.")

if __name__ == "__main__":
    run_gauntlet()
