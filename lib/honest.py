"""Honest fills for Indian equity and NIFTY options.

Same-minute last print is not a fill. The fill is the first print strictly
after the signal, plus slippage, with the stop at the traded extreme and
full NSE charges. Day type from 10:30 IST is not used on earlier bars.
"""

from .india_clock import DAY_TYPE_READY


EQUITY_SLIP_PCT = 0.15          # 0.15% adverse, the light honest equity slip
OPTION_SLIP_PT = 0.50           # 0.5 premium points
TICK = 0.05

# Equity intraday (NSE), published NSE statutory rates plus a typical Rs 20/order discount-brokerage.
EQUITY_BROKERAGE = 20.0
NSE_EQUITY_TXN_RATE = 0.0000297
SEBI_EQUITY_TURNOVER_RATE = 0.0000001
STT_EQUITY_INTRADAY_SELL_RATE = 0.00025
STAMP_DUTY_EQUITY_INTRADAY_BUY_RATE = 0.00003
GST_RATE = 0.18

# NIFTY options.
OPTION_BROKERAGE = 20.0
NSE_OPTION_TXN_RATE = 0.0003552
NSE_IPFT_RATE = 0.0000001
SEBI_TURNOVER_RATE = 0.0000001
STT_OPTION_SELL_RATE = 0.0015
STAMP_DUTY_OPTION_BUY_RATE = 0.00003


def first_print_after(prints, signal_ts):
    """prints: iterable of (ts, price) sorted or not. ts must be strictly after signal_ts."""
    later = [(t, p) for t, p in prints if t > signal_ts and p is not None]
    if not later:
        return None
    later.sort(key=lambda x: x[0])
    return later[0]


def buy_fill_equity(price, slip_pct=EQUITY_SLIP_PCT):
    return round(float(price) * (1.0 + slip_pct / 100.0), 2)


def sell_fill_equity(price, slip_pct=EQUITY_SLIP_PCT):
    return round(float(price) * (1.0 - slip_pct / 100.0), 2)


def buy_fill_option(price, slip_pt=OPTION_SLIP_PT):
    return round(float(price) + slip_pt, 2)


def sell_fill_option(price, slip_pt=OPTION_SLIP_PT):
    return round(max(TICK, float(price) - slip_pt), 2)


def stop_fill_long(bar_low, theoretical_stop):
    """A long stop fills at the worse of the stop and the bar's traded low."""
    return min(float(bar_low), float(theoretical_stop))


def stop_fill_short(bar_high, theoretical_stop):
    return max(float(bar_high), float(theoretical_stop))


def may_use_day_type(signal_time):
    """False until 10:31 IST. classify_day at 10:30 must not label 09:15 or 10:00 trades."""
    t = signal_time
    if hasattr(t, "time"):
        t = t.time()
    return t >= DAY_TYPE_READY


def equity_charges(entry_price, exit_price, qty):
    buy_turnover = max(float(entry_price), 0.0) * qty
    sell_turnover = max(float(exit_price), 0.0) * qty
    total = buy_turnover + sell_turnover
    brokerage = EQUITY_BROKERAGE * 2
    exchange_txn = total * NSE_EQUITY_TXN_RATE
    sebi_fee = total * SEBI_EQUITY_TURNOVER_RATE
    stt = sell_turnover * STT_EQUITY_INTRADAY_SELL_RATE
    stamp = buy_turnover * STAMP_DUTY_EQUITY_INTRADAY_BUY_RATE
    gst = (brokerage + exchange_txn + sebi_fee) * GST_RATE
    total_charges = brokerage + exchange_txn + sebi_fee + stt + stamp + gst
    return {"brokerage": round(brokerage, 2), "exchange_txn": round(exchange_txn, 2),
            "sebi_fee": round(sebi_fee, 4), "stt": round(stt, 2), "stamp_duty": round(stamp, 2),
            "gst": round(gst, 2), "total_charges": round(total_charges, 2)}


def option_charges(entry_price, exit_price, qty):
    buy_turnover = max(float(entry_price), 0.0) * qty
    sell_turnover = max(float(exit_price), 0.0) * qty
    total = buy_turnover + sell_turnover
    brokerage = OPTION_BROKERAGE * 2
    exchange_txn = total * NSE_OPTION_TXN_RATE
    sebi_fee = total * SEBI_TURNOVER_RATE
    ipft = total * NSE_IPFT_RATE
    stt = sell_turnover * STT_OPTION_SELL_RATE
    stamp = buy_turnover * STAMP_DUTY_OPTION_BUY_RATE
    gst = (brokerage + exchange_txn + sebi_fee + ipft) * GST_RATE
    total_charges = brokerage + exchange_txn + sebi_fee + ipft + stt + stamp + gst
    return {"brokerage": round(brokerage, 2), "exchange_txn": round(exchange_txn, 2),
            "sebi_fee": round(sebi_fee, 4), "ipft": round(ipft, 4), "stt": round(stt, 2),
            "stamp_duty": round(stamp, 2), "gst": round(gst, 2),
            "total_charges": round(total_charges, 2)}


def net_equity(entry, exit_, qty, side="buy"):
    charges = equity_charges(entry, exit_, qty)
    if side == "buy":
        gross = (exit_ - entry) * qty
    else:
        gross = (entry - exit_) * qty
    return round(gross - charges["total_charges"], 2), charges
