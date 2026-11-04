#!/usr/bin/env python3
"""News monitor. NSE corporate announcements instead of SEC 8-K. IST times."""

import argparse
import datetime as _dt
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.india_clock import parse_now, to_ist  # noqa: E402
from lib.io_util import read_json, write_json

KEYWORDS = [
    ("earnings", r"result|earnings|profit|q[1-4]\b|quarter"),
    ("dividend", r"dividend|interim dividend|record date"),
    ("deal", r"acquisition|merger|nclt|open offer|stake sale"),
    ("block", r"bulk deal|block deal|preferential"),
    ("regulatory", r"sebi|nclat|ed search|raid|penalty"),
    ("guidance", r"guidance|outlook|downgrade|upgrade"),
    ("board", r"board meeting|outcome of board"),
]


class NewsError(Exception):
    pass


def watch_from_files(portfolio="trader/portfolio.json", watchlist="trader/watchlist.json"):
    watch = {}
    wl = read_json(watchlist, "watchlist", required=False) or {}
    for h in wl.get("hits") or []:
        watch[str(h["symbol"]).upper()] = h.get("name") or h["symbol"]
    pf = read_json(portfolio, "portfolio", required=False) or {}
    for p in pf.get("positions") or []:
        t = str(p.get("ticker") or p.get("symbol") or "").upper()
        if t:
            watch[t] = p.get("name") or t
    return watch


def parse_rss(data, ticker):
    root = ET.fromstring(data)
    items = []
    for it in root.findall(".//item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate") or it.findtext("pubdate") or ""
        items.append({"id": link or title, "ticker": ticker, "title": title, "link": link,
                      "summary": (it.findtext("description") or "")[:400], "kind": "headline",
                      "source": "rss", "pub": pub})
    return items


def parse_nse_announcements(data, ticker):
    """NSE corporate-announcements JSON list or {data: [...]}."""
    doc = json.loads(data) if isinstance(data, str) else data
    rows = doc.get("data") if isinstance(doc, dict) else doc
    items = []
    for row in rows or []:
        sym = str(row.get("symbol") or row.get("sm_name") or ticker).upper()
        title = row.get("desc") or row.get("subject") or row.get("headline") or ""
        when = row.get("an_dt") or row.get("datetime") or row.get("date") or ""
        items.append({"id": "%s|%s|%s" % (sym, when, title), "ticker": sym, "title": title,
                      "link": row.get("attchmntFile") or row.get("url") or "",
                      "summary": row.get("attchmntText") or "", "kind": "filing",
                      "source": "nse_announcement", "pub": when,
                      "category": row.get("desc") or row.get("subject")})
    return items


def parse_time(value, now_ist):
    if not value:
        return now_ist
    value = str(value).strip()
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                "%d-%m-%Y %H:%M:%S"):
        try:
            return _dt.datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    return now_ist


def tag(items, watch):
    for it in items:
        hay = "%s %s" % (it["title"], it.get("summary") or "")
        it["touches"] = sorted({it["ticker"]} & set(watch) | (
            {t for t in watch if t in hay.upper()}))
        it["tags"] = [label for label, rx in KEYWORDS if re.search(rx, hay, re.I)]
    return items


def select(items, state, now, hours=48, show_all=False):
    seen = state.setdefault("seen", {})
    cutoff = now - _dt.timedelta(hours=hours)
    out = []
    for it in items:
        t = it.get("time") or now
        if t < cutoff or t > now + _dt.timedelta(minutes=10):
            continue
        fp = it["id"]
        it["new"] = fp not in seen
        if show_all or it["new"]:
            out.append(it)
    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--offline")
    p.add_argument("--watchlist", default="trader/watchlist.json")
    p.add_argument("--now")
    p.add_argument("--hours", type=int, default=48)
    p.add_argument("--json", action="store_true")
    p.add_argument("--write", default="trader/news.json")
    a = p.parse_args(argv)
    watch = watch_from_files(watchlist=a.watchlist)
    now = to_ist(parse_now(a.now))
    items = []
    if a.offline:
        raw = open(a.offline, encoding="utf-8").read()
        if a.offline.endswith(".xml"):
            ticker = next(iter(watch), "WATCH")
            items = parse_rss(raw, ticker)
        else:
            ticker = next(iter(watch), "WATCH")
            items = parse_nse_announcements(raw, ticker)
    for it in items:
        it["time"] = parse_time(it.get("pub"), now)
    items = tag(items, watch)
    state = read_json("trader/state/news.json", "news state", required=False) or {}
    chosen = select(items, state, now, hours=a.hours, show_all=True)
    doc = {"as_of": now.isoformat(), "clock": "IST", "watch": sorted(watch),
           "items": [{"title": it["title"], "ticker": it["ticker"], "tags": it.get("tags"),
                      "kind": it["kind"], "source": it["source"],
                      "time": it["time"].isoformat()} for it in chosen]}
    write_json(a.write, doc)
    if a.json:
        print(json.dumps(doc, indent=2))
    else:
        print("%d items for %s (IST)" % (len(chosen), ",".join(sorted(watch)) or "empty watch"))
        for it in chosen[:20]:
            print("  [%s] %s  %s" % (",".join(it.get("tags") or ["-"]), it["ticker"], it["title"][:90]))
    return 0 if chosen else 1


if __name__ == "__main__":
    sys.exit(main())
