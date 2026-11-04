# The Bazaar Trader skill

11 Claude skills for day trading on NSE and BSE: scan EQ charts, track
breaking NSE announcements, time every entry and exit in IST, and replay
every outcome with honest fills before you risk a rupee.

**Anyone can use this repo.** You do not need a broker account, an API key,
or a paid data feed. Clone it, run the Python tools, or paste a `SKILL.md`
into Claude. Paper is the default. Nothing in this pack can place a live
order.

Free, MIT, no signup. The tools are plain Python 3.8+ with the standard
library only. Nothing to pip install.

This is the Indian-market sequel to
[Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill)
(MIT). That pack is US hours, Yahoo, SEC EDGAR, Congress PTR and Alpaca.
This pack is 09:15-15:30 IST, NSE/BSE cash and F&O names, rupees, and a
generic paper ticket.

A scan is a list of charts that match a rule, not a list of stocks to buy.
Most people who day trade lose money. Honest fills are the default: the
first print after the signal, real NSE charges, no look-ahead day type.

And no trade goes through until you say yes.

## Who this is for

- Anyone who wants an IST day-trading workflow in Claude or Claude Code.
- Students and desk people who want to replay a setup before risking cash.
- People with Zerodha, Upstox, Angel, Groww, or any other Indian paper
  account: the ticket is a plain NSE INTRADAY payload you can type in by
  hand. The pack never logs into a broker.
- People with **no** broker at all: scanner, news, entry, exit, time
  machine, budget, risk, alerts, analyst and smart money all work on
  `--offline` files in `tests/fixtures/`.

You do **not** need:

- a live trading login
- a particular broker
- Yahoo, Alpaca, or SEC keys
- this pack to sit inside some other private trading repo

## What this repo is

A public skill pack. Clone it, copy the folders, or install it as a Claude
plugin. The same Python files that Claude calls also run from a terminal.

| | |
| --- | --- |
| **License** | MIT |
| **Language** | Python 3.8+ standard library |
| **Session** | 09:15-15:30 IST, NSE holidays, Muhurat is not a day-trade session |
| **Default mode** | paper tickets; `live_trading` is false |
| **Orders** | never sent. Typed `yes` only records a local ticket |
| **Data** | `--offline` fixtures, or files you drop in yourself |

It is **not** a live bot, a broker SDK, a signal service, or a paid data
feed. It does not log in anywhere.

## What this repo contains

```
bazaar-trader-skill/
  README.md                 this file
  LICENSE                   MIT
  .claude-plugin/           plugin.json + marketplace.json for Claude Code
  lib/
    india_clock.py          09:15-15:30 IST, holidays, dead zone 11:15-13:15
    honest.py               first print after the signal, slippage, NSE charges
    io_util.py              JSON helpers and rupee formatting
  bazaar-scanner/           Chart Scanner
  bazaar-news/              News Monitor
  bazaar-entry/             Entry Timer
  bazaar-exit/              Exit Planner
  bazaar-timemachine/       Time Machine
  bazaar-risk/              Risk Manager
  bazaar-budget/            Budget Manager + config.example.json
  bazaar-broker/            Order Executor (paper ticket)
  bazaar-alerts/            Price Alerts
  bazaar-analyst/           Results Analyst
  bazaar-smartmoney/        bulk/block + FII-DII
  tests/
    fixtures/               bhavcopy, bars, announcements, bulk deals, FII-DII
    test_*.py               offline unit tests
```

Each `bazaar-*` folder is one Claude skill: a `SKILL.md` plus a `.py` tool.

Working files the tools write (not in git) land in a `trader/` folder in
**your** project: `watchlist.json`, `plan.json`, `orders.json`, `risk.json`,
`state/broker.json`. That folder is local to you.

## Prerequisites

- Python 3.8 or newer (`python3 --version`)
- Optional: [Claude](https://claude.ai) or [Claude Code](https://docs.claude.com/en/docs/claude-code)
  if you want `/bazaar-scanner` as a chat command
- Optional: any Indian paper account if you later type the ticket in by hand

No pip packages. No API keys. No paid feed.

## Install

Paste this into Claude:

```
https://github.com/raiaashish-code/bazaar-trader-skill

install skill
```

Or as a plugin, in Claude Code:

```
/plugin marketplace add raiaashish-code/bazaar-trader-skill
/plugin install bazaar-trader-skill@bazaar-trader-skill
```

Claude Code namespaces plugin skills, so they show up as
`/bazaar-trader-skill:bazaar-scanner` and so on. Copy the folders instead
if you want plain `/bazaar-scanner`:

```bash
git clone https://github.com/raiaashish-code/bazaar-trader-skill.git
cd bazaar-trader-skill
python3 -m unittest discover -s tests
cp -r bazaar-* ~/.claude/skills/
```

Project-local instead of global: copy the same folders into your repo's
`.claude/skills/`. No Claude Code at all? Paste any single `SKILL.md` at the
top of a chat, or skip Claude and run the Python tools below.

Every command accepts `--offline` so a scan, a replay and a paper ticket
work with no network.

## Quick start (terminal, no Claude)

From a clone, with only the fixtures in this repo:

```bash
python3 bazaar-scanner/scan.py universe --offline tests/fixtures/bhav.csv
python3 bazaar-scanner/scan.py orb --offline tests/fixtures/orb_reliance.json --now "2026-10-19 10:15"
python3 bazaar-entry/entry.py RELIANCE --offline tests/fixtures/entry_reliance.json --now "2026-10-19 10:15"
python3 bazaar-exit/exit.py --symbol RELIANCE --entry 1418 --or-high 1405 --or-low 1388 --stop or-mid --target 1R
python3 bazaar-news/news.py --offline tests/fixtures/nse_announcements.json --now "2026-10-19 10:15"
python3 bazaar-smartmoney/deals.py bulk --offline tests/fixtures/bulk.csv
python3 bazaar-broker/ticket.py show --now "2026-10-19 10:20"
python3 -m unittest discover -s tests
```

`--now` is IST. The example dates are a Monday fixture so the holiday
calendar does not block the replay. `ticket.py show` prints a local hint
until `trader/orders.json` exists (after the pipeline). It still does not
call a broker.

## The eleven

| command | job | what it does |
| --- | --- | --- |
| `/bazaar-scanner` | Chart Scanner | NSE EQ bhavcopy universe, daily setups, 09:15 IST opening-range breakout. |
| `/bazaar-news` | News Monitor | NSE corporate announcements, tagged in IST. |
| `/bazaar-entry` | Entry Timer | First completed bar that closes beyond the range. Forming bars wait. |
| `/bazaar-exit` | Exit Planner | Stop and target in rupees, flat by 15:15 IST. |
| `/bazaar-timemachine` | Time Machine | 10,000 IST-session replays plus every past day the same ORB fired. |
| `/bazaar-risk` | Risk Manager | One slot, skip 11:15-13:15, paper only, PASS or BLOCK. |
| `/bazaar-budget` | Budget Manager | Size in INR, whole shares or F&O lots, charges in the max-loss picture. |
| `/bazaar-broker` | Order Executor | Generic paper ticket. Typed yes only. Never sends the order. |
| `/bazaar-alerts` | Price Alerts | Stop, target, 15:15 flatten, NSE opening bell at 09:15 IST. |
| `/bazaar-analyst` | Results Analyst | NSE/BSE quarterly numbers. Never a buy call. |
| `/bazaar-smartmoney` | Smart money | NSE bulk/block deals and FII-DII cash. There is no Indian Pelosi feed. |

## How to use it

Everything lands in a `trader/` folder, and each skill reads what the last one
wrote:

```
scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker   (one trade)
alerts: stop, target, flat by 15:15 IST                                        (while it is open)
news / analyst / smartmoney                                                    (on a schedule)
```

An example, RELIANCE on a Tuesday, IST, using the fixtures in this repo:

1. `/bazaar-scanner` `orb --now "2026-10-20 10:15"` after 09:30 IST: charts
   that have closed above the 09:15-09:30 range.
2. `/bazaar-news`: morning NSE announcements. A results note after the close
   is not a day-trade event; a halt is.
3. `/bazaar-entry` waits for the first completed 5-minute close above the
   range. The 10:10 bar still forming is waiting. The 10:15 close is
   triggered. The fill is not that close.
4. `/bazaar-exit` sets stop at the range midpoint, target 1R, flat by 15:15.
5. `/bazaar-timemachine` replays the rest of the session 10,000 times. A coin
   flip is a valid answer. Skip it.
6. `/bazaar-budget` with a Rs 50,000 paper account and a Rs 500 max loss
   sizes whole shares, charges included.
7. `/bazaar-risk` checks the IST window, one-slot cap, dead zone, stop,
   reward:risk, cash. PASS or BLOCK.
8. `/bazaar-broker` shows the ticket. You type `yes`. The pack records
   approval. It still does not call a broker.
9. `/bazaar-alerts` rings on the stop, the target and at 15:15 IST.

## The tools

All standard-library Python. Times without a zone are IST.

```bash
python3 bazaar-scanner/scan.py universe --offline tests/fixtures/bhav.csv
python3 bazaar-scanner/scan.py daily --offline tests/fixtures/daily.json --now "2026-10-19 08:30"
python3 bazaar-scanner/scan.py orb --offline tests/fixtures/orb_reliance.json --now "2026-10-19 10:15"
python3 bazaar-news/news.py --offline tests/fixtures/nse_announcements.json --now "2026-10-19 10:15"
python3 bazaar-entry/entry.py RELIANCE --offline tests/fixtures/entry_reliance.json --now "2026-10-19 10:15"
python3 bazaar-exit/exit.py --symbol RELIANCE --entry 1418 --or-high 1405 --or-low 1388 --stop or-mid --target 1R
python3 bazaar-timemachine/timemachine.py --plan trader/plan.json --offline tests/fixtures/sessions.json
python3 bazaar-budget/size.py --plan trader/plan.json --config bazaar-budget/config.example.json
python3 bazaar-risk/check.py --orders trader/orders.json --config bazaar-budget/config.example.json --now "2026-10-19 10:20"
python3 bazaar-broker/ticket.py show --now "2026-10-19 10:20"
python3 bazaar-alerts/alerts.py clock --now "2026-10-19 09:16"
python3 bazaar-analyst/facts.py RELIANCE --offline tests/fixtures/bazaar-analyst/RELIANCE.json
python3 bazaar-smartmoney/deals.py bulk --offline tests/fixtures/bulk.csv
```

```bash
python3 -m unittest discover -s tests
```

The tests run offline on the fixtures. They check IST clocks, honest fills,
ORB math, rupee sizing, the paper yes-gate, bulk/block parsing, and that
the pack does not name a live broker.

## Fixtures and your own data

`tests/fixtures/` is enough to run every tool with `--offline`:

| file | used by |
| --- | --- |
| `bhav.csv` | scanner universe (EQ series only) |
| `daily.json` | daily setups |
| `orb_reliance.json` | 09:15-09:30 opening range plus later bars |
| `entry_reliance.json` | first completed close beyond the range |
| `nse_announcements.json` | news |
| `sessions.json` | time machine |
| `bulk.csv` | smart money bulk/block |
| `fii.json` | FII-DII cash; empty stays empty |
| `bazaar-analyst/RELIANCE.json` | quarterly facts, never a buy call |

Point `--offline` at your own files in the same shapes. Live NSE pages are
unofficial and rate-limited; prefer files you already have.

## Paper tickets (not a live broker)

`bazaar-broker` never talks to a broker API. After risk PASS it prints a
ticket like: BUY 14 RELIANCE, market, INTRADAY NSE paper, stop, target.
You type `yes` for that one order. The pack writes `trader/state/broker.json`.
If you later want a fill, you type the same ticket into **your** paper UI
(any Indian broker). `ok`, `sure`, and `yes to all` are refused.

`"broker": "paper"` and `"live_trading": false` in
`bazaar-budget/config.example.json` are required. Change them to live and
risk BLOCKS the order.

Copy that example to `trader/config.json` and edit rupee limits only:

| key | example | meaning |
| --- | --- | --- |
| `budget` | 50000 | paper account in INR |
| `max_loss_per_trade_inr` | 500 | one-trade cap |
| `max_daily_loss_inr` | 1500 | day cap |
| `max_trades_per_day` / `max_open_positions` | 1 | one slot |
| `skip_dead_zone` | true | skip 11:15-13:15 IST |
| `day_type_ready` | 10:31 | no day-type label before this |
| `flat_by` | 15:15 | flatten before the close |
| `broker` / `paper` / `live_trading` | paper / true / false | leave these |

## US to India map

| Day Trader (US) | Bazaar Trader (India) |
| --- | --- |
| 09:30-16:00 ET | 09:15-15:30 IST |
| NYSE holidays | NSE holidays (Muhurat is not a day-trade session) |
| Nasdaq Trader symbol directories | NSE CM bhavcopy EQ series |
| Yahoo spark / v8 | `--offline` bhavcopy and bar JSON |
| SEC 8-K / EDGAR | NSE corporate announcements / quarterly results |
| House Clerk PTR (Pelosi) | NSE bulk deals, block deals, FII-DII cash |
| Alpaca paper | generic paper ticket, never auto-sent |
| `$` | `Rs` |
| Day type / regime labels | only after 10:31 IST |

## Honest fills

The fill is the first print strictly after the signal, plus 0.15% equity
slippage (0.5 premium points on index options). A stop fills at the traded
extreme of the bar, not at the theoretical stop. Charges are NSE statutory
intraday rates plus a typical Rs 20/order discount brokerage, in
`lib/honest.py`, not a flat Rs 100. A 10:30 day-type label must not be used
on a 09:15 or 10:00 bar.

`--demo` is not live. Empty FII/OI stays empty: the tools do not invent a
figure when the file has none.

## Safety

This is not financial advice. These tools do not place live orders. Paper is
the default and the only mode. A yes covers one ticket. "yes to all" is
refused. Most people who day trade lose money. The Time Machine is a
simulation from past bars, not a prediction. A stop is a plan, not a
guarantee: in a fast market it can fill worse than the price on the ticket.

## Fine print

Original method, calendar ideas and skill split: Jake Schincariol, MIT.
Indian clocks, bhavcopy universe, paper tickets, bulk/block stand-in and
honest-fill rules: this repository. NSE endpoints are unofficial or
rate-limited; prefer `--offline` fixtures.

Homepage: https://github.com/raiaashish-code/bazaar-trader-skill
