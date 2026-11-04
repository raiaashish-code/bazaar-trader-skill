---
name: bazaar-news
description: >-
  News Monitor for NSE names. Tracks corporate announcements and headlines
  on every stock you watch and flags what moves it: results, dividends,
  bulk/block, SEBI, board meetings. Reads NSE announcement JSON or RSS
  offline files, tags in IST, writes trader/news.json. Use when the user
  says "what's the news", "any filings", "board meeting", "results today",
  "why is this up", or after /bazaar-scanner before /bazaar-entry.
argument-hint: "[--offline FILE] [--hours 48]"
---

# bazaar-news

The News Monitor is the second step of a day trade. It lists what was said
about the names on your watchlist. It does not predict a move. A headline is
not a reason to buy.

The US pack reads Yahoo RSS and SEC 8-K Atom. India has no EDGAR 8-K. This
skill reads:

- NSE corporate announcements JSON (`symbol`, `desc` / `subject`, `an_dt`)
- optional RSS (Moneycontrol / exchange feed saved offline)

`${CLAUDE_SKILL_DIR}` is this skill's folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/news.py" --watchlist trader/watchlist.json --offline nse.json
python3 "${CLAUDE_SKILL_DIR}/news.py" --offline headlines.xml --now "2026-10-19 10:15"
```

## What it reads and writes

| file | what |
| --- | --- |
| `trader/watchlist.json` | symbols from bazaar-scanner |
| `trader/news.json` | tagged items, IST timestamps |
| `trader/state/news.json` | seen ids so a rerun is quiet |

## Tags

earnings, dividend, deal, block, regulatory, guidance, board.

A results announcement scheduled after 15:30 IST is not a reason to stay in a
day trade; you are supposed to be flat by 15:15. A trading halt or SEBI order
is.

## Safety

This is not financial advice. News does not place an order. Empty
announcement files stay empty; the tool does not invent a filing. Prefer
`--offline` in this environment. After news, still run bazaar-entry through
bazaar-broker and type yes for one paper ticket only.

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
