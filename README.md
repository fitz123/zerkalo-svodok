# Зеркало сводок — tamper-evident war-summary mirror

A public, automatically-collected, **tamper-evident** archive of what official
sides and independent observers *said* about the same war events — pinned with
timestamps so later rewriting ("переобувание") is caught.

> **What this is NOT.** It does not decide who is telling the truth. It records
> **claims** — who said what, when — and makes those claims permanent and
> attributable. The reader sees the official figure and the independent reports
> side by side, and sees where they diverge. Verdicts stay human.

## Why it can be trusted without trusting us

- **Hash-chained log.** Every entry commits to the previous one. Any later edit,
  reorder or deletion breaks the chain and `verify.py` flags it.
- **Signed head.** The current head is signed by the operator's published key.
- **OpenTimestamps.** The head is anchored in Bitcoin — so even *we* cannot
  backdate the log. (`не верь даже нам — проверь`.)
- **Hash + link, not full text.** The repo stores a content **hash**, metadata
  and an external archive link (Wayback) — not the republished article. It is a
  tamper-evident *index* of what was said. This sidesteps copyright/takedown and
  keeps the whole thing portable: it is just signed files + a public key, so it
  can move to any host (your own site, IPFS) and still verify.

## Layout

```
sources.yaml            # the sources (official RU/UA via RSS, independents via JSON)
collect.py              # fetch sources -> build records -> append new ones to the ledger (fast)
archive.py              # idempotent, paced pass: fill Wayback snapshots (mutable archive_url)
sign.py                 # keygen | sign the head (+ OpenTimestamps)
verify.py               # anyone runs this: chain + signature + timestamp
render.py               # build human-readable index.html (who said what + links)
index.html              # the browsable view (original + frozen-snapshot links)
lib/record.py           # record schema + canonical hashing
lib/ledger.py           # append-only hash-chained log
lib/wayback.py          # non-blocking Save-Page-Now archiving
ledger/log.jsonl        # the log (one entry per line, append-only)
ledger/head.json|.sig   # signed current head
keys/pubkey.hex         # operator public key (private key = GH Actions secret)
.github/workflows/      # scheduled collect -> sign -> verify -> commit
```

## Record = one claim

Hashed identity fields: `source_id, voice, source_name, basket, author, title,
url, published_at, event_date, content_hash`. (`archive_url` is a separate,
mutable, non-hashed field on the ledger entry — see "Run it".)
`voice` ∈ {`ru_official`, `ua_official`, `independent`}; official side = one
voice even if it has several feeds. `basket` groups by method (narrative /
territory / equipment / casualties_named / civilian / event) so divergence
across independent baskets is visible.

## Run it

```
pip install -r requirements.txt
python3 sign.py keygen          # once: writes keys/pubkey.hex + keys/privkey.hex (gitignored)
python3 collect.py              # fetch + append new records (fast, no blocking)
python3 archive.py              # fill Wayback snapshots (idempotent, paced; needs IA keys)
python3 sign.py sign            # sign the head (SIGNING_KEY_HEX env or keys/privkey.hex)
python3 verify.py               # verify chain (+ signature + timestamp)
```

Archiving is decoupled from collection: `archive.py` fills the **mutable,
non-hashed** `archive_url` on each entry, so a slow Wayback save never blocks
collection or locks a record. It is idempotent (only touches null snapshots) and
rate-paced (SPN2 ~15/min); a backlog drains over successive runs. Editing
`archive_url` does not affect `record_id`/`entry_hash`, so `verify.py` stays green.
IA keys come from env (`IA_ACCESS_KEY`/`IA_SECRET_KEY`) or the gitignored `keys/ia.env`.

Automated: `.github/workflows/collect.yml` runs collect → sign → verify → commit
on a schedule. Secrets used (all optional except the signing key):
`SIGNING_KEY_HEX` (required to sign), `IA_ACCESS_KEY`/`IA_SECRET_KEY` (Wayback),
`ACLED_KEY`/`ACLED_EMAIL` (ACLED).

## Status — Phase 1 skeleton

Working now: hash-chained ledger, signing, standalone verifier, RSS + JSON
collectors, GitHub Actions workflow. Honest TODOs:

- **Enabled by default** (verified, no auth): RIA RSS, TASS RSS, Ukrinform RSS,
  Bellingcat TimeMap JSON.
- **`enabled: false` pending confirmation:** DeepStateMAP exact endpoint,
  WarSpotting data endpoint, ACLED (needs free token + current auth flow).
- RSS gives the state **agency's relay**, not the ministry verbatim — attributed
  as such. Ministry-verbatim Telegram channels are a Phase 1.5 add-on.
- Wayback archiving is on only if IA keys are set.

## Honest limits

Signing proves **integrity** (not altered since signed), not truth-at-entry. A
single source can still lie; that is why we record official **and** independent
voices and make their divergence permanent. Independence/anti-collusion of
sources and volunteer contributors are later phases.

Licensing/attribution: honor each source's terms (DeepStateMAP non-commercial /
no API proxying, ACLED EULA, WarSpotting credit). Named-casualty datasets are
PII — ingest aggregates, not named records.
