#!/usr/bin/env python3
"""Collector: read sources.yaml, fetch each enabled source, build records and
append NEW ones to the ledger. Idempotent — a record already present (same
record_id) is skipped, so the scheduled job can run as often as you like.

Narrow scope by design:
  Telegram sources -> one record per public post.
  JSON sources     -> one record per run = a snapshot hash of the dataset state.

We store a content HASH + metadata + (optional) external archive link, never
the full source text. Wayback archiving lives in archive.py and uses the same
small source set; there are no collect-only feeds.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import requests
import yaml

from lib import ledger
from lib.record import content_hash, make_record, record_id

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCES_PATH = os.path.join(ROOT, "sources.yaml")
LEDGER_PATH = os.path.join(ROOT, "ledger", "log.jsonl")

UA = "Mozilla/5.0 (zerkalo-svodok/0.1; transparency archive)"
TIMEOUT = 30


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# Archiving lives in archive.py (a separate, idempotent, rate-paced pass), so a
# slow Wayback save never blocks collection or locks a record.


def collect_json(src: dict, existing: set[str]) -> list[dict]:
    try:
        r = requests.get(src["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as ex:
        print(f"  skip {src['id']}: fetch failed ({ex})")
        return []
    rec = make_record(
        source_id=src["id"],
        voice=src["voice"],
        source_name=src["name"],
        basket=src.get("basket", "event"),
        author=src.get("author", src["name"]),
        title=f"{src['name']} snapshot {today()}",
        url=src["url"],
        published_at=now_iso(),
        event_date=today(),
        content_hash=content_hash(r.content),
    )
    if record_id(rec) in existing:  # identical snapshot already recorded -> skip
        return []
    return [rec]


def collect_telegram(src: dict, existing: set[str]) -> list[dict]:
    from lib import telegram  # lazy import

    out = []
    for post in telegram.fetch(src["channel"]):
        dt = post.get("datetime")
        text = post["text"]
        rec = make_record(
            source_id=src["id"],
            voice=src["voice"],
            source_name=src["name"],
            basket=src.get("basket", "narrative"),
            author=src.get("author", src["name"]),
            title=text[:300],
            url=post["url"],
            published_at=dt,
            event_date=(dt or today())[:10],
            content_hash=content_hash(text.encode("utf-8")),
        )
        if record_id(rec) in existing:
            continue
        out.append(rec)
    return out


def main() -> int:
    with open(SOURCES_PATH, encoding="utf-8") as f:
        sources = yaml.safe_load(f)["sources"]

    captured_at = now_iso()
    existing = ledger.existing_record_ids(ledger.load(LEDGER_PATH))
    added = 0
    for src in sources:
        if not src.get("enabled", False):
            continue
        method = src.get("method")
        print(f"-> {src['id']} ({method})")
        try:
            if method == "json":
                recs = collect_json(src, existing)
            elif method == "telegram":
                recs = collect_telegram(src, existing)
            else:
                print(f"  skip: unknown or unsupported method {method}")
                continue
        except Exception as ex:  # fail-loud per source, never abort the whole run
            print(f"  ERROR {src['id']}: {ex}")
            continue
        for rec in recs:
            ledger.append(LEDGER_PATH, rec, captured_at)
            existing.add(record_id(rec))
            added += 1
        print(f"  +{len(recs)} new")
    print(f"done: {added} new records appended.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
