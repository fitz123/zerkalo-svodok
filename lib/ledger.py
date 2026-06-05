"""Append-only, hash-chained ledger.

Each entry commits to the previous entry's hash, so any later edit, reorder or
removal breaks the chain and is detectable by anyone — no trust in the operator
required. The current head (last entry_hash) is what we sign and timestamp
externally (OpenTimestamps), which also defeats a wholesale rewrite.

Storage: JSONL at ledger/log.jsonl — one entry per line, append-only.
"""
from __future__ import annotations

import json
import os

from .record import canonical, record_id, sha256_hex

GENESIS_PREV = "0" * 64


def _entry_hash(seq: int, rid: str, prev: str, captured_at: str) -> str:
    core = {"seq": seq, "record_id": rid, "prev": prev, "captured_at": captured_at}
    return sha256_hex(canonical(core))


def load(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def head(entries: list[dict]) -> str:
    return entries[-1]["entry_hash"] if entries else GENESIS_PREV


def existing_record_ids(entries: list[dict]) -> set[str]:
    return {e["record_id"] for e in entries}


def append(path: str, record: dict, captured_at: str) -> dict:
    """Append one record as a new chained entry; return the entry."""
    entries = load(path)
    seq = len(entries)
    prev = head(entries)
    rid = record_id(record)
    entry = {
        "seq": seq,
        "captured_at": captured_at,
        "record_id": rid,
        "prev": prev,
        "entry_hash": _entry_hash(seq, rid, prev, captured_at),
        "record": record,
        "archive_url": None,  # mutable provenance, NOT hashed — filled by archive.py
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def rewrite(path: str, entries: list[dict]) -> None:
    """Overwrite the whole log (used to fill mutable archive_url fields).

    Safe ONLY for non-hashed fields like archive_url — the chain (record_id,
    entry_hash, prev) must be left byte-identical or verify_chain will fail.
    """
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def verify_chain(entries: list[dict]) -> list[str]:
    """Return a list of problems; an empty list means the chain is intact."""
    problems = []
    prev = GENESIS_PREV
    for i, e in enumerate(entries):
        if e.get("seq") != i:
            problems.append(f"entry {i}: seq mismatch (got {e.get('seq')})")
        if e.get("prev") != prev:
            problems.append(f"entry {i}: prev-link broken (chain cut or reordered)")
        if record_id(e.get("record", {})) != e.get("record_id"):
            problems.append(f"entry {i}: record_id mismatch (the record was altered)")
        if _entry_hash(e.get("seq"), e.get("record_id"), e.get("prev"), e.get("captured_at")) != e.get("entry_hash"):
            problems.append(f"entry {i}: entry_hash mismatch (the entry was altered)")
        prev = e.get("entry_hash")
    return problems
