---
name: bazaar-analyst
description: >-
  Results Analyst for NSE/BSE names. Reads quarterly revenue, operating
  profit, net profit and EPS from an offline results file and sums up what
  changed, including year-on-year growth and TTM margin. Numbers only; it
  never says whether a stock is a buy. Use when the user says "results",
  "what changed this quarter", "earnings", "TTM margin", or on a schedule
  with /bazaar-news.
argument-hint: "SYMBOL [--offline FILE] [--quarters 4]"
---

# bazaar-analyst

The Results Analyst lays out reported numbers. It does not score a setup.
The US pack reads SEC companyfacts XBRL. Indian companies do not file 10-Q
there. This skill reads a JSON of periods you already saved (NSE financial
results, BSE, or a hand-built fixture).

`${CLAUDE_SKILL_DIR}` is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/facts.py" RELIANCE --offline tests/fixtures/bazaar-analyst/RELIANCE.json
python3 "${CLAUDE_SKILL_DIR}/facts.py" RELIANCE TCS --offline results.json --json
```

How the quarters are built:

- A quarter is a reported Q1/Q2/Q3/Q4 row.
- When only an annual and three quarters exist, Q4 may be marked derived
  (year minus Q1-Q3), same idea as the US 10-K minus three 10-Qs.
- Growth is versus the same quarter a year earlier.
- Banks and insurers may have blank operating margins; leave them blank.

## Safety

This is not financial advice. Numbers only. Empty files stay empty. Do not
invent a profit figure when the filing is missing. A good quarter is not a
day-trade entry; still run the scanner through bazaar-broker and type yes.

## Worked path (IST)

1. bazaar-scanner lists charts that match a rule.
2. bazaar-news lists what was filed or printed about those names.
3. bazaar-entry waits for a completed bar, not a forming one.
4. bazaar-exit writes stop, target and flat-by 15:15 IST.
5. bazaar-timemachine says the odds, including a coin flip.
6. bazaar-budget sizes in rupees; qty 0 means skip.
7. bazaar-risk PASS or BLOCK. BLOCK ends the path.
8. bazaar-broker shows the paper ticket. You type yes for that one order.
9. bazaar-alerts watches the stop, the target and 15:15 IST.

Nothing in that path is live. Paper is the only mode. A scan is not a buy.
Day type from 10:30 IST is not used on earlier bars. Empty FII/OI stays empty.
This is not financial advice. Your typed yes is still not a live order.

## What this is not

- Not a US skill. Clocks are IST. Holidays are NSE. Tickers are NSE cash.
- Not Alpaca. Tickets are NSE INTRADAY paper payloads. This pack never sends them.
- Not SEC EDGAR and not the House Clerk. Filings are NSE announcements;
  smart money is bulk/block and FII-DII.
- Not a live bot. Paper is the only mode.
- Not a promise of edge. If the time machine is a coin flip, skip the trade.
