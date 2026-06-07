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

from dataclasses import dataclass
import os
from datetime import datetime, timezone
from typing import Any

import requests

UA = "Mozilla/5.0 (zerkalo-svodok/0.1; transparency archive)"
TIMEOUT = 30
_KEYS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "keys", "ia.env")


@dataclass(frozen=True)
class SaveResult:
    """Outcome of one Save Page Now request, with operator-readable diagnostics."""

    ok: bool
    archive_url: str | None = None
    reason: str = ""
    http_status: int | None = None
    status: str | None = None
    status_ext: str | None = None
    job_id: str | None = None
    error: str | None = None
    body_excerpt: str | None = None

    def summary(self) -> str:
        parts = []
        if self.reason:
            parts.append(self.reason)
        if self.http_status is not None:
            parts.append(f"http={self.http_status}")
        if self.status:
            parts.append(f"status={self.status}")
        if self.status_ext:
            parts.append(f"status_ext={self.status_ext}")
        if self.job_id:
            parts.append(f"job_id={self.job_id}")
        if self.error:
            parts.append(f"error={self.error}")
        if self.body_excerpt:
            parts.append(f"body={self.body_excerpt}")
        return "; ".join(parts) if parts else "no details"


def _excerpt(value: Any, limit: int = 300) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\n", " ").strip()
    if not text:
        return None
    return text[:limit] + ("…" if len(text) > limit else "")


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


def save(url: str) -> SaveResult:
    """Fire an SPN2 save and return a resolvable Wayback URL, plus diagnostics."""
    ak, sk = keys()
    if not (ak and sk):
        return SaveResult(ok=False, reason="not-configured")

    headers = {"Authorization": f"LOW {ak}:{sk}", "Accept": "application/json", "User-Agent": UA}
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    try:
        r = requests.post("https://web.archive.org/save", headers=headers, data={"url": url}, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return SaveResult(ok=False, reason="request-exception", error=repr(exc))

    body: dict[str, Any] | None = None
    body_excerpt: str | None = None
    try:
        body = r.json()
        diagnostic = body.get("message") or body.get("status_ext") or body.get("status") or body
        body_excerpt = _excerpt(diagnostic)
    except ValueError:
        body_excerpt = _excerpt(r.text)

    if not r.ok:
        status = body.get("status") if body else None
        status_ext = body.get("status_ext") if body else None
        return SaveResult(
            ok=False,
            reason="http-error",
            http_status=r.status_code,
            status=status,
            status_ext=status_ext,
            body_excerpt=body_excerpt,
        )

    body = body or {}
    job_id = body.get("job_id")
    status = body.get("status")
    status_ext = body.get("status_ext")

    if job_id:
        return SaveResult(
            ok=True,
            archive_url=f"https://web.archive.org/web/{ts}/{url}",
            reason="accepted",
            http_status=r.status_code,
            status=status,
            status_ext=status_ext,
            job_id=job_id,
            body_excerpt=body_excerpt,
        )

    if status == "error" and "too-many" in (status_ext or ""):
        # Wayback says the URL already has enough captures today. Link to the
        # nearest capture for this date and stop burning quota on this entry.
        return SaveResult(
            ok=True,
            archive_url=f"https://web.archive.org/web/{ts[:8]}/{url}",
            reason="already-captured-today",
            http_status=r.status_code,
            status=status,
            status_ext=status_ext,
            body_excerpt=body_excerpt,
        )

    return SaveResult(
        ok=False,
        reason="not-accepted",
        http_status=r.status_code,
        status=status,
        status_ext=status_ext,
        body_excerpt=body_excerpt,
    )
