---
name: bazaar-broker
description: >-
  Order Executor for paper. Shows the ticket in plain words, records
  your explicit yes for ONE order, and never talks to a broker. Refuses
  "yes to all", "sure", "ok", a yes that names a different stock, and any
  order bazaar-risk did not PASS today. Use when the user says "place it",
  "send the order", "yes", or after /bazaar-risk PASS.
argument-hint: "[show | approve --index N --reply yes | decline]"
---

# bazaar-broker

The Order Executor is the last human gate. This tool never talks to a broker
and never places anything. Paper is the only mode. This is not financial
advice.

`${CLAUDE_SKILL_DIR}` is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/ticket.py" show --now "2026-10-19 10:20"
python3 "${CLAUDE_SKILL_DIR}/ticket.py" approve --index 1 --reply "yes"
python3 "${CLAUDE_SKILL_DIR}/ticket.py" decline --index 1
```

A ticket is READY only if bazaar-risk passed THIS exact fingerprint today and
nobody has decided on it yet. `approve` records your reply word for word in
`trader/state/broker.json`. Status is `approved` (paper log), not `placed`.
To actually paper-fill, a human uses their broker's paper UI; this skill
does not call it.

Yes rules, same as the US pack:

- the reply must start with "yes"
- one order, not a batch
- no doubt words (maybe, later, unless)
- if you name a qty or price it must match the ticket

## Safety

This is not financial advice. Typing yes still does not send a live order.
`--demo` is not live. Do not send the ticket to a live account.

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
