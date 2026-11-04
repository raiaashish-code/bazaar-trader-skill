#!/usr/bin/env python3
"""Risk manager. PASS or BLOCK. One slot. Paper only. IST window."""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.india_clock import (  # noqa: E402
    CLOSE, OPEN, in_dead_zone, parse_hhmm, parse_now, to_ist, trading_day,
)
from lib.io_util import rupees, write_json

ORDER_FIELDS = ("symbol", "side", "qty", "type", "time_in_force", "product", "exchange",
               "order_class", "take_profit_limit_price", "stop_loss_stop_price", "limit_price")
DEFAULTS = {
    "max_loss_per_trade_inr": 500,
    "max_daily_loss_inr": 1500,
    "max_trades_per_day": 1,
    "max_open_positions": 1,
    "min_reward_risk": 1,
    "require_stop": True,
    "allow_short": False,
    "allow_margin": False,
    "allow_options": False,
    "paper": True,
    "live_trading": False,
    "no_entries_before": "09:45",
    "no_entries_after": "14:30",
    "skip_dead_zone": True,
    "budget": 50000,
    "broker": "paper",
}


class RiskError(Exception):
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


def window_check(now_ist, c):
    before = parse_hhmm(c.get("no_entries_before") or "09:45")
    after = parse_hhmm(c.get("no_entries_after") or "14:30")
    d, t = now_ist.date(), now_ist.time().replace(second=0, microsecond=0)
    ok, why = trading_day(d)
    stamp = now_ist.strftime("%a %Y-%m-%d %H:%M")
    if not ok:
        return ["window: NSE is closed today (%s, %s IST)" % (why, stamp)]
    if t < OPEN or now_ist.time() >= CLOSE:
        return ["window: NSE is closed (%s IST; session 09:15-15:30)" % stamp]
    if t < before:
        return ["window: no new entries before %s IST (it is %s)" % (before.strftime("%H:%M"), t.strftime("%H:%M"))]
    if t > after:
        return ["window: no new entries after %s IST (it is %s)" % (after.strftime("%H:%M"), t.strftime("%H:%M"))]
    if c.get("skip_dead_zone") and in_dead_zone(t):
        return ["window: 11:15-13:15 IST is the dead zone on this desk; no new entries"]
    return []


def rec_day(rec):
    return str(rec.get("date") or str(rec.get("at", ""))[:10])


def rec_is_entry(rec):
    k = rec.get("kind")
    if k:
        return k == "entry"
    return str(rec.get("side", "")).lower() == "buy"


def placed_today(state, today):
    return [r for r in (state or {}).get("orders", [])
            if r.get("status") == "placed" and rec_day(r) == today]


def check(orders, cfg, portfolio=None, prices=None, state=None, today=None, now=None):
    c = dict(DEFAULTS)
    c.update(cfg or {})
    now_utc = now or parse_now(None)
    now_ist = to_ist(now_utc)
    today = today or now_ist.date().isoformat()
    cash = _f((portfolio or {}).get("cash"))
    if cash is None:
        cash = _f(c.get("budget")) or 0
    results = []
    done = placed_today(state, today)
    entries = [r for r in done if rec_is_entry(r)]
    open_n = sum(1 for r in entries if r.get("status") == "placed")
    for order in orders:
        reasons, warnings = [], []
        fp = fingerprint(order)
        kind = "entry" if str(order.get("side", "")).lower() == "buy" else "exit"
        if not c.get("paper", True) or c.get("live_trading"):
            reasons.append("live trading is disabled: this pack is paper only")
        if str(order.get("broker") or c.get("broker") or "paper").lower() != "paper":
            reasons.append("broker must be paper")
        if kind == "entry":
            reasons.extend(window_check(now_ist, c))
            if len(entries) >= int(c.get("max_trades_per_day") or 1):
                reasons.append("max trades per day is %s (one slot)" % c["max_trades_per_day"])
            if open_n >= int(c.get("max_open_positions") or 1):
                reasons.append("already one open position; this pack runs one slot")
        side = str(order.get("side", "")).lower()
        if side == "sell" and kind == "entry" and not c.get("allow_short"):
            reasons.append("shorts are off")
        if order.get("product") == "MARGIN" and not c.get("allow_margin"):
            reasons.append("margin is off")
        if (order.get("instrument") in ("OPTIDX", "OPTSTK") or
                re.search(r"\d(CE|PE)$", str(order.get("symbol") or "").upper())) and not c.get("allow_options"):
            reasons.append("options are off in the example config")
        stop = _f(order.get("stop_loss_stop_price")) or _f((order.get("plan") or {}).get("stop"))
        if c.get("require_stop") and kind == "entry" and not stop:
            reasons.append("require_stop: no stop on this order")
        qty = _f(order.get("qty")) or 0
        plan = order.get("plan") or {}
        entry = _f(order.get("limit_price")) or _f(plan.get("entry")) or (prices or {}).get(str(order.get("symbol", "")).upper())
        target = _f(order.get("take_profit_limit_price")) or _f(plan.get("target"))
        max_loss = _f(plan.get("max_loss"))
        if entry and stop and qty:
            risk = abs(entry - stop) * qty
            if max_loss is None:
                max_loss = risk
            if max_loss > float(c.get("max_loss_per_trade_inr") or 0) + 0.01:
                reasons.append("max loss %s is over the %s cap" % (rupees(max_loss), rupees(c["max_loss_per_trade_inr"])))
        if entry and stop and target and stop:
            risk_px = abs(entry - stop)
            reward_px = abs(target - entry)
            if risk_px > 0 and reward_px / risk_px + 1e-9 < float(c.get("min_reward_risk") or 0):
                reasons.append("reward:risk %.2f is under the minimum %s" % (reward_px / risk_px, c["min_reward_risk"]))
        cost = (entry or 0) * qty
        if cost > cash + 0.01:
            reasons.append("order costs %s, cash is %s" % (rupees(cost), rupees(cash)))
        verdict = "BLOCK" if reasons else "PASS"
        results.append({"fingerprint": fp, "symbol": order.get("symbol"), "kind": kind,
                        "verdict": verdict, "reasons": reasons, "warnings": warnings})
        if verdict == "PASS" and kind == "entry":
            open_n += 1
    return {"date": today, "clock": "IST", "results": results,
            "pass": sum(1 for r in results if r["verdict"] == "PASS"),
            "block": sum(1 for r in results if r["verdict"] == "BLOCK")}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--orders", default="trader/orders.json")
    p.add_argument("--config", default="trader/config.json")
    p.add_argument("--state", default="trader/state/broker.json")
    p.add_argument("--now")
    p.add_argument("--write", default="trader/risk.json")
    a = p.parse_args(argv)
    try:
        blob = json.load(open(a.orders, encoding="utf-8"))
        orders = blob.get("orders") if isinstance(blob, dict) else blob
        orders = [o for o in (orders or []) if o]
        cfg = json.load(open(a.config, encoding="utf-8")) if os.path.exists(a.config) else {}
        state = json.load(open(a.state, encoding="utf-8")) if os.path.exists(a.state) else None
        res = check(orders, cfg, state=state, now=parse_now(a.now))
        write_json(a.write, res)
        for r in res["results"]:
            print("%s %s %s" % (r["symbol"], r["verdict"], "; ".join(r["reasons"]) or "ok"))
        return 0 if res["block"] == 0 and res["pass"] else 1
    except RiskError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
