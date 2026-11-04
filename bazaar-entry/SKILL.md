---
name: bazaar-entry
description: >-
  Entry Timer for NSE. Watches a setup bar by bar in IST and tells you the
  moment to get in: the first completed 5-minute (or 1-minute) close above
  the 09:15 opening-range high, or above a level. Forming bars wait. Same-
  minute last prints are not fills; the honest fill is the first print after
  the bar closes. Use when the user says "is it triggered", "watch RELIANCE",
  "opening range", or after /bazaar-scanner and /bazaar-news.
argument-hint: "SYMBOL [--setup orb|level] [--now IST]"
---

# bazaar-entry

The Entry Timer watches one chart and says waiting, triggered, expired or
no-data. That is all it does. Triggered is not a buy. Most people who day
trade lose money.

`${CLAUDE_SKILL_DIR}` is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/entry.py" RELIANCE --offline bars.json --now "2026-10-19 10:15"
python3 "${CLAUDE_SKILL_DIR}/entry.py" RELIANCE --offline bars.json --setup level --level 1400
```

NSE opens at 09:15 IST. The 15-minute opening range is complete at 09:30.
Default `no_entries_before` is 09:45 so the first 15 minutes after the range
can print. Default `no_entries_after` is 14:30. Day type from NIFTY at 10:30
is not an entry signal and must not be used on a 09:15 or 10:00 bar
(`lib/honest.may_use_day_type`).

## Honest fill

When status is triggered, the trigger price is the completed bar's close.
Do not treat that close as the fill. bazaar-budget should size at the next
print plus 0.15% if that print is worse. bazaar-timemachine still uses the
close for history replay, same as the US pack, and says so.

## Safety

This is not financial advice. The timer does not place an order. A trigger
is not a yes. Continue to bazaar-exit, bazaar-timemachine, bazaar-budget,
bazaar-risk and bazaar-broker. bazaar-broker records paper only after you
type yes for that one ticket.

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
