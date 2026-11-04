---
name: bazaar-alerts
description: >-
  Price Alerts for NSE. Rings when a price, a stop or the 09:15 IST opening
  bell hits, and at 15:15 to flatten. Use when the user says "alert me",
  "opening bell", "watch my stop", "flat by close", or while a paper trade
  is open after /bazaar-broker.
argument-hint: "[clock | add | check | list]"
---

# bazaar-alerts

Alerts watch the plan while it is open. They do not place an order. This is
not financial advice.

`${CLAUDE_SKILL_DIR}` is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/alerts.py" clock --now "2026-10-19 09:14"
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --from-plan trader/plan.json
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --opening-bell
python3 "${CLAUDE_SKILL_DIR}/alerts.py" check --quotes quotes.json --now "2026-10-19 15:15"
```

Rule types: above/target, below/stop, pct_move, opening_bell (09:15 IST),
time (flat by 15:15 IST). A rule with a date is only watched that IST day.
Quotes are for alerts only, never for timing an order.

The US pack rings at 15:55 ET. This pack rings at 15:15 IST for cash. NSE
has no regular 13:00 early close like the day after US Thanksgiving;
Muhurat is treated as closed for new day trades.

## Safety

This is not financial advice. An alert is not a yes. Flatten still goes
through bazaar-risk and your typed yes if you use bazaar-broker for the exit.

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
