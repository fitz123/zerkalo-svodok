"""Record schema + canonical hashing for the Зеркало-сводок transparency log.

A *record* captures ONE published claim/report about a war event. We store
metadata + a content hash + an external archive link — NOT the full source
text. That keeps the repo a tamper-evident *index* of what was said (and
sidesteps copyright/takedown): the bulky original lives in Wayback/WARC.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

# Fields that define a record's identity. Order-independent: we hash canonical JSON.
RECORD_FIELDS = (
    "source_id",     # stable id from sources.yaml, e.g. "ru_official_ria"
    "voice",         # logical voice: "ru_official" | "ua_official" | "independent"
    "source_name",   # human label, e.g. "RIA Novosti (relaying RU MoD)"
    "basket",        # narrative | territory | equipment | casualties_named | civilian | event
    "author",        # attributed author / outlet
    "title",         # short claim title / headline
    "url",           # original public URL
    "published_at",  # source's own timestamp (ISO 8601 UTC), if any
    "event_date",    # date of the event being claimed about (YYYY-MM-DD)
    "content_hash",  # sha256 of the fetched original content (proves what was said)
)
# NOTE: archive_url (Wayback snapshot) is deliberately NOT part of a record's
# identity hash. It is mutable provenance filled asynchronously by archive.py
# AFTER the record is committed, so a slow external save never blocks/locks the
# claim. The integrity proof of *what was said* is content_hash, not the link.


def canonical(obj: Any) -> bytes:
    """Deterministic JSON bytes — sorted keys, no whitespace. The thing we hash."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(raw: bytes) -> str:
    """Hash of the raw fetched source content (the proof of 'what was said')."""
    return sha256_hex(raw)


def make_record(**fields: Any) -> dict:
    """Build a record holding only the defined fields (missing -> None)."""
    return {k: fields.get(k) for k in RECORD_FIELDS}


def record_id(record: dict) -> str:
    """Identity of a record = sha256 of its canonical form (defined fields only)."""
    core = {k: record.get(k) for k in RECORD_FIELDS}
    return sha256_hex(canonical(core))
