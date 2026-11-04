import datetime
import unittest

from lib.honest import (
    buy_fill_equity, buy_fill_option, equity_charges, first_print_after,
    may_use_day_type, option_charges, stop_fill_long,
)
from lib.india_clock import (
    CLOSE, OPEN, in_dead_zone, parse_now, to_ist, trading_day,
)


class Clock(unittest.TestCase):
    def test_ist_offset(self):
        utc = datetime.datetime(2026, 10, 19, 4, 45, 0)
        self.assertEqual(to_ist(utc).strftime("%H:%M"), "10:15")

    def test_parse_now_naive_is_ist(self):
        utc = parse_now("2026-10-19 10:15")
        self.assertEqual(to_ist(utc).strftime("%H:%M"), "10:15")

    def test_open_close(self):
        self.assertEqual(OPEN, datetime.time(9, 15))
        self.assertEqual(CLOSE, datetime.time(15, 30))

    def test_republic_day_closed(self):
        ok, why = trading_day(datetime.date(2026, 1, 26))
        self.assertFalse(ok)
        self.assertIn("Republic", why)

    def test_monday_open(self):
        ok, why = trading_day(datetime.date(2026, 10, 19))
        self.assertTrue(ok, why)

    def test_dead_zone(self):
        self.assertTrue(in_dead_zone(datetime.time(12, 0)))
        self.assertFalse(in_dead_zone(datetime.time(10, 0)))


class Honest(unittest.TestCase):
    def test_first_print_after_skips_signal_minute(self):
        signal = datetime.datetime(2026, 10, 19, 10, 15)
        prints = [
            (datetime.datetime(2026, 10, 19, 10, 15), 100.0),
            (datetime.datetime(2026, 10, 19, 10, 16), 101.5),
        ]
        hit = first_print_after(prints, signal)
        self.assertEqual(hit[1], 101.5)

    def test_day_type_not_before_1031(self):
        self.assertFalse(may_use_day_type(datetime.time(9, 15)))
        self.assertFalse(may_use_day_type(datetime.time(10, 0)))
        self.assertFalse(may_use_day_type(datetime.time(10, 30)))
        self.assertTrue(may_use_day_type(datetime.time(10, 31)))

    def test_equity_buy_fill_adds_slip(self):
        self.assertEqual(buy_fill_equity(100.0, 0.15), 100.15)

    def test_option_buy_fill_adds_half_point(self):
        self.assertEqual(buy_fill_option(50.0), 50.5)

    def test_stop_uses_traded_low(self):
        self.assertEqual(stop_fill_long(98.0, 99.0), 98.0)

    def test_charges_not_flat_100(self):
        eq = equity_charges(1400, 1390, 10)
        op = option_charges(100, 90, 65)
        self.assertNotEqual(eq["total_charges"], 100)
        self.assertNotEqual(op["total_charges"], 100)
        self.assertGreater(eq["total_charges"], 40)
        self.assertGreater(op["total_charges"], 40)


if __name__ == "__main__":
    unittest.main()
