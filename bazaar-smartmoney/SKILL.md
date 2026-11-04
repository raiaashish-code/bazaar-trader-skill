---
name: bazaar-smartmoney
description: >-
  Smart-money tracker for India. Reads NSE bulk deals, NSE block deals and
  FII-DII cash provisional. This is the stand-in for the US Pelosi / House
  Clerk PTR feed, which does not apply to NSE names. Use when the user says
  "bulk deals", "block deals", "FII DII", "Pelosi for India", "who bought",
  or on a schedule with /bazaar-news.
argument-hint: "[bulk | block | fii-dii | new] [--offline FILE]"
---

# bazaar-smartmoney

US members of Congress file periodic transaction reports. Indian members of
Parliament do not publish an equivalent machine feed, and copying a US
politician's ticker list is not an NSE strategy. The honest Indian stand-in
is lagged public tape:

- NSE bulk deals (typically 0.5%+ of equity in one session)
- NSE block deals (windowed large tickets)
- NSE FII/DII cash provisional

`${CLAUDE_SKILL_DIR}` is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/deals.py" bulk --offline bulk.csv
python3 "${CLAUDE_SKILL_DIR}/deals.py" block --offline block.csv --symbol RELIANCE
python3 "${CLAUDE_SKILL_DIR}/deals.py" fii-dii --offline fii.json
python3 "${CLAUDE_SKILL_DIR}/deals.py" new --offline bulk.csv
```

A bulk print is not a reason to chase at 09:20. The file is end-of-day or
intra-day delayed. Empty FII/OI stays empty; this tool does not invent a
figure. Hits on your watchlist are flagged `WATCH` only.

## Safety

This is not financial advice. Smart-money is not a yes. Do not copy-trade a
client name from a bulk file. If you still want a paper ticket, run
bazaar-scanner through bazaar-broker and type yes for that one order. This
pack never places live.

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
