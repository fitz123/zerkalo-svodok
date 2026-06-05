#!/usr/bin/env python3
"""Render AI-clustered events (events-clustered.json) into event cards.

Each card = a named event + the claims of each side covering it. Events where
more than one side reports are highlighted (that is the divergence the archive
exists to surface). Pure stdlib. The clustering itself is produced by an AI step
(see events-clustered.json); this only renders it.
"""
from __future__ import annotations

import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "events-clustered.json")
OUT = os.path.join(ROOT, "events.html")

VOICE = {"ru_official": ("РФ · офиц.", "ru"), "ua_official": ("UA · офиц.", "ua"), "independent": ("независимый", "ind")}

CSS = """
:root{color-scheme:light dark}
body{font:15px/1.55 system-ui,sans-serif;margin:0;padding:1.2rem;max-width:900px;margin:auto}
h1{font-size:1.4rem;margin:.2rem 0}.sub{color:#888;font-size:.9rem;margin-bottom:.6rem}
nav a{margin-right:1rem}.note{background:#0001;border-left:3px solid #888;padding:.6rem .9rem;border-radius:4px;font-size:.9rem;margin:1rem 0}
.event{border:1px solid #8884;border-radius:8px;padding:.8rem 1rem;margin:.9rem 0}
.event.multi{border-color:#d33a;border-width:2px;background:#d3300a}
.evh{font-weight:600;font-size:1.05rem;margin-bottom:.5rem}
.evdate{color:#999;font-weight:400;font-size:.85rem;margin-left:.4rem}
.badge{background:#d33;color:#fff;font-size:.72rem;padding:.05rem .45rem;border-radius:999px;margin-left:.5rem}
.side{display:flex;gap:.5rem;align-items:baseline;padding:.3rem 0;border-top:1px solid #8882}
.tag{flex:none;display:inline-block;padding:.05rem .45rem;border-radius:999px;font-size:.75rem;color:#fff}
.ru{background:#d33a}.ua{background:#2a6ad3aa}.ind{background:#2a8a4aaa}
a{color:#2a6ad3;text-decoration:none}a:hover{text-decoration:underline}
.snap{font-size:.8rem;color:#888;margin-left:.3rem}.pending{color:#aa8}
"""


def main() -> int:
    data = json.load(open(DATA, encoding="utf-8"))
    events = data.get("events", [])
    multi = sum(1 for e in events if e.get("multi"))
    cards = []
    for e in events:
        sides = []
        for s in e.get("sides", []):
            lbl, cls = VOICE.get(s.get("voice"), (s.get("voice") or "", "ind"))
            title = html.escape(s.get("title") or "")
            url = html.escape(s.get("url") or "", quote=True)
            link = f'<a href="{url}" target="_blank" rel="noopener">{title}</a>' if url else title
            snap = s.get("snap")
            snaplink = (f'<a class="snap" href="{html.escape(snap, quote=True)}" target="_blank">снимок ↗</a>'
                        if snap else '<span class="snap pending">снимок ожидает</span>')
            sides.append(f'<div class="side"><span class="tag {cls}">{html.escape(lbl)}</span>'
                         f'<span>{link} <span class="snap">· {html.escape(s.get("source") or "")}</span> {snaplink}</span></div>')
        badge = '<span class="badge">2 стороны</span>' if e.get("multi") else ""
        cards.append(f'<div class="event {"multi" if e.get("multi") else ""}">'
                     f'<div class="evh">{html.escape(e.get("name") or "")}'
                     f'<span class="evdate">{html.escape(e.get("date") or "")}</span>{badge}</div>'
                     f'{"".join(sides)}</div>')
    body = (f'<div class="note"><b>Карточки событий.</b> Каждая — одно событие и что заявила о нём '
            f'каждая сторона. Красным выделены события, которые освещают <b>несколько сторон</b> — '
            f'там видно расхождение версий. Кластеризация сделана ИИ-шагом; из ленты отброшено '
            f'<b>{data.get("dropped_non_war", 0)}</b> невоенных сообщений. Демо на {data.get("method","")}.'
            f'</div>{"".join(cards)}')
    doc = (f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>Зеркало сводок — по событиям</title><style>{CSS}</style></head><body>'
           f'<h1>Зеркало сводок — по событиям</h1>'
           f'<div class="sub">{len(events)} событий · {multi} с несколькими сторонами</div>'
           f'<nav><a href="index.html">Список</a><a href="events.html">По событиям</a></nav>'
           f'{body}</body></html>')
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {OUT} — {len(events)} events, {multi} multi-side")
    return 0


if __name__ == "__main__":
    sys.exit(main())
