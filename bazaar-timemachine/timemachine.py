#!/usr/bin/env python3
"""Time Machine. Replays the rest of the NSE session from the name's own bars.

Conservative: if stop and target sit in the same bar, the stop counts.
Honest: entry is the close of the trigger bar for the history replay (same as the
US pack); live you still wait for the next print. This tool never places an order.
"""

import argparse
import json
import os
import random
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.io_util import write_json  # noqa: E402

SESSION_BARS = 75  # 09:15 to 15:30 in 5-minute slots
SAMPLE_PATHS = 8
BAND_PATHS = 2000
BAND_Q = (0.05, 0.25, 0.5, 0.75, 0.95)
HIST_BINS = 20


class TMError(Exception):
    pass


def pct(a, q):
    return a[min(len(a) - 1, int(q * len(a)))]


def simulate(pool, entry, stop, target, k, last, replays=10000, seed=19, window=2, side="buy"):
    long = side == "buy"
    risk = (entry - stop) if long else (stop - entry)

    def slot(rng, i):
        return i if window == 0 else min(SESSION_BARS - 1, max(1, i + rng.randint(-window, window)))

    rng = random.Random(seed)
    outcomes, closes, paths = [], [], []
    for n in range(replays):
        p = entry
        outcome = None
        keep = n < SAMPLE_PATHS
        path = [entry]
        for i in range(k + 1, last + 1):
            bucket = pool.get(slot(rng, i)) or pool.get(i) or [(1, 1, 1, 1)]
            _o, h, l, c = rng.choice(bucket)
            hi, lo, cl = p * h, p * l, p * c
            if outcome is None:
                if long:
                    if lo <= stop:
                        outcome = "stop"
                    elif hi >= target:
                        outcome = "target"
                else:
                    if hi >= stop:
                        outcome = "stop"
                    elif lo <= target:
                        outcome = "target"
            p = cl
            if keep:
                path.append(round(p, 2))
        outcomes.append(outcome or "close")
        closes.append(p)
        if keep:
            paths.append(path)
    cnt = {x: outcomes.count(x) for x in ("target", "stop", "close")}
    Rs = [((target - entry) if long else (entry - target)) / risk if o == "target" else
          -1.0 if o == "stop" else ((p - entry) if long else (entry - p)) / risk
          for o, p in zip(outcomes, closes)]
    return {
        "replays": replays, "seed": seed,
        "p_target": round(cnt["target"] / replays, 4),
        "p_stop": round(cnt["stop"] / replays, 4),
        "p_neither": round(cnt["close"] / replays, 4),
        "avg_R": round(statistics.mean(Rs), 3),
        "sample_paths": paths,
        "note": "same-bar stop+target counts as stop. Not financial advice.",
    }


def opening_range(bars, n):
    return max(b["h"] for b in bars[:n]), min(b["l"] for b in bars[:n])


def history_replay(sessions, or_minutes=15, target_r=1, last=74, side="buy"):
    long = side == "buy"
    n = or_minutes // 5
    trades = []
    for d, bars in sessions:
        oh, ol = opening_range(bars, n)
        kk = next((i for i in range(n, min(last, len(bars) - 1) + 1)
                   if (bars[i]["c"] > oh if long else bars[i]["c"] < ol)), None)
        if kk is None:
            continue
        e = round(bars[kk]["c"], 2)
        s = round((oh + ol) / 2, 2)
        risk = (e - s) if long else (s - e)
        if risk <= 0:
            continue
        t = round(e + target_r * risk, 2) if long else round(e - target_r * risk, 2)
        oc = None
        for b in bars[kk + 1:last + 1]:
            if (b["l"] <= s) if long else (b["h"] >= s):
                oc = "stop"
                break
            if (b["h"] >= t) if long else (b["l"] <= t):
                oc = "target"
                break
        trades.append({"date": d, "entry": e, "stop": s, "target": t, "outcome": oc or "close"})
    ntr = len(trades)
    return {
        "sessions": len(sessions), "triggered": ntr,
        "target": sum(1 for x in trades if x["outcome"] == "target"),
        "stop": sum(1 for x in trades if x["outcome"] == "stop"),
        "close": sum(1 for x in trades if x["outcome"] == "close"),
        "trades": trades,
    }


def verdict(mc, hist):
    p = mc["p_target"]
    if hist["triggered"] < 10:
        return "too few past fires (%d). A coin flip until you have more sessions." % hist["triggered"]
    if p < 0.35 and mc["p_stop"] > 0.4:
        return "lean against: stop hits more often than target in the replay."
    if p > 0.45 and mc["avg_R"] > 0:
        return "close to a coin flip with a small positive average R. That is not an edge."
    return "close to a coin flip. That is the point of looking before you risk a rupee."


def build_pool(sessions):
    pool = {}
    for _d, bars in sessions:
        for i, b in enumerate(bars):
            o = b.get("o") or b["c"]
            if o <= 0:
                continue
            pool.setdefault(i, []).append((1.0, b["h"] / o, b["l"] / o, b["c"] / o))
    return pool


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--plan", default="trader/plan.json")
    p.add_argument("--offline", required=True, help="JSON {sessions: [[date, bars], ...]}")
    p.add_argument("--replays", type=int, default=10000)
    p.add_argument("--seed", type=int, default=19)
    p.add_argument("--write", default="trader/timemachine.json")
    a = p.parse_args(argv)
    try:
        plan = json.load(open(a.plan, encoding="utf-8"))
        raw = json.load(open(a.offline, encoding="utf-8"))
        sessions = raw["sessions"] if isinstance(raw, dict) else raw
        pool = build_pool(sessions)
        entry, stop, target = plan["entry"], plan["stop"], plan["target"]
        k = int(plan.get("bar_index") or 3)
        last = SESSION_BARS - 1
        mc = simulate(pool, entry, stop, target, k, last, replays=a.replays, seed=a.seed,
                      side=plan.get("side", "buy"))
        hist = history_replay(sessions, side=plan.get("side", "buy"))
        doc = {"symbol": plan.get("symbol"), "monte_carlo": mc, "history": hist,
               "verdict": verdict(mc, hist), "clock": "IST",
               "disclaimer": "Not financial advice. Replay odds are not a live edge."}
        write_json(a.write, doc)
        print("%s  target %.1f%%  stop %.1f%%  neither %.1f%%  avg R %s" % (
            plan.get("symbol"), mc["p_target"] * 100, mc["p_stop"] * 100, mc["p_neither"] * 100, mc["avg_R"]))
        print("history: %d fires in %d sessions (%d target / %d stop / %d close)" % (
            hist["triggered"], hist["sessions"], hist["target"], hist["stop"], hist["close"]))
        print(doc["verdict"])
        return 0
    except TMError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
