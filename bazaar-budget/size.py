#!/usr/bin/env python3
"""Budget manager. Sizes a long day trade in rupees. Whole shares, or F&O lots."""

import argparse
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.honest import equity_charges  # noqa: E402
from lib.io_util import rupees, write_json

DEFAULTS = {
    "budget": 50000,
    "cash_buffer_pct": 10,
    "max_loss_per_trade_inr": 500,
    "max_position_pct": 40,
    "max_order_inr": 25000,
    "min_order_inr": 1000,
    "min_reward_risk": 1,
    "currency": "INR",
    "paper": True,
    "lot_size": 1,
}


class SizeError(Exception):
    pass


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def shares_for(inr, per):
    if per <= 0:
        return 0
    return int(math.floor((inr + 1e-9) / per))


def round_to_lot(qty, lot):
    if lot <= 1:
        return qty
    return (qty // lot) * lot


def size_trade(plan, cfg, budget=None, price=None, cash=None, today=None):
    c = dict(DEFAULTS)
    c.update(cfg or {})
    if not c.get("paper", True):
        raise SizeError("this pack sizes PAPER trades only")
    sym = str(plan.get("symbol") or "").strip().upper()
    if not sym:
        raise SizeError("the plan has no symbol")
    side = str(plan.get("side") or "buy").strip().lower()
    if side != "buy":
        raise SizeError("this pack sizes long (buy) day trades only")
    if today and plan.get("date") and str(plan["date"]) != today:
        raise SizeError("the plan is for %s and today is %s IST" % (plan["date"], today))
    entry_plan, stop, target = _f(plan.get("entry")), _f(plan.get("stop")), _f(plan.get("target"))
    for name, v in (("entry", entry_plan), ("stop", stop), ("target", target)):
        if v is None or v <= 0:
            raise SizeError("the plan needs a positive %s" % name)
    budget = float(budget if budget is not None else c.get("budget") or 0)
    if budget <= 0:
        raise SizeError("no budget")
    if price is not None and price > entry_plan:
        ref, ref_from = round(price, 2), "honest_print"
    else:
        ref, ref_from = round(entry_plan, 2), "plan"
    stop, target = round(stop, 2), round(target, 2)
    if stop >= ref:
        raise SizeError("stop is not below entry")
    if target <= ref:
        raise SizeError("target is not above entry")
    risk = round(ref - stop, 2)
    buf_pct = float(c.get("cash_buffer_pct") or 0)
    cash_buffer = round(budget * buf_pct / 100.0, 2)
    available = budget - cash_buffer
    if cash is not None:
        available = min(available, cash - cash_buffer)
    available = max(round(available, 2), 0.0)
    lot = int(c.get("lot_size") or 1)
    limits = []
    max_loss = _f(c.get("max_loss_per_trade_inr"))
    if max_loss:
        limits.append({"name": "max loss", "inr": max_loss, "shares": round_to_lot(shares_for(max_loss, risk), lot)})
    cap_pct = _f(c.get("max_position_pct"))
    if cap_pct:
        cap = round(budget * cap_pct / 100.0, 2)
        limits.append({"name": "position cap", "inr": cap, "shares": round_to_lot(shares_for(cap, ref), lot)})
    max_order = _f(c.get("max_order_inr"))
    if max_order:
        limits.append({"name": "max order", "inr": max_order, "shares": round_to_lot(shares_for(max_order, ref), lot)})
    limits.append({"name": "cash", "inr": available, "shares": round_to_lot(shares_for(available, ref), lot)})
    qty = max(0, min(l["shares"] for l in limits))
    bound = [l["name"] for l in limits if l["shares"] == qty]
    cost = round(qty * ref, 2)
    loss = round(qty * risk, 2)
    sample_charges = equity_charges(ref, stop, qty) if qty else {"total_charges": 0}
    # Include round-trip charges in the max-loss picture so the stop is not the whole story.
    loss_with_charges = round(loss + sample_charges["total_charges"], 2)
    refusal = None
    if qty == 0:
        refusal = "one share (or one lot) risks more than your max loss or cash. No order."
    elif _f(c.get("min_reward_risk")) and (target - ref) < _f(c["min_reward_risk"]) * risk - 1e-9:
        refusal = "reward:risk is under your minimum. No order."
    elif cost < float(c.get("min_order_inr") or 0):
        refusal = "order is under your minimum. No order."
    elif not c.get("paper", True):
        refusal = "live trading is disabled in this pack."
    return {
        "symbol": sym, "side": "buy", "entry": ref, "entry_from": ref_from, "stop": stop, "target": target,
        "risk_per_share": risk, "qty": qty, "lot_size": lot, "cost": cost, "max_loss": loss,
        "max_loss_with_charges": loss_with_charges, "charges_at_stop": sample_charges,
        "bound_by": bound[0] if bound else None, "budget": budget, "refusal": refusal,
        "currency": "INR", "paper": True, "broker": "paper",
        "flat_by": plan.get("flat_by") or "15:15",
    }


def bracket_order(s):
    if s["refusal"] or s["qty"] <= 0:
        return None
    return {
        "symbol": s["symbol"], "side": "buy", "qty": str(int(s["qty"])), "type": "market",
        "time_in_force": "day", "product": "INTRADAY", "exchange": "NSE",
        "order_class": "bracket", "take_profit_limit_price": "%.2f" % s["target"],
        "stop_loss_stop_price": "%.2f" % s["stop"], "broker": "paper", "paper": True,
        "plan": {"entry": s["entry"], "stop": s["stop"], "target": s["target"],
                 "max_loss": s["max_loss_with_charges"], "flat_by": s["flat_by"]},
        "why": "paper bracket on %s: %d shares, bound by %s" % (s["symbol"], s["qty"], s["bound_by"]),
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--plan", default="trader/plan.json")
    p.add_argument("--config", default="trader/config.json")
    p.add_argument("--budget", type=float)
    p.add_argument("--write", default="trader/orders.json")
    a = p.parse_args(argv)
    try:
        plan = json.load(open(a.plan, encoding="utf-8"))
        cfg = {}
        if os.path.exists(a.config):
            cfg = json.load(open(a.config, encoding="utf-8"))
        sized = size_trade(plan, cfg, budget=a.budget, today=plan.get("date"))
        order = bracket_order(sized)
        doc = {"sized": sized, "orders": [order] if order else []}
        write_json(a.write, doc)
        if sized["refusal"]:
            print(sized["refusal"])
            return 1
        print("%s  %d shares  cost %s  max loss %s (with charges %s)  bound by %s" % (
            sized["symbol"], sized["qty"], rupees(sized["cost"]), rupees(sized["max_loss"]),
            rupees(sized["max_loss_with_charges"]), sized["bound_by"]))
        return 0
    except SizeError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
