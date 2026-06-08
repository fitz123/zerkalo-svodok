# Зеркало сводок — tamper-evident war-summary mirror

A public, automatically-collected, **tamper-evident** archive of what official
sides and independent observers *said* about the same war events — pinned with
timestamps so later rewriting ("переобувание") is caught.

> **What this is NOT.** It does not decide who is telling the truth. It records
> **claims** — who said what, when — and makes those claims permanent and
> attributable. Verdicts stay human.

## Scope

Narrow scope by design: the system collects only sources worth both recording in
the ledger **and** freezing in Wayback. No collect-only agency relays.

Current sources:

- **RU official:** Минобороны России Telegram (`mod_russia`).
- **UA official:** Генштаб ЗСУ Telegram (`GeneralStaffZSU`).
- **Independent / civilian harm:** Bellingcat Civilian Harm TimeMap JSON.
- **Independent / territory:** DeepStateMAP history JSON.

Removed from the active system: RIA, TASS, Ukrinform, WarSpotting, ACLED. They
can be reconsidered later only as an explicit scope decision.

## Why it can be trusted without trusting us

- **Hash-chained log.** Every entry commits to the previous one. Any later edit,
  reorder or deletion breaks the chain and `verify.py` flags it.
- **Signed head.** The current head is signed by the operator's published key.
- **OpenTimestamps.** The head is anchored in Bitcoin — so even *we* cannot
  backdate the log. (`не верь даже нам — проверь`.)
- **Hash + link, not full text.** The repo stores a content **hash**, metadata
  and an external archive link (Wayback) — not the republished article. It is a
  tamper-evident *index* of what was said.

## Layout

```
sources.yaml            # narrow source scope: collect == archive set
collect.py              # Telegram/JSON sources -> records -> append new ones to ledger
archive.py              # paced Wayback backfill for the same narrow source set
sign.py                 # keygen | sign the head (+ OpenTimestamps)
verify.py               # anyone runs this: chain + signature + timestamp
render.py               # build human-readable index.html (who said what + links)
index.html              # browsable view (original + frozen-snapshot links)
lib/record.py           # record schema + canonical hashing
lib/ledger.py           # append-only hash-chained log
lib/wayback.py          # Save-Page-Now archiving with diagnostics/backoff
ledger/log.jsonl        # the log (one entry per line)
ledger/head.json|.sig   # signed current head
keys/pubkey.hex         # operator public key (private key = GH Actions secret)
.github/workflows/      # scheduled collect -> archive -> sign -> verify -> render -> commit
```

## Record = one claim

Hashed identity fields: `source_id, voice, source_name, basket, author, title,
url, published_at, event_date, content_hash`. `archive_url` is deliberately
mutable/non-hashed: Wayback can be filled later without changing what claim was
recorded.

## Run it

```
pip install -r requirements.txt
python3 sign.py keygen          # once: writes keys/pubkey.hex + keys/privkey.hex (gitignored)
python3 collect.py              # fetch + append new records
python3 archive.py              # fill Wayback snapshots (needs IA keys)
python3 sign.py sign            # sign the head (SIGNING_KEY_HEX env or keys/privkey.hex)
python3 verify.py               # verify chain (+ signature + timestamp)
python3 render.py               # rebuild index.html
```

## Automation

`.github/workflows/collect.yml` currently runs collection, Wayback archive pass,
signing, verification, render, and commit. Wayback is limited/backed off in code
so Archive.org failures do not corrupt the ledger.

Secrets:

- `SIGNING_KEY_HEX` — required in CI to sign the head.
- `IA_ACCESS_KEY` / `IA_SECRET_KEY` — optional Wayback Save Page Now keys.

## Honest limits

Signing proves **integrity** (not altered since signed), not truth-at-entry. A
single source can still lie; that is why the archive records opposing official
voices plus independent datasets and makes divergence permanent.

Licensing/attribution: honor each source's terms. DeepStateMAP is non-commercial
with attribution/no API proxying. Named-casualty datasets are PII — ingest
aggregates, not named records.
