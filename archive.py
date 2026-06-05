#!/usr/bin/env python3
"""Archive pass: fill missing Wayback snapshots on ledger entries.

Runs AFTER collect.py. Idempotent (only touches entries whose archive_url is
still null) and rate-paced (Wayback SPN2 limit ~15/min). It edits only the
mutable, non-hashed archive_url field, so the hash-chain stays valid — verify.py
still passes. A backlog drains over successive runs (cap via ARCHIVE_MAX).
"""
from __future__ import annotations

import os
import sys
import time

from lib import ledger, wayback

ROOT = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(ROOT, "ledger", "log.jsonl")
MAX = int(os.environ.get("ARCHIVE_MAX", "50"))       # snapshots per run
PACE = float(os.environ.get("ARCHIVE_PACE", "4"))    # seconds between saves (~15/min)


def main() -> int:
    if not wayback.configured():
        print("archive: IA keys not set (env or keys/ia.env) — skipping")
        return 0
    entries = ledger.load(LEDGER_PATH)
    todo = [e for e in entries if not e.get("archive_url") and e.get("record", {}).get("url")]
    print(f"archive: {len(todo)} entries missing snapshots; doing up to {MAX}")
    done = 0
    for e in todo[:MAX]:
        snap = wayback.save(e["record"]["url"])
        if snap:
            e["archive_url"] = snap
            done += 1
            print(f"  seq {e['seq']}: {snap[:90]}")
        else:
            print(f"  seq {e['seq']}: save not accepted (will retry next run)")
        time.sleep(PACE)
    if done:
        ledger.rewrite(LEDGER_PATH, entries)
    print(f"archive: filled {done} snapshot(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
