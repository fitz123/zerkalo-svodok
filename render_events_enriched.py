#!/usr/bin/env python3
"""Render enriched event cards (events-enriched.json): for each two-sided event,
show РФ official / UA official / Independent sources side by side, with each
independent source's stance and a final independent summary. Pure stdlib.
"""
from __future__ import annotations

import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "events-enriched.json")
OUT = os.path.join(ROOT, "events.html")

SUPPORT = {
    "ru": ("подтверждает РФ", "s-ru"), "ua": ("подтверждает UA", "s-ua"),
    "neither": ("нейтрально", "s-n"), "unclear": ("неясно", "s-n"), "both": ("обе стороны", "s-b"),
}

CSS = """
:root{color-scheme:light dark}
body{font:15px/1.55 system-ui,sans-serif;margin:0;padding:1.2rem;max-width:980px;margin:auto}
h1{font-size:1.4rem;margin:.2rem 0}.sub{color:#888;font-size:.9rem;margin-bottom:.6rem}
.note{background:#0001;border-left:3px solid #888;padding:.6rem .9rem;border-radius:4px;font-size:.9rem;margin:1rem 0}
.event{border:1px solid #8884;border-radius:10px;padding:.9rem 1.1rem;margin:1rem 0}
.evh{font-weight:600;font-size:1.08rem;margin-bottom:.6rem}.evdate{color:#999;font-weight:400;font-size:.85rem;margin-left:.4rem}
.grp{margin:.5rem 0}.grp h4{margin:.3rem 0;font-size:.8rem;text-transform:uppercase;letter-spacing:.03em}
.h-ru{color:#d35}.h-ua{color:#37c}.h-ind{color:#2a8a4a}
.claim{padding:.22rem 0;font-size:.92rem;border-top:1px solid #8881}
.src{color:#888;font-size:.82rem}
a{color:#2a6ad3;text-decoration:none}a:hover{text-decoration:underline}
.says{color:#bbb;font-size:.88rem;display:block;margin:.1rem 0 .1rem .2rem}
.b{display:inline-block;padding:.03rem .4rem;border-radius:999px;font-size:.72rem;color:#fff;margin-left:.3rem}
.s-ru{background:#d35}.s-ua{background:#37c}.s-n{background:#888}.s-b{background:#85a}
.verdict{background:#2a8a4a14;border-left:3px solid #2a8a4a;padding:.5rem .8rem;border-radius:4px;font-size:.88rem;margin-top:.6rem}
"""


def _claims(items, cls):
    out = []
    for c in items:
        title = html.escape(c.get("title") or "")
        url = html.escape(c.get("url") or "", quote=True)
        link = f'<a href="{url}" target="_blank" rel="noopener">{title}</a>' if url else title
        out.append(f'<div class="claim">{link} <span class="src">· {html.escape(c.get("source") or "")}</span></div>')
    return "".join(out) or '<div class="claim src">—</div>'


def _independents(items):
    out = []
    for c in items:
        url = html.escape(c.get("url") or "", quote=True)
        src = html.escape(c.get("source") or "")
        srclink = f'<a href="{url}" target="_blank" rel="noopener">{src}</a>' if url else src
        lbl, cls = SUPPORT.get(c.get("supports"), ("неясно", "s-n"))
        out.append(f'<div class="claim">{srclink}<span class="b {cls}">{lbl}</span>'
                   f'<span class="says">{html.escape(c.get("says") or "")}</span></div>')
    return "".join(out) or '<div class="claim src">независимых данных не найдено</div>'


def main() -> int:
    data = json.load(open(DATA, encoding="utf-8"))
    events = data.get("events", [])
    cards = []
    for e in events:
        verdict = html.escape(e.get("note") or "")
        cards.append(
            f'<div class="event"><div class="evh">{html.escape(e.get("name") or "")}'
            f'<span class="evdate">{html.escape(e.get("date") or "")}</span></div>'
            f'<div class="grp"><h4 class="h-ru">🇷🇺 РФ официальная</h4>{_claims(e.get("ru", []), "ru")}</div>'
            f'<div class="grp"><h4 class="h-ua">🇺🇦 UA официальная</h4>{_claims(e.get("ua", []), "ua")}</div>'
            f'<div class="grp"><h4 class="h-ind">🔎 Независимые</h4>{_independents(e.get("independents", []))}</div>'
            + (f'<div class="verdict"><b>Независимый итог:</b> {verdict}</div>' if verdict else "")
            + '</div>'
        )
    doc = (f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>Зеркало сводок — события со всех сторон</title><style>{CSS}</style></head><body>'
           f'<h1>Зеркало сводок — события со всех сторон</h1>'
           f'<div class="sub">{len(events)} событий · официальные обе стороны + независимая проверка</div>'
           f'<div class="note"><b>Как читать.</b> Для каждого события — что заявила каждая сторона и что нашли '
           f'<b>независимые источники</b> (WarSpotting, ISW, агентства, спутник). Метка у независимого показывает, '
           f'чью версию он поддерживает. «Независимый итог» — честная сводка: что подтверждено, а что нет. '
           f'Система не выносит вердикт — она кладёт всё рядом и заверяет.</div>'
           f'{"".join(cards)}</body></html>')
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {OUT} — {len(events)} enriched events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
