#!/usr/bin/env python3
"""Render the ledger into human-readable static pages.

  index.html   — flat, newest-first list of every claim (who said what + links).
  events.html  — grouped BY DAY, voices side by side (RU official | UA official |
                 independent), so divergence between sources is visible at a glance.

Grouping is by event_date (day granularity). True per-incident clustering (same
place/event across sources) needs matching logic and is a later step. Pure stdlib;
output is static, hostable anywhere. Run after collect/archive.
"""
from __future__ import annotations

import html
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

from lib import ledger

ROOT = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(ROOT, "ledger", "log.jsonl")

VOICES = [("ru_official", "РФ · офиц.", "ru"), ("ua_official", "UA · офиц.", "ua"), ("independent", "независимый", "ind")]
VOICE_LABEL = {k: (lbl, cls) for k, lbl, cls in VOICES}
PER_VOICE_CAP = 40  # max items per voice per day in the grouped view

CSS = """
:root{color-scheme:light dark}
body{font:15px/1.5 system-ui,sans-serif;margin:0;padding:1.2rem;max-width:1200px;margin:auto}
h1{font-size:1.4rem;margin:.2rem 0}
.sub{color:#888;font-size:.9rem;margin-bottom:.6rem}
nav{margin:.4rem 0 1rem}nav a{margin-right:1rem}
.note{background:#0001;border-left:3px solid #888;padding:.6rem .9rem;border-radius:4px;font-size:.9rem;margin:1rem 0}
table{border-collapse:collapse;width:100%;font-size:.93rem}
th,td{text-align:left;padding:.45rem .5rem;border-bottom:1px solid #8883;vertical-align:top}
th{position:sticky;top:0;background:Canvas;font-size:.8rem;text-transform:uppercase;letter-spacing:.03em;color:#888}
.tag{display:inline-block;padding:.05rem .45rem;border-radius:999px;font-size:.78rem;white-space:nowrap;color:#fff}
.ru{background:#d33a}.ua{background:#2a6ad3aa}.ind{background:#2a8a4aaa}
a{color:#2a6ad3;text-decoration:none}a:hover{text-decoration:underline}
.pending{color:#aa8}.snap{font-size:.82rem;color:#888;margin-left:.3rem}
.hash{font-family:ui-monospace,monospace;color:#999;font-size:.8rem}
.day{margin:1.4rem 0;border-top:2px solid #8884;padding-top:.6rem}
.day h2{font-size:1.1rem;margin:.2rem 0 .6rem}
.cols{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem}
@media(max-width:800px){.cols{grid-template-columns:1fr}}
.col h3{margin:.2rem 0 .5rem;font-size:.85rem}
.item{padding:.3rem 0;border-bottom:1px solid #8882;font-size:.9rem}
.muted{color:#999;font-size:.85rem}
"""


def _orig(r: dict) -> str:
    title = html.escape(r.get("title") or "(без заголовка)")
    url = html.escape(r.get("url") or "", quote=True)
    return f'<a href="{url}" target="_blank" rel="noopener">{title}</a>' if url else title


def _snap(entry: dict) -> str:
    s = entry.get("archive_url")
    if s:
        return f'<a class="snap" href="{html.escape(s, quote=True)}" target="_blank" rel="noopener">снимок ↗</a>'
    return '<span class="snap pending">снимок ожидает</span>'


def _page(title: str, sub: str, body: str) -> str:
    return (f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head><body>'
            f'<h1>Зеркало сводок</h1><div class="sub">{sub}</div>'
            f'<nav><a href="index.html">Список</a><a href="events.html">По событиям</a></nav>'
            f'<div class="note"><b>Что это.</b> Архив фиксирует, <b>кто что заявил и когда</b> — '
            f'официальные стороны и независимые источники. Он <b>не выносит вердикт об истине</b>: '
            f'ставит заявления рядом и не даёт переписать их задним числом. Целостность проверяет '
            f'<code>verify.py</code> (цепочка + подпись + Bitcoin-якорь).</div>{body}</body></html>')


def render_flat(entries: list[dict]) -> str:
    rows = []
    for x in entries:
        r = x["record"]
        lbl, cls = VOICE_LABEL.get(r.get("voice"), (r.get("voice") or "", "ind"))
        rows.append(
            f"<tr><td>{html.escape(r.get('event_date') or '')}</td>"
            f"<td><span class='tag {cls}'>{html.escape(lbl)}</span></td>"
            f"<td>{html.escape(r.get('source_name') or '')}</td><td>{_orig(r)}</td>"
            f"<td>{_snap(x)}</td><td class='hash'>{html.escape((x.get('record_id') or '')[:12])}…</td></tr>"
        )
    return ("<table><thead><tr><th>Дата</th><th>Голос</th><th>Источник</th><th>Заявление</th>"
            "<th>Снимок</th><th>Хеш</th></tr></thead><tbody>" + "\n".join(rows) + "</tbody></table>")


def render_events(entries: list[dict]) -> str:
    by_day: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for x in entries:
        by_day[x["record"].get("event_date") or "—"][x["record"].get("voice") or "independent"].append(x)
    blocks = []
    for day in sorted(by_day, reverse=True):
        cols = []
        for vkey, lbl, cls in VOICES:
            items = by_day[day].get(vkey, [])
            shown = items[:PER_VOICE_CAP]
            lis = "".join(f'<div class="item">{_orig(x["record"])} {_snap(x)}</div>' for x in shown)
            more = f'<div class="muted">+{len(items) - len(shown)} ещё</div>' if len(items) > len(shown) else ""
            empty = '<div class="muted">—</div>' if not items else ""
            cols.append(f'<div class="col"><h3><span class="tag {cls}">{html.escape(lbl)}</span> '
                        f'<span class="muted">{len(items)}</span></h3>{lis}{more}{empty}</div>')
        blocks.append(f'<section class="day"><h2>{html.escape(day)}</h2><div class="cols">{"".join(cols)}</div></section>')
    return "".join(blocks)


def main() -> int:
    entries = ledger.load(LEDGER_PATH)
    flat = sorted(entries, key=lambda x: (x["record"].get("event_date") or "", x["seq"]), reverse=True)
    head = ledger.head(entries)[:16] if entries else "—"
    archived = sum(1 for x in entries if x.get("archive_url"))
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sub = (f'Заверенный архив заявлений о войне · {len(entries)} записей · {archived} со снимком · '
           f'голова <span class="hash">{head}…</span> · обновлено {gen}')
    # CI produces only the flat index.html (cheap, deterministic). The event-card
    # view (events.html) needs the AI clustering/enrichment step and is built
    # separately (render_events_enriched.py), so CI must NOT clobber it here.
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(_page("Зеркало сводок — список", sub, render_flat(flat)))
    days = len({x["record"].get("event_date") for x in entries})
    print(f"wrote index.html — {len(entries)} records, {days} days, {archived} snapshots")
    return 0


if __name__ == "__main__":
    sys.exit(main())
