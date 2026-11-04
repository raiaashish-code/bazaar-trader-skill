---
name: bazaar-scanner
description: >-
  Chart Scanner for NSE/BSE. Scans EQ charts for setups: opening-range
  breakouts after 09:15 IST, flags, oversold bounces. Builds the list of NSE
  cash EQ names from a bhavcopy, runs a pre-open scan of daily closes
  (20-day closing-high breakout, bull flag, reclaimed the 20-day average,
  oversold, oversold bounce) and an intraday opening-range breakout scan on
  5-minute bars, then writes trader/watchlist.json for bazaar-news and
  bazaar-entry. Use when the user says "scan the market", "find me NSE
  setups", "what is breaking out", "opening range breakouts", "Nifty
  stocks", "pre-open scan", "build my watchlist", or at the start of an IST
  session before /bazaar-news.
argument-hint: "[universe | daily | orb] [--at HH:MM]"
---

# bazaar-scanner

The Chart Scanner is the first step of a day trade. It reads charts and lists
the ones that match a rule. That is all it does. A scan is a list of charts
that match a rule, not a list of stocks to buy, and a setup on a chart is not
a prediction. Most people who day trade lose money; the scanner does not
change that.

`${CLAUDE_SKILL_DIR}` below is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/scan.py" universe --offline bhav.csv
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily --offline daily.json --now "2026-10-19 08:30"
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb --offline bars.json --now "2026-10-19 10:15"
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb --at 10:15 --or-minutes 15
```

Flags: `--min-price 50` and `--min-volume` (daily 100,000), `--or-minutes 15`,
`--now "2026-10-19 10:15"` (IST) to pin the clock, `--offline PATH`,
`--no-write`, `--show N`. Exit code 0 when the scan found something, 1 when
it found nothing. This pack does not invent names: empty bhavcopy stays empty.

## What it reads and writes

| file | what |
| --- | --- |
| `trader/universe.txt` | written by `universe`: one `SYMBOL\|Name` a line |
| `trader/watchlist.json` | written by `daily` and `orb`: `mode`, `as_of`, `hits[]` |
| `trader/config.json` | optional IST windows |

## The universe

`universe` reads an NSE CM bhavcopy (UDiFF or classic CSV) and keeps a row
when, in this order:

1. Series is EQ. BE, BZ, ST, SM, GS and similar are out.
2. The name is not an ETF / BeES / Bharat Bond / InvIT / REIT product.
3. The ticker is a plain NSE symbol.

There is no Nasdaq Trader file for India. Do not mix `.NS` Yahoo suffixes
into `trader/universe.txt`; keep the NSE cash ticker (RELIANCE, not
RELIANCE.NS).

## The daily scan (before 09:15 IST)

Daily closes only. Today's bar is dropped until 15:30 IST. Setups, from
closes only:

- breakout_20d: last close above every close of the 20 before it
- bull_flag: up more than 10% over the 10 sessions before the last 5, then
  the last 5 closes inside a 5% range
- reclaim_ma20: closed under the 20-day average, then closed above it
- oversold: RSI 14 (Wilder) under 30
- oversold_bounce: RSI 14 was under 30 yesterday and today closed up

## Opening-range breakout

The range is the first `--or-minutes` (15) of the session starting 09:15 IST,
not 09:30 ET. A hit is the first completed 5-minute bar to CLOSE above the
range high. A bar still forming does not count. A same-minute last print is
not a fill; bazaar-entry and lib/honest.py wait for the next print.

Floors: `--min-price 50` (illiquid cash names), `--min-volume` 0 on orb.

## Safety

This is not financial advice. The scanner does not place an order. A hit is
not a yes. Run bazaar-news, bazaar-entry, bazaar-exit, bazaar-timemachine,
bazaar-budget and bazaar-risk before bazaar-broker. bazaar-broker still needs
your typed yes, and even then it only logs paper.

Muhurat sessions are not treated as a full day-trade session. Weekends and
the NSE holiday list in `lib/india_clock.py` keep the scanner dark.
