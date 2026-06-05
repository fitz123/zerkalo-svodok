"""Wayback Machine (Save Page Now v2) archiving — non-blocking.

SPN2 saving is asynchronous and can take minutes. We do NOT block on it: we fire
the save and return a deterministic timestamp-redirect URL. Wayback resolves
/web/{ts}/{url} to the capture nearest {ts} — i.e. the one we just triggered,
once it finishes rendering. The capture's content is independently anchored by
the record's own content_hash; this link is just the durable, readable copy.

Keys: IA_ACCESS_KEY / IA_SECRET_KEY (archive.org/account/s3.php), from the
environment or the gitignored keys/ia.env file.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import requests

UA = "Mozilla/5.0 (zerkalo-svodok/0.1; transparency archive)"
TIMEOUT = 30
_KEYS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "keys", "ia.env")


def keys() -> tuple[str | None, str | None]:
    ak, sk = os.environ.get("IA_ACCESS_KEY"), os.environ.get("IA_SECRET_KEY")
    if ak and sk:
        return ak, sk
    if os.path.exists(_KEYS_FILE):
        vals = {}
        for line in open(_KEYS_FILE, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
        return vals.get("IA_ACCESS_KEY"), vals.get("IA_SECRET_KEY")
    return None, None


def configured() -> bool:
    ak, sk = keys()
    return bool(ak and sk)


def save(url: str) -> str | None:
    """Fire an SPN2 save (non-blocking) and return a resolvable Wayback URL, or None."""
    ak, sk = keys()
    if not (ak and sk):
        return None
    headers = {"Authorization": f"LOW {ak}:{sk}", "Accept": "application/json", "User-Agent": UA}
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    try:
        r = requests.post("https://web.archive.org/save", headers=headers, data={"url": url}, timeout=TIMEOUT)
        if not r.ok:
            return None
        body = r.json()
        if body.get("job_id"):
            return f"https://web.archive.org/web/{ts}/{url}"        # accepted; resolves once captured
        if body.get("status") == "error" and "too-many" in body.get("status_ext", ""):
            return f"https://web.archive.org/web/{ts[:8]}/{url}"    # captures already exist today
        return None
    except (requests.RequestException, ValueError):
        return None
