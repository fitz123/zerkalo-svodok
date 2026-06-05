"""Read a PUBLIC Telegram channel via its web preview — no account, no MTProto.

`https://t.me/s/<channel>` is a plain server-rendered HTML page of the latest
posts. We parse each post's text, permalink and timestamp. This is the
credential-free way to ingest official military summaries (МО РФ @mod_russia,
Генштаб ЗСУ @GeneralStaffZSU). Brittle only to Telegram changing its HTML.
"""
from __future__ import annotations

import html
import re

import requests

UA = "Mozilla/5.0 (zerkalo-svodok/0.1; transparency archive)"
TIMEOUT = 30

_TEXT = re.compile(r'tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
_TIME = re.compile(r'<time[^>]*datetime="([^"]+)"')


def _clean(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"</p>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return html.unescape(re.sub(r"[ \t]+", " ", fragment)).strip()


def fetch(channel: str) -> list[dict]:
    """Return recent posts: [{url, text, datetime}] (newest last), or []."""
    r = requests.get(f"https://t.me/s/{channel}", headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    posts = []
    # Each post block begins with data-post="<channel>/<id>".
    for chunk in r.text.split('data-post="')[1:]:
        mid = chunk.split('"', 1)[0]                 # e.g. "mod_russia/40123"
        tm = _TEXT.search(chunk)
        if not tm:
            continue
        text = _clean(tm.group(1))
        if len(text) < 30:
            continue
        dt = _TIME.search(chunk)
        posts.append({
            "url": f"https://t.me/{mid}",
            "text": text,
            "datetime": dt.group(1) if dt else None,
        })
    return posts
