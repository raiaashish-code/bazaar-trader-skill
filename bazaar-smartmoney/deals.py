#!/usr/bin/env python3
"""Smart-money tracker. NSE bulk/block deals and FII-DII cash, not US Congress PTR.

Pelosi / House Clerk filings do not apply to NSE names. The Indian stand-in is:

  bulk     NSE bulk deals (0.5%+ of equity in one session)
  block    NSE block deals (windowed large tickets)
  fii-dii  NSE FII/DII cash provisional (empty stays empty; this tool does not invent OI)

    python3 deals.py bulk --offline bulk.csv
    python3 deals.py block --offline block.csv --symbol RELIANCE
    python3 deals.py fii-dii --offline fii.json
    python3 deals.py new --offline bulk.csv --state trader/state/smartmoney.json
"""

import argparse
import csv
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.io_util import read_json, rupees, write_json  # noqa: E402


class DealError(Exception):
    pass


def _f(x):
    try:
        return float(str(x).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def parse_deals(text, kind="bulk"):
    """NSE bulk/block CSV. Headers vary; we accept Date, Symbol, Client Name, Buy/Sell, Quantity, Price, Remarks."""
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise DealError("empty deals file")
    rows = []
    for item in reader:
        lower = {k.strip().lower(): v for k, v in item.items() if k}
        sym = (lower.get("symbol") or lower.get("security") or "").strip().upper()
        if not sym:
            continue
        side = (lower.get("buy/sell") or lower.get("trade") or lower.get("side") or "").strip().upper()
        if side.startswith("B"):
            side = "BUY"
        elif side.startswith("S"):
            side = "SELL"
        qty = _f(lower.get("quantity") or lower.get("qty") or lower.get("shares"))
        px = _f(lower.get("trade price") or lower.get("price") or lower.get("wap"))
        client = (lower.get("client name") or lower.get("client") or "").strip()
        day = (lower.get("date") or lower.get("deal date") or "").strip()
        rows.append({"kind": kind, "date": day, "symbol": sym, "side": side, "qty": qty,
                     "price": px, "value": round(qty * px, 2), "client": client,
                     "remarks": (lower.get("remarks") or "").strip()})
    return rows


def parse_fii_dii(doc):
    """Keep FII/DII cash. Empty stays empty. Never invents a figure."""
    if isinstance(doc, str):
        doc = json.loads(doc)
    rows = doc.get("data") if isinstance(doc, dict) else doc
    out = []
    for row in rows or []:
        cat = row.get("category") or row.get("cat") or ""
        buy = row.get("buyValue")
        sell = row.get("sellValue")
        net = row.get("netValue")
        if buy is None and sell is None and net is None:
            continue
        out.append({"date": row.get("date"), "category": cat, "buy": buy, "sell": sell, "net": net,
                    "source": row.get("source") or "nse_fii_dii"})
    return out


def select(rows, symbol=None, since=None, side=None):
    out = []
    for r in rows:
        if symbol and r.get("symbol") != symbol.upper():
            continue
        if since and str(r.get("date")) < since:
            continue
        if side and r.get("side") != side.upper():
            continue
        out.append(r)
    return out


def new_since(rows, state):
    seen = set(state.get("seen") or [])
    fresh = []
    for r in rows:
        key = "|".join(str(r.get(k) or "") for k in ("kind", "date", "symbol", "side", "qty", "client"))
        r["id"] = key
        if key not in seen:
            fresh.append(r)
    return fresh


def describe(row):
    if "category" in row and "symbol" not in row:
        net = row.get("net")
        return "%s %s  net %s" % (row.get("date"), row.get("category"), rupees(net or 0))
    return "%s %s %s %s @ %s  %s  %s" % (
        row.get("date"), row.get("symbol"), row.get("side"), int(row.get("qty") or 0),
        rupees(row.get("price") or 0), rupees(row.get("value") or 0), row.get("client"))


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["bulk", "block", "fii-dii", "new"])
    p.add_argument("--offline", required=True)
    p.add_argument("--symbol")
    p.add_argument("--since")
    p.add_argument("--state", default="trader/state/smartmoney.json")
    p.add_argument("--watchlist", default="trader/watchlist.json")
    p.add_argument("--write", default="trader/smartmoney.json")
    a = p.parse_args(argv)
    try:
        raw = open(a.offline, encoding="utf-8").read()
        if a.cmd == "fii-dii":
            rows = parse_fii_dii(raw)
        else:
            kind = "block" if a.cmd == "block" else "bulk"
            rows = parse_deals(raw, kind=kind)
            rows = select(rows, symbol=a.symbol, since=a.since)
            if a.cmd == "new":
                state = read_json(a.state, "smartmoney", required=False) or {}
                rows = new_since(rows, state)
                seen = list(state.get("seen") or [])
                seen.extend(r["id"] for r in rows)
                write_json(a.state, {"seen": seen})
        watch = set()
        wl = read_json(a.watchlist, "watchlist", required=False) or {}
        for h in wl.get("hits") or []:
            watch.add(str(h["symbol"]).upper())
        for r in rows:
            r["on_watch"] = r.get("symbol") in watch
        write_json(a.write, {"cmd": a.cmd, "rows": rows, "note": "Not a copy-trade list. Bulk/block is lagged public tape."})
        print("%s: %d rows" % (a.cmd, len(rows)))
        for r in rows[:25]:
            flag = " WATCH" if r.get("on_watch") else ""
            print("  %s%s" % (describe(r), flag))
        return 0 if rows else 1
    except DealError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
