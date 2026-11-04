---
name: bazaar-timemachine
description: >-
  Time Machine for NSE. Replays every possible outcome of a trade before you
  risk a rupee: 10,000 simulated IST sessions plus every past day the same
  opening-range rule fired. Conservative same-bar rule: if stop and target
  both print in one bar, the stop counts. Use when the user says "what are
  the odds", "replay this", "time machine", or after /bazaar-exit wrote
  trader/plan.json.
argument-hint: "[--plan trader/plan.json] [--offline sessions.json]"
---

# bazaar-timemachine

The Time Machine is the look-before-you-leap step. It does not say buy. A
coin flip is a valid answer, and then you skip the trade. Most people who
day trade lose money; seeing 10,000 paths does not create an edge.

`${CLAUDE_SKILL_DIR}` is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" --plan trader/plan.json --offline sessions.json --seed 19
```

The session is 75 five-minute bars from 09:15 to 15:30 IST (not 78 US bars
from 09:30 ET). Seed 19 matches the US reel so anyone can repeat a fixture.
History replay uses the same ORB rule: first close beyond the range, stop at
or-mid, target 1R, stop first if both print in one bar.

This tool never places an order. If the verdict is "close to a coin flip",
do not force a ticket through bazaar-broker. This replay is conservative on purpose.

## Safety

This is not financial advice. Odds are not a live edge. Continue only if you
still want a paper ticket: bazaar-budget, bazaar-risk, then type yes in
bazaar-broker. Live scalp and live equity stay off.

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
