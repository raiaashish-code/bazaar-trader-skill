import datetime
import json
import os
import tempfile
import unittest

from _load import FIX, ROOT, load

scan = load("bazaar-scanner", "scan")
entry = load("bazaar-entry", "entry")
exitp = load("bazaar-exit", "exit")
tm = load("bazaar-timemachine", "timemachine")
size = load("bazaar-budget", "size")
risk = load("bazaar-risk", "check")
ticket = load("bazaar-broker", "ticket")
alerts = load("bazaar-alerts", "alerts")
news = load("bazaar-news", "news")
facts = load("bazaar-analyst", "facts")
deals = load("bazaar-smartmoney", "deals")


def tmpdir():
    return tempfile.TemporaryDirectory()


class Scanner(unittest.TestCase):
    def test_universe_keeps_eq_drops_etf(self):
        text = open(os.path.join(FIX, "bhav.csv"), encoding="utf-8").read()
        kept, counts = scan.build_universe(text)
        names = [s for s, _n in kept]
        self.assertIn("RELIANCE", names)
        self.assertIn("TCS", names)
        self.assertNotIn("NIFTYBEES", names)
        self.assertNotIn("BOND", names)
        self.assertNotIn("SMEME", names)

    def test_daily_breakout(self):
        data = json.load(open(os.path.join(FIX, "daily.json"), encoding="utf-8"))
        now = scan.parse_now("2026-10-19 08:30")
        hits, counts, last = scan.scan_daily(data, ["RELIANCE", "THIN"], now, 50, 100000)
        self.assertEqual(counts["illiquid"], 1)
        self.assertTrue(any(h["symbol"] == "RELIANCE" and "breakout_20d" in h["setups"] for h in hits))

    def test_orb_first_close_above_range(self):
        data = json.load(open(os.path.join(FIX, "orb_reliance.json"), encoding="utf-8"))
        day = datetime.date(2026, 10, 19)
        cutoff = datetime.datetime(2026, 10, 19, 10, 15)
        bars = scan.session_bars(data["RELIANCE"], day, cutoff)
        self.assertTrue(scan.usable(bars, day, cutoff, 3))
        hit = scan.orb_hit(bars, 3)
        self.assertIsNotNone(hit)
        self.assertGreater(hit["price"], hit["or_high"])

    def test_cli_orb(self):
        rc = scan.main(["orb", "--offline", os.path.join(FIX, "orb_reliance.json"),
                        "--now", "2026-10-19 10:15", "--no-write", "--min-price", "0",
                        "--min-volume", "0"])
        self.assertEqual(rc, 0)


class Entry(unittest.TestCase):
    def test_trigger_after_range(self):
        chart = json.load(open(os.path.join(FIX, "entry_reliance.json"), encoding="utf-8"))
        res = entry.evaluate(chart, entry.parse_now("2026-10-19 10:15"), setup="orb")
        self.assertEqual(res["status"], "triggered")
        self.assertIn("first print", res["trigger"]["honest_note"])

    def test_forming_range_waits(self):
        chart = json.load(open(os.path.join(FIX, "entry_reliance.json"), encoding="utf-8"))
        res = entry.evaluate(chart, entry.parse_now("2026-10-19 09:20"), setup="orb")
        self.assertEqual(res["status"], "waiting")
        self.assertEqual(res["phase"], "forming")


class Exit(unittest.TestCase):
    def test_or_mid_1r(self):
        plan = exitp.compute(1405, "or_mid", None, "r", exitp.D("1"), or_high=1410, or_low=1390)
        self.assertEqual(plan["stop"], 1400.0)
        self.assertEqual(plan["target"], 1410.0)
        self.assertEqual(plan["reward_risk"], 1.0)
        self.assertEqual(plan["flat_by"], "15:15")

    def test_tight_stop_refused(self):
        with self.assertRaises(exitp.PlanError):
            exitp.compute(1405, "price", exitp.D("1404.99"), "r", exitp.D("1"))


class TimeMachine(unittest.TestCase):
    def test_same_bar_counts_stop(self):
        pool = {i: [(1, 1.05, 0.95, 1.0)] for i in range(75)}
        mc = tm.simulate(pool, 100, 99, 101, 3, 10, replays=50, seed=19, window=0)
        self.assertEqual(mc["p_stop"], 1.0)
        self.assertIn("stop", mc["note"])

    def test_history_replay(self):
        raw = json.load(open(os.path.join(FIX, "sessions.json"), encoding="utf-8"))
        hist = tm.history_replay(raw["sessions"], last=5)
        self.assertEqual(hist["triggered"], 1)
        self.assertEqual(hist["trades"][0]["outcome"], "target")


class Budget(unittest.TestCase):
    def test_reel_style_size(self):
        plan = {"symbol": "RELIANCE", "entry": 1405, "stop": 1400, "target": 1415, "date": "2026-10-19", "side": "buy"}
        cfg = json.load(open(os.path.join(ROOT, "bazaar-budget", "config.example.json")))
        s = size.size_trade(plan, cfg, budget=50000, today="2026-10-19")
        self.assertGreater(s["qty"], 0)
        self.assertLessEqual(s["max_loss"], 500.01)
        self.assertGreater(s["max_loss_with_charges"], s["max_loss"])
        self.assertTrue(s["paper"])
        order = size.bracket_order(s)
        self.assertEqual(order["broker"], "paper")
        self.assertEqual(order["product"], "INTRADAY")

    def test_refuses_live(self):
        plan = {"symbol": "RELIANCE", "entry": 1405, "stop": 1400, "target": 1415, "side": "buy"}
        with self.assertRaises(size.SizeError):
            size.size_trade(plan, {"paper": False, "budget": 50000})


class Risk(unittest.TestCase):
    def _order(self, **over):
        o = {"symbol": "RELIANCE", "side": "buy", "qty": "20", "type": "market",
             "time_in_force": "day", "product": "INTRADAY", "exchange": "NSE",
             "order_class": "bracket", "take_profit_limit_price": "1415.00",
             "stop_loss_stop_price": "1400.00", "broker": "paper", "paper": True,
             "plan": {"entry": 1405, "stop": 1400, "target": 1415, "max_loss": 140}}
        o.update(over)
        return o

    def test_pass_in_window(self):
        cfg = json.load(open(os.path.join(ROOT, "bazaar-budget", "config.example.json")))
        res = risk.check([self._order()], cfg, now=risk.parse_now("2026-10-19 10:20"))
        self.assertEqual(res["results"][0]["verdict"], "PASS")

    def test_block_dead_zone(self):
        cfg = json.load(open(os.path.join(ROOT, "bazaar-budget", "config.example.json")))
        res = risk.check([self._order()], cfg, now=risk.parse_now("2026-10-19 12:00"))
        self.assertEqual(res["results"][0]["verdict"], "BLOCK")
        self.assertTrue(any("dead zone" in r for r in res["results"][0]["reasons"]))

    def test_reliance_is_not_an_option_symbol(self):
        cfg = json.load(open(os.path.join(ROOT, "bazaar-budget", "config.example.json")))
        opt = self._order()
        opt["symbol"] = "NIFTY25OCT24000CE"
        res = risk.check([opt], cfg, now=risk.parse_now("2026-10-19 10:20"))
        self.assertEqual(res["results"][0]["verdict"], "BLOCK")
        cash = self._order()
        res = risk.check([cash], cfg, now=risk.parse_now("2026-10-19 10:20"))
        self.assertEqual(res["results"][0]["verdict"], "PASS")

    def test_block_live(self):
        cfg = {"paper": False, "live_trading": True, "budget": 50000, "max_loss_per_trade_inr": 500}
        res = risk.check([self._order()], cfg, now=risk.parse_now("2026-10-19 10:20"))
        self.assertEqual(res["results"][0]["verdict"], "BLOCK")


class Broker(unittest.TestCase):
    def test_yes_rules(self):
        order = {"symbol": "RELIANCE", "qty": "20", "side": "buy",
                 "stop_loss_stop_price": "1400.00", "take_profit_limit_price": "1415.00",
                 "plan": {"max_loss": 140}}
        self.assertTrue(ticket.parse_yes("yes", order)[0])
        self.assertFalse(ticket.parse_yes("sure", order)[0])
        self.assertFalse(ticket.parse_yes("yes to all", order)[0])
        ok, why = ticket.parse_yes("yes TCS", order, batch_symbols=["TCS"])
        self.assertFalse(ok, why)

    def test_fingerprint_stable(self):
        o = {"symbol": "RELIANCE", "side": "buy", "qty": "20", "type": "market"}
        self.assertEqual(ticket.fingerprint(o), ticket.fingerprint(dict(o)))


class Alerts(unittest.TestCase):
    def test_opening_bell(self):
        st = alerts.clock_status(alerts.parse_now("2026-10-19 09:14"))
        self.assertFalse(st["open"])
        st = alerts.clock_status(alerts.parse_now("2026-10-19 09:16"))
        self.assertTrue(st["open"])
        hit = alerts.eval_rule({"id": "nse-open", "type": "opening_bell"}, {},
                               alerts.to_ist(alerts.parse_now("2026-10-19 09:16")), set())
        self.assertIsNotNone(hit)

    def test_stop_alert(self):
        hit = alerts.eval_rule({"id": "r-stop", "type": "stop", "symbol": "RELIANCE", "price": 1400},
                               {"RELIANCE": 1399}, alerts.to_ist(alerts.parse_now("2026-10-19 11:00")), set())
        self.assertIn("below", hit["message"])


class News(unittest.TestCase):
    def test_nse_tags(self):
        raw = open(os.path.join(FIX, "nse_announcements.json"), encoding="utf-8").read()
        items = news.parse_nse_announcements(raw, "RELIANCE")
        items = news.tag(items, {"RELIANCE": "Reliance", "TCS": "TCS"})
        tags = {it["ticker"]: it["tags"] for it in items}
        self.assertIn("earnings", tags["RELIANCE"])
        self.assertIn("dividend", tags["RELIANCE"])
        self.assertIn("regulatory", tags["TCS"])


class Analyst(unittest.TestCase):
    def test_yoy_and_ttm(self):
        raw = json.load(open(os.path.join(FIX, "bazaar-analyst", "RELIANCE.json"), encoding="utf-8"))
        laid = facts.layout_quarters(raw["periods"])
        q2 = [q for q in laid if q["period"] == "2026-Q2"][0]
        self.assertEqual(q2["yoy_revenue_pct"], 25.0)
        summary = facts.summarise(laid, n=4)
        self.assertGreater(summary["ttm_revenue"], 0)
        self.assertIn("Not a buy", summary["note"])


class SmartMoney(unittest.TestCase):
    def test_bulk_and_fii(self):
        rows = deals.parse_deals(open(os.path.join(FIX, "bulk.csv"), encoding="utf-8").read())
        self.assertEqual(rows[0]["symbol"], "RELIANCE")
        self.assertEqual(rows[0]["side"], "BUY")
        fii = deals.parse_fii_dii(open(os.path.join(FIX, "fii.json"), encoding="utf-8").read())
        self.assertEqual(len(fii), 2)
        empty = deals.parse_fii_dii({"data": [{"category": "FII"}]})
        self.assertEqual(empty, [])


class Pipeline(unittest.TestCase):
    def test_scanner_to_broker_paper_yes(self):
        plan = exitp.compute(1405, "or_mid", None, "r", exitp.D("1"), or_high=1410, or_low=1390)
        plan.update(symbol="RELIANCE", date="2026-10-19", side="buy", setup="orb")
        cfg = json.load(open(os.path.join(ROOT, "bazaar-budget", "config.example.json")))
        sized = size.size_trade(plan, cfg, today="2026-10-19")
        order = size.bracket_order(sized)
        res = risk.check([order], cfg, now=risk.parse_now("2026-10-19 10:20"))
        self.assertEqual(res["results"][0]["verdict"], "PASS")
        fp = ticket.fingerprint(order)
        self.assertEqual(fp, res["results"][0]["fingerprint"])
        ready, label, _ = ticket.status_of(order, res, {"orders": []}, "2026-10-19")
        self.assertTrue(ready, label)
        ok, why = ticket.parse_yes("yes", order)
        self.assertTrue(ok, why)


if __name__ == "__main__":
    unittest.main()
