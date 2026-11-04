#!/usr/bin/env python3
"""Entry timer. First completed IST bar that closes beyond the level, not a forming bar."""

import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.india_clock import (  # noqa: E402
    CLOSE, OPEN, NO_ENTRIES_AFTER, NO_ENTRIES_BEFORE, clock_label, parse_hhmm,
    parse_now, session, to_ist, trading_day,
)
from lib.io_util import write_json

INTERVALS = {"5m": 300, "1m": 60}


class EntryError(Exception):
    pass


def r2(x):
    return None if x is None else round(float(x), 2)


def evaluate(chart, now_utc, setup="orb", or_minutes=15, interval="5m", level=None, cfg=None):
    cfg = cfg or {}
    step = INTERVALS[interval]
    n_or = or_minutes * 60 // step
    local = to_ist(now_utc)
    day = local.date()
    res = {"symbol": chart["symbol"], "setup": setup, "side": "buy", "date": day.isoformat(),
           "interval": interval, "or_minutes": or_minutes, "now": local.strftime("%Y-%m-%d %H:%M:%S"),
           "status": "waiting", "phase": "", "reason": "", "opening_range": None, "level": None,
           "trigger": None, "clock": "IST", "honest": "fill is the next print after this bar closes"}
    ok, why = trading_day(day)
    if not ok:
        res.update(status="no-data", phase="closed", reason="NSE is closed today (%s)" % why)
        return res
    o, c = session(day)
    open_dt = datetime.datetime.combine(day, o)
    close_dt = datetime.datetime.combine(day, c)
    before = datetime.datetime.combine(day, parse_hhmm(cfg.get("no_entries_before", "09:45")))
    cutoff = datetime.datetime.combine(day, parse_hhmm(cfg.get("no_entries_after", "14:30")))
    or_end = open_dt + datetime.timedelta(minutes=or_minutes)

    by_slot = {}
    for b in chart["bars"]:
        et = datetime.datetime.combine(day, datetime.time.fromisoformat(b["t"])) if isinstance(b["t"], str) and len(b["t"]) <= 8 else None
        if et is None and isinstance(b.get("et"), str):
            et = datetime.datetime.fromisoformat(b["et"])
        if et is None:
            continue
        if not (open_dt <= et < close_dt):
            continue
        slot = int((et - open_dt).total_seconds()) // step
        by_slot[slot] = dict(b, et=et, end=et + datetime.timedelta(seconds=step), slot=slot)

    bars = []
    now_ts = local
    for slot in sorted(by_slot):
        b = by_slot[slot]
        if b["end"] <= now_ts:
            bars.append(b)
        elif b["et"] <= local:
            res["forming"] = {"bar_start": clock_label(b["et"]), "closes": clock_label(b["end"]), "price": r2(b["c"])}

    if local < open_dt:
        res.update(phase="pre-open", reason="NSE opens at 09:15 IST")
        return res

    or_bars = [b for b in bars if b["slot"] < n_or]
    if or_bars:
        res["opening_range"] = {"high": r2(max(b["h"] for b in or_bars)), "low": r2(min(b["l"] for b in or_bars)),
                                "minutes": or_minutes, "bars": len(or_bars), "of": n_or,
                                "complete": local >= or_end}
    if setup == "orb":
        if local < or_end:
            res.update(phase="forming", reason="%d of %d range bars closed; the range is set at %s" % (
                len(or_bars), n_or, clock_label(or_end)))
            return res
        if not or_bars:
            res.update(status="no-data", phase="open", reason="no bars for the opening range")
            return res
        lvl = max(b["h"] for b in or_bars)
    else:
        if level is None:
            raise EntryError("level setup needs --level")
        lvl = float(level)
    res["level"] = r2(lvl)

    first_slot = n_or if setup == "orb" else 0
    trig = None
    for b in bars:
        if b["slot"] < first_slot or b["end"] < before or b["end"] > cutoff:
            continue
        if b["c"] > lvl:
            trig = b
            break
    last = bars[-1] if bars else None
    if trig:
        res.update(status="triggered", phase="open" if local < close_dt else "after-close",
                   reason="the %s bar closed above the range high" % clock_label(trig["et"]))
        res["trigger"] = {"time": clock_label(trig["end"]), "bar_start": clock_label(trig["et"]),
                          "bar_index": trig["slot"], "price": r2(trig["c"]),
                          "pct_over": r2(100.0 * (trig["c"] / lvl - 1)),
                          "honest_note": "honest fill is the first print after %s, not this bar's close" % clock_label(trig["end"])}
        return res
    if not bars:
        res.update(status="no-data", phase="open", reason="no bars yet")
        return res
    if local >= cutoff:
        res.update(status="expired", phase="after-cutoff",
                   reason="no close above Rs %.2f by %s" % (lvl, clock_label(cutoff)))
        return res
    gap = lvl - last["c"]
    res.update(phase="open", reason="last close Rs %.2f (%s bar), Rs %.2f %s the level" % (
        last["c"], clock_label(last["et"]), abs(gap), "under" if gap >= 0 else "over"))
    return res


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("symbol")
    p.add_argument("--offline", required=True)
    p.add_argument("--now")
    p.add_argument("--setup", default="orb")
    p.add_argument("--or-minutes", type=int, default=15)
    p.add_argument("--level", type=float)
    p.add_argument("--json", action="store_true")
    p.add_argument("--write", default="trader/entry.json")
    a = p.parse_args(argv)
    try:
        chart = json.load(open(a.offline, encoding="utf-8"))
        if "symbol" not in chart:
            chart["symbol"] = a.symbol.upper()
        res = evaluate(chart, parse_now(a.now), setup=a.setup, or_minutes=a.or_minutes, level=a.level)
        write_json(a.write, res)
        if a.json:
            print(json.dumps(res, indent=2, default=str))
        else:
            print("%s %s IST: %s. %s" % (res["symbol"], res["now"], res["status"], res["reason"]))
            if res.get("trigger"):
                print("honest fill: first print after %s, not this bar's close." % res["trigger"]["time"])
        return 0 if res["status"] == "triggered" else 1
    except EntryError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
