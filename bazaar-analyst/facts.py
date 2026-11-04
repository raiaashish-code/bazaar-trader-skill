#!/usr/bin/env python3
"""Results reader. NSE/BSE quarterly figures, not SEC XBRL.

    python3 facts.py RELIANCE --offline tests/fixtures/bazaar-analyst/RELIANCE.json

Numbers only: this tool never says whether a stock is a buy.
A quarter is a reported period of about 90 days. The fourth quarter is the
full year minus the first three, marked derived, when only annual + 9M exist.
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.io_util import rupees, write_json  # noqa: E402


class FactsError(Exception):
    pass


def growth(curr, prev):
    if prev in (None, 0) or curr is None:
        return None
    return round((curr / prev - 1) * 100.0, 1)


def margin(part, revenue):
    if part is None or not revenue:
        return None
    return round(part / revenue * 100.0, 1)


def derive_q4(annual, q1, q2, q3, field):
    vals = [annual.get(field), q1.get(field), q2.get(field), q3.get(field)]
    if any(v is None for v in vals):
        return None
    return round(vals[0] - vals[1] - vals[2] - vals[3], 2)


def layout_quarters(rows):
    """rows: list of {period, kind=Q|Y, revenue, operating_income, net_income, eps} oldest first."""
    by = {r["period"]: r for r in rows}
    out = []
    for r in rows:
        if r.get("kind") != "Q":
            continue
        yoy = None
        year, tag = r["period"].split("-")
        prev = "%s-%s" % (int(year) - 1, tag)
        if prev in by:
            yoy = growth(r.get("revenue"), by[prev].get("revenue"))
        rec = dict(r)
        rec["yoy_revenue_pct"] = yoy
        rec["op_margin_pct"] = margin(r.get("operating_income"), r.get("revenue"))
        rec["net_margin_pct"] = margin(r.get("net_income"), r.get("revenue"))
        rec["derived"] = bool(r.get("derived"))
        out.append(rec)
    return out


def summarise(quarters, n=4):
    last = quarters[-n:]
    ttm_rev = sum(q.get("revenue") or 0 for q in last)
    ttm_ni = sum(q.get("net_income") or 0 for q in last)
    return {
        "quarters": last,
        "ttm_revenue": ttm_rev,
        "ttm_net_income": ttm_ni,
        "ttm_net_margin_pct": margin(ttm_ni, ttm_rev),
        "latest": last[-1] if last else None,
        "note": "Numbers only. Not a buy or sell.",
    }


def load_offline(path, symbol):
    doc = json.load(open(path, encoding="utf-8"))
    if symbol and symbol.upper() in doc:
        doc = doc[symbol.upper()]
    return doc


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("symbols", nargs="+")
    p.add_argument("--offline", required=True)
    p.add_argument("--quarters", type=int, default=4)
    p.add_argument("--json", action="store_true")
    p.add_argument("--write", default="trader/metrics.json")
    a = p.parse_args(argv)
    metrics = {}
    for sym in a.symbols:
        raw = load_offline(a.offline, sym)
        rows = raw.get("periods") or raw.get("quarters") or raw
        laid = layout_quarters(rows)
        metrics[sym.upper()] = summarise(laid, n=a.quarters)
    write_json(a.write, metrics)
    if a.json:
        print(json.dumps(metrics, indent=2))
        return 0
    for sym, m in metrics.items():
        latest = m["latest"] or {}
        print("%s  latest %s  revenue %s  net %s  yoy %s%%  TTM net margin %s%%" % (
            sym, latest.get("period"), rupees(latest.get("revenue") or 0),
            rupees(latest.get("net_income") or 0), latest.get("yoy_revenue_pct"),
            m.get("ttm_net_margin_pct")))
        print("  %s" % m["note"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
