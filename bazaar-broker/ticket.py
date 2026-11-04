#!/usr/bin/env python3
"""Order tickets. Never talks to a broker. Never places anything. Your typed yes only."""

import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.india_clock import ist_iso, parse_now, to_ist  # noqa: E402
from lib.io_util import read_json, rupees, write_json

ORDER_FIELDS = ("symbol", "side", "qty", "type", "time_in_force", "product", "exchange",
               "order_class", "take_profit_limit_price", "stop_loss_stop_price", "limit_price")
YES_WORDS = ("yes", "y")
BATCH_WORDS = {"all", "every", "everything", "rest", "remaining", "them", "both", "batch", "each"}
DOUBT_WORDS = {"no", "not", "dont", "don't", "wait", "cancel", "stop", "but", "maybe", "later",
               "hold", "unless", "if"}


class TicketError(Exception):
    pass


def fingerprint(order):
    core = {k: order[k] for k in ORDER_FIELDS if k in order and order[k] is not None}
    blob = json.dumps(core, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _str_num(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        f = float(v)
        return str(int(f)) if f == int(f) else repr(f)
    return str(v)


def paper_input(order):
    """Arguments a human would paste into a paper account. This pack does not send them."""
    out = {}
    for k in ORDER_FIELDS:
        if k in order and order[k] is not None:
            out[k] = order[k]
    out["paper"] = True
    return out


def plain(order):
    qty = _str_num(order.get("qty"))
    parts = ["%s %s %s, %s, INTRADAY NSE paper" % (
        str(order.get("side", "")).upper(), qty, order.get("symbol"), order.get("type", "market"))]
    if order.get("stop_loss_stop_price") is not None:
        parts.append("stop-loss %s" % order["stop_loss_stop_price"])
    if order.get("take_profit_limit_price") is not None:
        parts.append("take-profit %s" % order["take_profit_limit_price"])
    plan = order.get("plan") or {}
    if plan.get("max_loss") is not None:
        parts.append("max loss about %s if the stop fills (it can fill worse)" % rupees(plan["max_loss"]))
    return " / ".join(parts)


def amount_numbers(order):
    nums = []
    for k in ("qty", "limit_price", "stop_loss_stop_price", "take_profit_limit_price"):
        if order.get(k) is not None:
            v = _f(order[k])
            if v is not None:
                nums.append(v)
    ml = _f((order.get("plan") or {}).get("max_loss"))
    if ml is not None:
        nums.append(ml)
    return nums


def parse_yes(reply, order, batch_symbols=()):
    raw = (reply or "").strip()
    if not raw:
        return False, "the reply is empty"
    if "?" in raw:
        return False, "the reply is a question, not a yes"
    words = re.findall(r"[a-z']+", raw.lower())
    if not words or words[0] not in YES_WORDS:
        return False, "only a reply that starts with \"yes\" counts (not ok, sure, go, do it)"
    if BATCH_WORDS & set(words):
        return False, "a yes covers one order at a time, not a batch"
    if DOUBT_WORDS & set(words[1:]):
        return False, "the reply has a condition or a doubt in it; ask again"
    sym = str(order.get("symbol", "")).upper()
    tokens = set(re.findall(r"[A-Z][A-Z.\-]{0,11}", raw.upper()))
    others = {s.upper() for s in batch_symbols} - {sym}
    named = tokens & others
    if named:
        return False, "the reply names %s, but this order is for %s" % (", ".join(sorted(named)), sym)
    nums = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", raw)]
    if nums:
        want = amount_numbers(order)
        if not any(abs(n - w) < 0.005 for n in nums for w in want):
            return False, "the reply says %s, but this order is %s" % (
                ", ".join(_str_num(n) for n in nums), plain(order))
    return True, "explicit yes for %s" % plain(order)


def rec_day(rec):
    return str(rec.get("date") or str(rec.get("at", ""))[:10])


def risk_verdict(risk, fp, today):
    if not risk:
        return None, "bazaar-risk has not checked these orders"
    if risk.get("date") != today:
        return None, "the risk check is from %s, not today" % risk.get("date")
    for r in risk.get("results", []):
        if r.get("fingerprint") == fp:
            return r, None
    return None, "this exact order was not in the last risk check"


def status_of(order, risk, state, today):
    fp = fingerprint(order)
    rv, why = risk_verdict(risk, fp, today)
    if rv is None:
        return False, "NOT READY: " + why, None
    if rv.get("verdict") != "PASS":
        return False, "BLOCKED by bazaar-risk: " + "; ".join(rv.get("reasons", [])), rv
    found = None
    for rec in (state or {}).get("orders", []):
        if rec.get("fingerprint") == fp and rec_day(rec) == today:
            found = rec
    if found:
        return False, "DONE: %s at %s" % (found.get("status"), found.get("at")), rv
    return True, "READY: bazaar-risk PASS, waiting for your yes", rv


def render(order, idx, total, risk, state, today):
    ready, label, rv = status_of(order, risk, state, today)
    lines = ["ORDER %d of %d, PAPER account, paper (this tool never sends the order)" % (idx, total)]
    lines.append("  " + plain(order))
    lines.append("  " + label)
    lines.append("  payload a human could key into paper:")
    for l in json.dumps(paper_input(order), indent=2).splitlines():
        lines.append("    " + l)
    if ready:
        lines.append("  Reply \"yes\" to record approval for this one order, or \"no\" to skip it.")
        lines.append("  Nothing is sent to a broker from this pack. Paper is the only mode.")
    return "\n".join(lines), ready


def append_state(path, rec):
    state = read_json(path, "broker state", required=False) or {"orders": []}
    state.setdefault("orders", []).append(rec)
    write_json(path, state)
    return state


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    show = sub.add_parser("show")
    show.add_argument("--orders", default="trader/orders.json")
    show.add_argument("--risk", default="trader/risk.json")
    show.add_argument("--state", default="trader/state/broker.json")
    show.add_argument("--now")
    ap = sub.add_parser("approve")
    ap.add_argument("--index", type=int, required=True)
    ap.add_argument("--reply", required=True)
    ap.add_argument("--orders", default="trader/orders.json")
    ap.add_argument("--risk", default="trader/risk.json")
    ap.add_argument("--state", default="trader/state/broker.json")
    ap.add_argument("--now")
    no = sub.add_parser("decline")
    no.add_argument("--index", type=int, required=True)
    no.add_argument("--orders", default="trader/orders.json")
    no.add_argument("--risk", default="trader/risk.json")
    no.add_argument("--state", default="trader/state/broker.json")
    no.add_argument("--now")
    a = p.parse_args(argv)
    now = parse_now(a.now)
    today = to_ist(now).date().isoformat()
    if not os.path.isfile(a.orders):
        print("no %s yet. Run scanner -> entry -> exit -> budget -> risk first, "
              "or pass --orders. This tool never talks to a broker." % a.orders)
        return 0
    blob = json.load(open(a.orders, encoding="utf-8"))
    orders = [o for o in (blob.get("orders") if isinstance(blob, dict) else blob) if o]
    if not orders:
        print("no paper tickets in %s." % a.orders)
        return 0
    risk = read_json(a.risk, "risk", required=False)
    state = read_json(a.state, "broker state", required=False) or {"orders": []}
    if a.cmd == "show":
        for i, order in enumerate(orders, 1):
            print(render(order, i, len(orders), risk, state, today)[0])
            print()
        return 0
    i = a.index - 1
    if i < 0 or i >= len(orders):
        print("error: no order %s" % a.index, file=sys.stderr)
        return 1
    order = orders[i]
    ready, label, _rv = status_of(order, risk, state, today)
    if a.cmd == "decline":
        append_state(a.state, {"fingerprint": fingerprint(order), "status": "declined",
                               "date": today, "at": ist_iso(now), "symbol": order.get("symbol"),
                               "side": order.get("side"), "kind": "entry"})
        print("declined order %d" % a.index)
        return 0
    if not ready:
        print("error: %s" % label, file=sys.stderr)
        return 1
    ok, why = parse_yes(a.reply, order, [o.get("symbol") for o in orders])
    if not ok:
        print("error: %s" % why, file=sys.stderr)
        return 1
    append_state(a.state, {"fingerprint": fingerprint(order), "status": "approved",
                           "date": today, "at": ist_iso(now), "symbol": order.get("symbol"),
                           "side": order.get("side"), "kind": "entry", "reply": a.reply,
                           "note": "approved for paper; this pack still does not place the order"})
    print("APPROVED (paper log only): %s" % why)
    return 0


if __name__ == "__main__":
    sys.exit(main())
