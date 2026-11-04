---
name: bazaar-budget
description: >-
  Budget Manager for INR paper accounts. Sizes every position to your budget
  and your max loss per trade, whole shares or F&O lots, and folds NSE
  charges into the max-loss picture. Writes trader/orders.json for
  bazaar-risk. Use when the user says "how many shares", "size this", "I have
  50,000 rupees", or after /bazaar-exit and /bazaar-timemachine.
argument-hint: "[--plan trader/plan.json] [--budget 50000]"
---

# bazaar-budget

The Budget Manager turns a plan into a share count. qty may be 0. That is a
valid answer: skip the trade. This is not financial advice.

`${CLAUDE_SKILL_DIR}` is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/size.py" --plan trader/plan.json --config trader/config.json --budget 50000
```

Copy `config.example.json` to `trader/config.json`. Defaults: Rs 50,000
paper, Rs 500 max loss, 10% cash buffer, one lot size 1 for cash, paper true,
live_trading false.

If the honest next print is above the plan entry, size at that worse price
(`entry_from: honest_print`). Long day trades only. Options stay off in the
example config. Any Indian discount broker's paper account is fine; this pack
does not name or call one.

## Safety

This is not financial advice. Sizing does not place an order. bazaar-risk must
PASS the exact ticket. bazaar-broker still needs your typed yes. "yes to all"
is refused. This pack will not size a live order.

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
