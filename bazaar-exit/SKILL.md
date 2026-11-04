---
name: bazaar-exit
description: >-
  Exit Planner for NSE. Sets your stop and your target in rupees before you
  enter, so you know when to get out. Default long ORB: stop at the
  opening-range midpoint, target 1R, flat by 15:15 IST. Writes
  trader/plan.json for bazaar-timemachine and bazaar-budget. Use when the user
  says "where is my stop", "plan the trade", "1R target", or after
  /bazaar-entry says triggered.
argument-hint: "--symbol SYM --entry PX --or-high X --or-low Y"
---

# bazaar-exit

The Exit Planner sets the stop and the target before the entry. You do not
invent a target after you are in. Flat by 15:15 IST for cash (15:20 for F&O
on this desk). This is not financial advice.

`${CLAUDE_SKILL_DIR}` is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/exit.py" --symbol RELIANCE --entry 1405 --or-high 1410 --or-low 1390 --stop or-mid --target 1R
python3 "${CLAUDE_SKILL_DIR}/exit.py" --symbol RELIANCE --entry 1405 --stop pct:1 --target 2R
```

Stops: `or-mid`, `or-low`, `price:X`, `pct:X`, `atr:K`.
Targets: `1R`, `1.5R`, `2R`, `price:X`.

A long stop must sit under the entry. A stop tighter than 0.05% of price is
refused (spread noise). Size later with bazaar-budget, which adds NSE
charges to the max-loss picture. A stop fill in replay is the bar low, not
the theoretical stop (`lib/honest.stop_fill_long`).

## Safety

This is not financial advice. The planner does not place an order. Run
bazaar-timemachine before you risk a rupee. Then bazaar-budget, bazaar-risk and
bazaar-broker. Nothing is live until you type yes, and even then this pack
only logs paper.

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
