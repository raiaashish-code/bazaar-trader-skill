#!/usr/bin/env python3
"""Price alerts and the NSE clock. IST. Opening bell is 09:15."""

import argparse
import datetime
import json
import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.india_clock import CLOSE, OPEN, parse_hhmm, parse_now, to_ist, trading_day  # noqa: E402
from lib.io_util import read_json, write_json


class AlertError(Exception):
    pass


def clock_status(now_utc):
    local = to_ist(now_utc)
    d, t = local.date(), local.time()
    ok, why = trading_day(d)
    if not ok:
        return {"open": False, "reason": why, "local": local.isoformat(), "clock": "IST"}
    is_open = OPEN <= t < CLOSE
    return {"open": is_open, "opens": "09:15", "closes": "15:30", "local": local.strftime("%H:%M"),
            "clock": "IST", "reason": None if is_open else ("pre-open" if t < OPEN else "after-close")}


def eval_rule(rule, quotes, now_ist, fired):
    rid = rule.get("id") or rule.get("label")
    if rid in fired:
        return None
    kind = rule.get("type") or rule.get("kind")
    if rule.get("date") and rule["date"] != now_ist.date().isoformat():
        return None
    if kind == "opening_bell":
        ok, _ = trading_day(now_ist.date())
        if ok and now_ist.time() >= OPEN:
            return {"id": rid, "type": kind, "message": "NSE opening bell 09:15 IST"}
        return None
    if kind == "time":
        at = parse_hhmm(rule["at"])
        ok, _ = trading_day(now_ist.date())
        if ok and now_ist.time() >= at:
            return {"id": rid, "type": kind, "message": "%s (%s IST)" % (rule.get("label") or "time", rule["at"])}
        return None
    sym = str(rule.get("symbol") or "").upper()
    q = quotes.get(sym)
    if q is None:
        return None
    px = float(q)
    if kind in ("above", "target") and px >= float(rule["price"]):
        return {"id": rid, "type": kind, "message": "%s at Rs %.2f, at/above Rs %.2f" % (sym, px, float(rule["price"]))}
    if kind in ("below", "stop") and px <= float(rule["price"]):
        return {"id": rid, "type": kind, "message": "%s at Rs %.2f, at/below Rs %.2f" % (sym, px, float(rule["price"]))}
    if kind == "pct_move":
        ref = float(rule.get("ref") or 0)
        if ref <= 0:
            return None
        move = (px / ref - 1) * 100
        need = float(rule["pct"])
        direction = rule.get("direction") or "up"
        if direction == "up" and move >= need:
            return {"id": rid, "type": kind, "message": "%s +%.2f%%" % (sym, move)}
        if direction == "down" and move <= -need:
            return {"id": rid, "type": kind, "message": "%s %.2f%%" % (sym, move)}
    return None


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    cl = sub.add_parser("clock")
    cl.add_argument("--now")
    ad = sub.add_parser("add")
    ad.add_argument("--file", default="trader/alerts.json")
    ad.add_argument("--from-plan")
    ad.add_argument("--symbol")
    ad.add_argument("--stop", type=float)
    ad.add_argument("--target", type=float)
    ad.add_argument("--at")
    ad.add_argument("--label")
    ad.add_argument("--opening-bell", action="store_true")
    ch = sub.add_parser("check")
    ch.add_argument("--file", default="trader/alerts.json")
    ch.add_argument("--quotes")
    ch.add_argument("--now")
    ls = sub.add_parser("list")
    ls.add_argument("--file", default="trader/alerts.json")
    a = p.parse_args(argv)
    if a.cmd == "clock":
        print(json.dumps(clock_status(parse_now(a.now)), indent=2))
        return 0
    path = getattr(a, "file", "trader/alerts.json")
    doc = read_json(path, "alerts", required=False) or {"rules": [], "fired": []}
    if a.cmd == "list":
        for r in doc["rules"]:
            print("%s  %s" % (r.get("id"), r))
        return 0
    if a.cmd == "add":
        if a.from_plan:
            plan = json.load(open(a.from_plan, encoding="utf-8"))
            sym = plan["symbol"]
            day = plan.get("date")
            doc["rules"].append({"id": "%s-stop" % sym.lower(), "type": "stop", "symbol": sym,
                                 "price": plan["stop"], "date": day})
            doc["rules"].append({"id": "%s-target" % sym.lower(), "type": "target", "symbol": sym,
                                 "price": plan["target"], "date": day})
            doc["rules"].append({"id": "%s-flat" % sym.lower(), "type": "time", "at": plan.get("flat_by") or "15:15",
                                 "label": "flat by close", "date": day})
        elif a.opening_bell:
            doc["rules"].append({"id": "nse-open", "type": "opening_bell"})
        elif a.at:
            doc["rules"].append({"id": str(uuid.uuid4())[:8], "type": "time", "at": a.at, "label": a.label})
        elif a.symbol and a.stop:
            doc["rules"].append({"id": "%s-stop" % a.symbol.lower(), "type": "stop", "symbol": a.symbol.upper(),
                                 "price": a.stop})
        elif a.symbol and a.target:
            doc["rules"].append({"id": "%s-target" % a.symbol.lower(), "type": "target", "symbol": a.symbol.upper(),
                                 "price": a.target})
        else:
            print("error: nothing to add", file=sys.stderr)
            return 1
        write_json(path, doc)
        print("alerts: %d rules" % len(doc["rules"]))
        return 0
    quotes = {}
    if a.quotes:
        quotes = json.load(open(a.quotes, encoding="utf-8"))
    now_ist = to_ist(parse_now(a.now))
    fired = set(doc.get("fired") or [])
    hits = []
    for rule in doc["rules"]:
        hit = eval_rule(rule, quotes, now_ist, fired)
        if hit:
            hits.append(hit)
            fired.add(hit["id"])
    doc["fired"] = sorted(fired)
    write_json(path, doc)
    if not hits:
        print("no alerts")
        return 1
    for h in hits:
        print("ALERT %s: %s" % (h["id"], h["message"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
