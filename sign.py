#!/usr/bin/env python3
"""Sign the current ledger head (and optionally timestamp it).

The head (last entry_hash) summarises the whole chain. Signing it with the
operator key lets anyone confirm the published head is ours; OpenTimestamps
then anchors that head in Bitcoin so even WE cannot backdate it later.

Subcommands:
  keygen   Generate an Ed25519 keypair. Prints the PRIVATE key hex (store it as
           a GitHub Actions secret SIGNING_KEY_HEX — never commit it) and writes
           the PUBLIC key to keys/pubkey.hex (commit this).
  sign     Compute the head, write ledger/head.json, sign it with SIGNING_KEY_HEX
           (env), write ledger/head.sig, then `ots stamp` head.json if available.

Requires the `cryptography` package. OpenTimestamps is optional (`ots` CLI).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from lib import ledger
from lib.record import canonical

ROOT = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(ROOT, "ledger", "log.jsonl")
PUBKEY_PATH = os.path.join(ROOT, "keys", "pubkey.hex")
PRIVKEY_PATH = os.path.join(ROOT, "keys", "privkey.hex")  # gitignored (privkey*) — local use only
HEAD_JSON = os.path.join(ROOT, "ledger", "head.json")
HEAD_SIG = os.path.join(ROOT, "ledger", "head.sig")


def _load_crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
        return Ed25519PrivateKey, Ed25519PublicKey
    except ImportError:
        sys.exit("error: `cryptography` not installed (pip install cryptography)")


def keygen() -> None:
    Ed25519PrivateKey, _ = _load_crypto()
    from cryptography.hazmat.primitives import serialization

    priv = Ed25519PrivateKey.generate()
    priv_raw = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    os.makedirs(os.path.dirname(PUBKEY_PATH), exist_ok=True)
    with open(PUBKEY_PATH, "w") as f:
        f.write(pub_raw.hex() + "\n")
    # Write the PRIVATE key to a gitignored file — never to stdout (transcripts/logs).
    fd = os.open(PRIVKEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(priv_raw.hex() + "\n")
    print("PUBLIC key  -> keys/pubkey.hex (commit this):")
    print("  " + pub_raw.hex())
    print()
    print("PRIVATE key -> keys/privkey.hex (gitignored, mode 600). NOT printed here.")
    print("For production: copy it into the GitHub Actions secret SIGNING_KEY_HEX, then delete the file:")
    print("  cat keys/privkey.hex   # paste into the secret")
    print("  rm keys/privkey.hex")


def sign() -> None:
    Ed25519PrivateKey, _ = _load_crypto()
    key_hex = os.environ.get("SIGNING_KEY_HEX")
    if not key_hex and os.path.exists(PRIVKEY_PATH):
        key_hex = open(PRIVKEY_PATH).read()  # local fallback (gitignored)
    if not key_hex:
        sys.exit("error: no key — set SIGNING_KEY_HEX or run `sign.py keygen` first")
    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_hex.strip()))

    entries = ledger.load(LEDGER_PATH)
    head_doc = {
        "head": ledger.head(entries),
        "seq": len(entries) - 1 if entries else -1,
        "count": len(entries),
        "signed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    payload = canonical(head_doc)
    with open(HEAD_JSON, "wb") as f:
        f.write(payload)
    sig = priv.sign(payload)
    with open(HEAD_SIG, "w") as f:
        f.write(sig.hex() + "\n")
    print(f"signed head {head_doc['head'][:16]}… ({head_doc['count']} entries)")

    # Optional: anchor head.json in Bitcoin via OpenTimestamps, if the CLI is present.
    if shutil.which("ots"):
        ots_path = HEAD_JSON + ".ots"
        # The head changed every run; a stale .ots is invalid AND `ots stamp` refuses
        # to overwrite it ("File exists"). Drop it so we always stamp the current head.
        if os.path.exists(ots_path):
            os.remove(ots_path)
        try:
            subprocess.run(["ots", "stamp", HEAD_JSON], check=True)
            print("opentimestamps: head.json.ots created")
        except subprocess.CalledProcessError as e:
            print(f"opentimestamps: stamp failed ({e}) — non-fatal")
    else:
        print("opentimestamps: `ots` not found — skipping (install opentimestamps-client to anchor)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "keygen":
        keygen()
    elif cmd == "sign":
        sign()
    else:
        sys.exit("usage: sign.py {keygen|sign}")
