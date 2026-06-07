#!/usr/bin/env python3
"""Archive pass: fill missing Wayback snapshots on selected ledger entries.

Runs independently from collection. Idempotent (only touches entries whose
archive_url is still null) and rate-paced (Wayback SPN2 limit ~15/min). It edits
only the mutable, non-hashed archive_url field, so the hash-chain stays valid —
verify.py still passes.

Wayback policy is an allow-list: only sources with `archive: true` in
sources.yaml are snapshotted. Other sources remain collected and hash-chained,
but do not burn Wayback quota.
"""
from __future__ import annotations

import os
import sys
import time

import yaml

from lib import ledger, wayback

ROOT = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(ROOT, "ledger", "log.jsonl")
SOURCES_PATH = os.path.join(ROOT, "sources.yaml")
MAX = int(os.environ.get("ARCHIVE_MAX", "50"))       # snapshots per run
PACE = float(os.environ.get("ARCHIVE_PACE", "5"))    # seconds between saves (~12/min, safe vs SPN2 ~15/min)


def _archivable_sources() -> set[str]:
    """source_ids explicitly marked `archive: true` in sources.yaml."""
    with open(SOURCES_PATH, encoding="utf-8") as f:
        srcs = yaml.safe_load(f)["sources"]
    return {s["id"] for s in srcs if s.get("archive") is True}


def _missing_snapshot(e: dict) -> bool:
    return bool(not e.get("archive_url") and e.get("record", {}).get("url"))


def main() -> int:
    if not wayback.configured():
        print("archive: IA keys not set (env or keys/ia.env) — skipping")
        return 0

    allow = _archivable_sources()
    if not allow:
        print("archive: no sources marked archive: true in sources.yaml — nothing to do")
        return 0

    entries = ledger.load(LEDGER_PATH)
    missing = [e for e in entries if _missing_snapshot(e)]
    todo = [e for e in missing if e["record"].get("source_id") in allow]
    skipped = len(missing) - len(todo)

    print(f"archive: allow-list sources: {', '.join(sorted(allow))}")
    print(f"archive: {len(todo)} allowed entries missing snapshots; {skipped} non-archivable missing entries skipped; doing up to {MAX}")

    done = 0
    failed = 0
    for e in todo[:MAX]:
        r = e["record"]
        result = wayback.save(r["url"])
        label = f"seq {e['seq']} {r.get('source_id')}"
        if result.ok and result.archive_url:
            e["archive_url"] = result.archive_url
            done += 1
            print(f"  {label}: archived -> {result.archive_url[:100]} ({result.summary()})")
        else:
            failed += 1
            print(f"  {label}: not archived ({result.summary()})")
        time.sleep(PACE)

    if done:
        ledger.rewrite(LEDGER_PATH, entries)
    print(f"archive: filled {done} snapshot(s); {failed} attempt(s) not accepted/failed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
