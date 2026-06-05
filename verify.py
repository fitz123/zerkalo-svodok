#!/usr/bin/env python3
"""Standalone verifier — anyone can run this; it trusts no one.

Checks, in order:
  1. Hash-chain integrity — every entry links to the previous; nothing was
     altered, reordered or removed. (Pure standard library.)
  2. Signature on the current head against the published public key
     (keys/pubkey.hex), if a signature is present. (Needs `cryptography`.)
  3. OpenTimestamps proof on the head (ledger/head.json.ots), if present —
     proves the head existed by a past time, anchored in Bitcoin, so even the
     operator cannot have backdated it. (Needs the `ots` CLI.)

Usage:  python3 verify.py
Exit 0 = everything that could be checked passed; 1 = a real failure.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

from lib import ledger
from lib.record import canonical

ROOT = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(ROOT, "ledger", "log.jsonl")
PUBKEY_PATH = os.path.join(ROOT, "keys", "pubkey.hex")
HEAD_JSON = os.path.join(ROOT, "ledger", "head.json")
HEAD_SIG = os.path.join(ROOT, "ledger", "head.sig")


def check_chain() -> bool:
    entries = ledger.load(LEDGER_PATH)
    problems = ledger.verify_chain(entries)
    if problems:
        print(f"[FAIL] chain: {len(problems)} problem(s):")
        for p in problems:
            print("   - " + p)
        return False
    print(f"[ OK ] chain intact — {len(entries)} entries, head {ledger.head(entries)[:16]}…")
    return True


def check_signature() -> bool | None:
    """True/False if checked; None if there's nothing to check."""
    if not (os.path.exists(HEAD_JSON) and os.path.exists(HEAD_SIG) and os.path.exists(PUBKEY_PATH)):
        print("[skip] signature: no head.json / head.sig / pubkey.hex yet")
        return None
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        print("[skip] signature: `cryptography` not installed")
        return None

    pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(open(PUBKEY_PATH).read().strip()))
    payload = open(HEAD_JSON, "rb").read()
    sig = bytes.fromhex(open(HEAD_SIG).read().strip())

    # The signed head must match the head recomputed from the chain.
    import json
    signed_head = json.loads(payload).get("head")
    actual_head = ledger.head(ledger.load(LEDGER_PATH))
    if signed_head != actual_head:
        print(f"[FAIL] signature: signed head != chain head ({signed_head[:16]}… vs {actual_head[:16]}…)")
        return False
    try:
        pub.verify(sig, payload)
    except InvalidSignature:
        print("[FAIL] signature: INVALID — head not signed by the published key")
        return False
    print("[ OK ] signature valid — head signed by the published key")
    return True


def check_ots() -> bool | None:
    ots_file = HEAD_JSON + ".ots"
    if not os.path.exists(ots_file):
        print("[skip] opentimestamps: no head.json.ots yet")
        return None
    if not shutil.which("ots"):
        print("[skip] opentimestamps: `ots` CLI not installed")
        return None
    res = subprocess.run(["ots", "verify", ots_file], capture_output=True, text=True)
    out = (res.stdout + res.stderr).lower()
    # Check "pending" FIRST: a fresh stamp says "Pending confirmation in Bitcoin
    # blockchain" — which must NOT be mistaken for a confirmed anchor.
    if "pending" in out or "could not be confirmed" in out or "no attestation" in out:
        print("[info] opentimestamps: stamp created, awaiting Bitcoin confirmation (~hours) — not a failure")
        return None
    if "success" in out or "attests existence" in out:
        print("[ OK ] opentimestamps: head anchored in Bitcoin (confirmed)")
        return True
    print("[FAIL] opentimestamps: verification failed")
    return False


def main() -> int:
    results = [check_chain(), check_signature(), check_ots()]
    if any(r is False for r in results):
        print("\nRESULT: FAILED — see [FAIL] lines above.")
        return 1
    print("\nRESULT: OK — everything that could be checked passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
