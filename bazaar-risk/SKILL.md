---
name: bazaar-risk
description: >-
  Risk Manager for the Indian desk. Checks every ticket against IST session
  hours, the 11:15-13:15 dead zone, one-slot cap, max loss in rupees, stop
  required, paper-only, and cash. PASS or BLOCK with the reason. Use when
  the user says "check risk", "can I take this", or after /bazaar-budget
  wrote trader/orders.json and before /bazaar-broker.
argument-hint: "[--orders trader/orders.json] [--now IST]"
---

# bazaar-risk

The Risk Manager is the gate. BLOCK means stop. Do not argue it into a
ticket. This is not financial advice.

`${CLAUDE_SKILL_DIR}` is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/check.py" --orders trader/orders.json --config trader/config.json --now "2026-10-19 10:20"
```

Checks, in spirit the same as the US pack, rewritten for this desk:

1. Paper only. live_trading true is always BLOCK.
2. NSE session 09:15-15:30 IST, entries 09:45-14:30.
3. Skip 11:15-13:15 IST (dead zone).
4. Max one open slot / max one new trade per day.
5. Stop required. Reward:risk at least 1.
6. Max loss per trade and daily loss in INR.
7. Shorts, margin and options off unless you change config (do not do that
   to "enable live").
8. Day type is not a risk input before 10:31 IST.

Fingerprints match bazaar-broker. If you edit qty after a PASS, run check
again.

## Safety

This is not financial advice. PASS is not a yes. bazaar-broker still needs
your typed yes for that exact order, and it still does not send live.

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
