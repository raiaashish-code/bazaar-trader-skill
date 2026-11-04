#!/usr/bin/env python3
"""NSE/BSE Chart Scanner. Standard library only.

    python3 scan.py universe --offline bhav.csv
    python3 scan.py daily --offline daily.json --now "2026-10-19 08:30"
    python3 scan.py orb --offline bars.json --now "2026-10-19 10:15"

universe  EQ series from an NSE bhavcopy (UDiFF or classic). ETFs, bonds and
          SME series are dropped. Writes trader/universe.txt as SYMBOL|Name.
daily     Pre-open scan of daily CLOSES. Today's bar is dropped until 15:30 IST.
          Setups: breakout_20d, bull_flag, reclaim_ma20, oversold, oversold_bounce.
orb       Opening-range breakout on 5-minute bars. Range is 09:15-09:30 IST
          (first --or-minutes). A hit is the first COMPLETED bar to CLOSE above
          the range high. Incomplete bars and same-minute last prints are ignored.
"""

from __future__ import print_function

import argparse
import csv
import datetime
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.india_clock import CLOSE, OPEN, clock_label, parse_hhmm, parse_now, session, to_ist, trading_day, ts_to_ist
from lib.io_util import write_json

BAR_MIN = 5
MIN_DAILY_BARS = 30
DEFAULT_UNIVERSE = "trader/universe.txt"
NOTE = "A scan is a list of charts that match a rule, not a list of stocks to buy."
DROP_SERIES = {"BE", "BZ", "ST", "SM", "SZ", "GS", "GB", "N1", "N2", "N3", "N4", "N5", "Y1", "Y2"}
DROP_NAME = ("ETF", "NIFTY BEES", "GOLD BEES", "LIQUID BEES", "BHARAT BOND", "INVIT", "REIT")

SETUPS = [
    ("breakout_20d", "20-day closing-high breakout"),
    ("bull_flag", "bull flag"),
    ("reclaim_ma20", "reclaimed the 20-day average"),
    ("oversold", "oversold (RSI under 30)"),
    ("oversold_bounce", "oversold bounce"),
]


class ScanError(Exception):
    pass


def rsi(closes, n=14):
    if len(closes) < n + 1:
        return None
    g = [max(0.0, closes[i] - closes[i - 1]) for i in range(1, len(closes))]
    lo = [max(0.0, closes[i - 1] - closes[i]) for i in range(1, len(closes))]
    ag, al = sum(g[:n]) / n, sum(lo[:n]) / n
    for i in range(n, len(g)):
        ag = (ag * (n - 1) + g[i]) / n
        al = (al * (n - 1) + lo[i]) / n
    return 100 - 100 / (1 + ag / al) if al else 100.0


def find_setups(closes):
    c = closes
    last = c[-1]
    hi20 = max(c[-21:-1])
    ma20 = sum(c[-20:]) / 20.0
    ma20_prev = sum(c[-21:-1]) / 20.0
    run = c[-6] / c[-16] - 1
    rng5 = (max(c[-5:]) - min(c[-5:])) / last
    r = rsi(c)
    r_prev = rsi(c[:-1])
    tags = []
    if last > hi20:
        tags.append("breakout_20d")
    if run > 0.10 and rng5 < 0.05:
        tags.append("bull_flag")
    if c[-2] < ma20_prev and last > ma20:
        tags.append("reclaim_ma20")
    if r is not None and r < 30:
        tags.append("oversold")
    if r_prev is not None and r_prev < 30 and last > c[-2]:
        tags.append("oversold_bounce")
    return tags, {"rsi": r, "rsi_prev": r_prev, "high20": hi20, "ma20": ma20,
                  "run_pct": run * 100, "range5_pct": rng5 * 100}


def parse_bhavcopy(text):
    """NSE UDiFF or classic bhavcopy CSV -> [(SYMBOL, name, series, close, volume)]."""
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ScanError("bhavcopy has no header")
    rows = []
    for item in reader:
        series = (item.get("SctySrs") or item.get("SERIES") or "").strip().upper()
        symbol = (item.get("TckrSymb") or item.get("SYMBOL") or "").strip().upper()
        name = (item.get("FinInstrmNm") or item.get("NAME") or symbol).strip()
        close = item.get("ClsPric") or item.get("CLOSE") or "0"
        vol = item.get("TtlTradgVol") or item.get("TOTTRDQTY") or "0"
        if not symbol:
            continue
        rows.append((symbol, name, series, _f(close), _f(vol)))
    return rows


def _f(x):
    try:
        return float(str(x).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def classify_eq(symbol, name, series):
    if series != "EQ":
        return "series %s" % (series or "?")
    up = name.upper()
    for tag in DROP_NAME:
        if tag in up:
            return "ETF / bond product"
    if not symbol.replace("-", "").replace("&", "").isalnum():
        return "not a plain ticker"
    return "keep"


def build_universe(text):
    kept, counts = {}, {}
    for symbol, name, series, close, vol in parse_bhavcopy(text):
        why = classify_eq(symbol, name, series)
        counts[why] = counts.get(why, 0) + 1
        counts["rows"] = counts.get("rows", 0) + 1
        if why == "keep":
            kept[symbol] = name
    return sorted(kept.items()), counts


def daily_closes(series, now_utc):
    now = to_ist(now_utc)
    today = now.date()
    s = session(today)
    today_done = s is None or now.time() >= s[1]
    out = {}
    for ts, c in zip(series["t"], series["c"]):
        if c is None:
            continue
        d = datetime.date.fromisoformat(ts) if isinstance(ts, str) else to_ist(
            datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=int(ts))
        ).date()
        if d > today or (d == today and not today_done):
            continue
        out[d] = float(c)
    return sorted(out.items())


def scan_daily(data, symbols, now_utc, min_price, min_volume):
    hits, dates = [], {}
    counts = {"requested": len(symbols), "fetched": 0, "illiquid": 0, "short": 0, "scanned": 0}
    for sym in symbols:
        s = data.get(sym)
        if not s:
            continue
        counts["fetched"] += 1
        bars = daily_closes(s, now_utc)
        meta = s.get("meta") or {}
        price = meta.get("regularMarketPrice")
        if price is None and bars:
            price = bars[-1][1]
        vol = meta.get("regularMarketVolume")
        if vol is None:
            vol = meta.get("volume")
        if price is None or price < min_price or (min_volume > 0 and (vol is None or vol < min_volume)):
            counts["illiquid"] += 1
            continue
        if len(bars) < MIN_DAILY_BARS:
            counts["short"] += 1
            continue
        counts["scanned"] += 1
        d_last = bars[-1][0]
        dates[d_last] = dates.get(d_last, 0) + 1
        closes = [c for _, c in bars]
        tags, nums = find_setups(closes)
        if tags:
            hits.append({"symbol": sym, "setups": tags, "price": round(closes[-1], 2),
                         "close_date": d_last.isoformat(), "rsi": round(nums["rsi"], 1) if nums["rsi"] else None,
                         "volume": int(vol) if vol is not None else None, "exchange": "NSE"})
    hits.sort(key=lambda h: (-(h["price"] * (h["volume"] or 0)), h["symbol"]))
    last_date = max(dates, key=lambda d: (dates[d], d)) if dates else None
    counts["hits"] = len(hits)
    return hits, counts, last_date


def slot(day, k):
    return datetime.datetime.combine(day, OPEN) + datetime.timedelta(minutes=BAR_MIN * k)


def session_bars(series, day, cutoff):
    s = session(day)
    close_t = s[1] if s else CLOSE
    out = {}
    hs, ls = series.get("h"), series.get("l")
    for i, ts in enumerate(series["t"]):
        c = series["c"][i]
        if c is None:
            continue
        if isinstance(ts, str) and "T" in ts:
            raw = ts.replace("Z", "+00:00")
            parsed = datetime.datetime.fromisoformat(raw)
            if parsed.tzinfo is None:
                et = parsed
            else:
                et = to_ist(parsed.replace(tzinfo=None) - parsed.utcoffset())
        elif isinstance(ts, str) and len(ts) == 5:
            hh, mm = ts.split(":")
            et = datetime.datetime.combine(day, datetime.time(int(hh), int(mm)))
        else:
            et = ts_to_ist(ts)
        if et.date() != day or et.second or et.minute % BAR_MIN:
            continue
        if et.time() < OPEN or et.time() >= close_t:
            continue
        if et + datetime.timedelta(minutes=BAR_MIN) > cutoff:
            continue
        v = series.get("v")
        out[et] = {"start": et, "c": float(c),
                   "h": None if not hs or hs[i] is None else float(hs[i]),
                   "l": None if not ls or ls[i] is None else float(ls[i]),
                   "v": (v[i] or 0) if v else 0}
    return [out[k] for k in sorted(out)]


def usable(bars, day, cutoff, n_range):
    want = int((cutoff - slot(day, 0)).total_seconds() // (BAR_MIN * 60))
    s = session(day)
    if s:
        want = min(want, int((datetime.datetime.combine(day, s[1]) - slot(day, 0)).total_seconds()
                             // (BAR_MIN * 60)))
    if want < n_range or len(bars) != want:
        return False
    return all(b["start"] == slot(day, k) for k, b in enumerate(bars))


def orb_hit(bars, n_range):
    rng = bars[:n_range]
    if any(b["h"] is None or b["l"] is None for b in rng):
        return None
    oh = max(b["h"] for b in rng)
    ol = min(b["l"] for b in rng)
    for k in range(n_range, len(bars)):
        b = bars[k]
        if b["c"] > oh:
            closes_at = b["start"] + datetime.timedelta(minutes=BAR_MIN)
            return {"price": round(b["c"], 2), "at": clock_label(closes_at),
                    "bar_start": b["start"].strftime("%H:%M"), "bar_index": k,
                    "or_high": round(oh, 2), "or_low": round(ol, 2),
                    "pct_over": round((b["c"] / oh - 1) * 100, 2), "_t": closes_at}
    return None


def load_offline(path):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if isinstance(doc, dict) and "t" in doc:
        return {"_one": doc}
    return doc


def cmd_universe(a):
    if not a.offline:
        raise ScanError("universe needs --offline PATH to an NSE bhavcopy CSV (this pack does not invent names)")
    text = open(a.offline, encoding="utf-8").read()
    kept, counts = build_universe(text)
    if not a.no_write:
        os.makedirs(os.path.dirname(a.universe) or ".", exist_ok=True)
        with open(a.universe, "w", encoding="utf-8") as fh:
            for sym, name in kept:
                fh.write("%s|%s\n" % (sym, name))
    print("universe %d EQ names (from %d rows). %s" % (len(kept), counts.get("rows", 0), NOTE))
    return 0 if kept else 1


def cmd_daily(a):
    now = parse_now(a.now)
    data = load_offline(a.offline) if a.offline else {}
    symbols = a.symbols.split(",") if a.symbols else sorted(data.keys())
    hits, counts, last = scan_daily(data, symbols, now, a.min_price, a.min_volume)
    doc = {"mode": "daily", "as_of": to_ist(now).isoformat(), "universe": len(symbols),
           "scanned": counts["scanned"], "failed": counts["requested"] - counts["fetched"],
           "hits": hits, "note": NOTE, "clock": "IST"}
    if not a.no_write:
        write_json(a.watchlist, doc)
    print("daily scan %s IST: %d hits / %d scanned. %s" % (
        to_ist(now).strftime("%Y-%m-%d %H:%M"), len(hits), counts["scanned"], NOTE))
    for h in hits[: a.show]:
        print("  %s  %s  Rs %.2f  %s" % (h["symbol"], ",".join(h["setups"]), h["price"], h["close_date"]))
    return 0 if hits else 1


def cmd_orb(a):
    now = parse_now(a.now)
    local = to_ist(now)
    day = local.date()
    ok, why = trading_day(day)
    if not ok:
        raise ScanError("NSE is closed today (%s)" % why)
    at = parse_hhmm(a.at) if a.at else local.time()
    cutoff = datetime.datetime.combine(day, at)
    n_range = a.or_minutes // BAR_MIN
    data = load_offline(a.offline) if a.offline else {}
    hits = []
    for sym, series in data.items():
        bars = session_bars(series, day, cutoff)
        if not usable(bars, day, cutoff, n_range):
            continue
        hit = orb_hit(bars, n_range)
        if hit:
            hits.append({"symbol": sym, "setups": ["orb"], "price": hit["price"], "at": hit["at"],
                         "or_high": hit["or_high"], "or_low": hit["or_low"], "pct_over": hit["pct_over"],
                         "exchange": "NSE"})
    doc = {"mode": "orb", "as_of": local.isoformat(), "hits": hits, "or_minutes": a.or_minutes,
           "note": NOTE, "clock": "IST", "open": "09:15"}
    if not a.no_write:
        write_json(a.watchlist, doc)
    print("orb %s IST: %d hits. Range is 09:15 plus %d minutes. %s" % (
        local.strftime("%Y-%m-%d %H:%M"), len(hits), a.or_minutes, NOTE))
    for h in hits[: a.show]:
        print("  %s  close Rs %.2f at %s, range high Rs %.2f" % (h["symbol"], h["price"], h["at"], h["or_high"]))
    return 0 if hits else 1


def main(argv=None):
    p = argparse.ArgumentParser(description="Indian NSE chart scanner")
    p.add_argument("cmd", choices=["universe", "daily", "orb"])
    p.add_argument("--offline")
    p.add_argument("--now")
    p.add_argument("--at")
    p.add_argument("--symbols")
    p.add_argument("--min-price", type=float, default=50.0)
    p.add_argument("--min-volume", type=float, default=100000)
    p.add_argument("--or-minutes", type=int, default=15)
    p.add_argument("--universe", default=DEFAULT_UNIVERSE)
    p.add_argument("--watchlist", default="trader/watchlist.json")
    p.add_argument("--no-write", action="store_true")
    p.add_argument("--show", type=int, default=20)
    a = p.parse_args(argv)
    try:
        if a.cmd == "universe":
            return cmd_universe(a)
        if a.cmd == "daily":
            if not a.offline:
                raise ScanError("daily needs --offline JSON of {SYMBOL: {t,c,meta}}")
            return cmd_daily(a)
        if not a.offline:
            raise ScanError("orb needs --offline JSON of 5-minute bars")
        return cmd_orb(a)
    except ScanError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
