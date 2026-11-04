#!/usr/bin/env python3
"""Exit planner. Stop and target in rupees before you enter. Longs only by default."""

import argparse
import json
import os
import re
import sys
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.india_clock import FLAT_BY_EQUITY, parse_now, to_ist  # noqa: E402
from lib.io_util import rupees, write_json

CENT = Decimal("0.05")  # NSE equity tick is 0.05 for most names; we still plan in paise
MIN_RISK_PCT = Decimal("0.05")
PAISE = Decimal("0.01")


class PlanError(Exception):
    pass


def D(x, what="a number"):
    try:
        return Decimal(str(x))
    except Exception:
        raise PlanError("%s is not a number" % what)


def paise(x):
    return D(x).quantize(PAISE, rounding=ROUND_HALF_UP)


def floor_tick(x):
    return D(x).quantize(PAISE, rounding=ROUND_DOWN)


def parse_stop(text):
    t = str(text).strip().lower()
    if t in ("or-mid", "or_mid", "mid"):
        return "or_mid", None
    if t in ("or-low", "or_low", "low"):
        return "or_low", None
    m = re.match(r"^(price|pct|atr):\s*([0-9][0-9,]*\.?[0-9]*)$", t)
    if not m:
        raise PlanError("--stop is or-mid, or-low, price:X, pct:X or atr:K")
    return m.group(1), D(m.group(2), "--stop")


def parse_target(text):
    t = str(text).strip()
    m = re.match(r"^([0-9]*\.?[0-9]+)\s*[Rr]$", t)
    if m:
        return "r", D(m.group(1), "--target")
    m = re.match(r"^price:\s*([0-9][0-9,]*\.?[0-9]*)$", t.lower())
    if m:
        return "price", D(m.group(1), "--target")
    raise PlanError("--target is 1R, 2R or price:X")


def compute(entry, stop_rule, stop_param, target_rule, target_param, or_high=None, or_low=None,
            atr=None, atr_bars=None, side="buy"):
    e = paise(entry)
    if e <= 0:
        raise PlanError("the entry price must be above Rs 0")
    long = side == "buy"
    detail = ""
    if stop_rule in ("or_mid", "or_low"):
        if or_high is None or or_low is None:
            raise PlanError("an opening-range stop needs --or-high and --or-low")
        oh, ol = paise(or_high), paise(or_low)
        if oh <= ol:
            raise PlanError("range high must be above range low")
        if stop_rule == "or_mid":
            raw = (oh + ol) / 2
            label = "opening-range midpoint"
        else:
            raw, label = (ol if long else oh), "opening-range low" if long else "opening-range high"
    elif stop_rule == "price":
        raw, label = stop_param, "your price"
    elif stop_rule == "pct":
        raw = e * (1 - stop_param / 100) if long else e * (1 + stop_param / 100)
        label = "%s%% from the entry" % stop_param
    elif stop_rule == "atr":
        if atr is None:
            raise PlanError("an atr stop needs ATR")
        raw = e - stop_param * D(atr) if long else e + stop_param * D(atr)
        label = "%s x ATR under/over the entry" % stop_param
    else:
        raise PlanError("unknown stop rule")
    stop = floor_tick(raw) if long else paise(raw)
    if long and stop >= e:
        raise PlanError("a long stop %s is at or above the entry %s" % (rupees(stop), rupees(e)))
    if not long and stop <= e:
        raise PlanError("a short stop must sit above the entry")
    if stop <= 0:
        raise PlanError("stop works out to zero")
    risk = (e - stop) if long else (stop - e)
    if risk < e * MIN_RISK_PCT / 100:
        raise PlanError("stop is tighter than 0.05%% of price: too tight for the spread")
    if target_rule == "r":
        target = paise(e + target_param * risk if long else e - target_param * risk)
        t_label = "%sR" % target_param
    else:
        target = paise(target_param)
        t_label = "your price"
    if long and target <= e:
        raise PlanError("long target must be above entry")
    if not long and target >= e:
        raise PlanError("short target must be below entry")
    rr = ((target - e) / risk if long else (e - target) / risk).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"entry": float(e), "stop": float(stop), "target": float(target), "risk": float(risk),
            "reward_risk": float(rr), "stop_label": label, "target_label": t_label, "stop_detail": detail,
            "side": side, "flat_by": FLAT_BY_EQUITY.strftime("%H:%M"), "clock": "IST"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--stop", default="or-mid")
    p.add_argument("--target", default="1R")
    p.add_argument("--or-high", type=float)
    p.add_argument("--or-low", type=float)
    p.add_argument("--side", default="buy")
    p.add_argument("--setup", default="orb")
    p.add_argument("--write", default="trader/plan.json")
    p.add_argument("--now")
    a = p.parse_args(argv)
    try:
        rule, param = parse_stop(a.stop)
        tr, tp = parse_target(a.target)
        plan = compute(a.entry, rule, param, tr, tp, a.or_high, a.or_low, side=a.side)
        local = to_ist(parse_now(a.now))
        plan.update(symbol=a.symbol.upper(), setup=a.setup, date=local.date().isoformat(),
                    honest_note="size at the honest fill, not at this planned entry if the next print is worse")
        write_json(a.write, plan)
        print("%s %s  entry %s  stop %s (%s)  target %s (%s)  R:R %s  flat by %s IST" % (
            plan["symbol"], plan["side"], rupees(plan["entry"]), rupees(plan["stop"]), plan["stop_label"],
            rupees(plan["target"]), plan["target_label"], plan["reward_risk"], plan["flat_by"]))
        return 0
    except PlanError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
