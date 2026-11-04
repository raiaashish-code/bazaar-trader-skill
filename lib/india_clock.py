"""NSE/BSE session clock. Always Asia/Calcutta (IST, UTC+5:30). No DST."""

import datetime
import re

IST_OFFSET = datetime.timedelta(hours=5, minutes=30)
CALENDAR_YEARS = (2026, 2027)
OPEN = datetime.time(9, 15)
CLOSE = datetime.time(15, 30)
# Equity cash square-off on this desk; F&O a few minutes later.
FLAT_BY_EQUITY = datetime.time(15, 15)
FLAT_BY_FO = datetime.time(15, 20)
# Day type from NIFTY is only known after 10:30. Do not use it before this.
DAY_TYPE_READY = datetime.time(10, 31)
DEAD_ZONE_START = datetime.time(11, 15)
DEAD_ZONE_END = datetime.time(13, 15)
NO_ENTRIES_BEFORE = datetime.time(9, 45)
NO_ENTRIES_AFTER = datetime.time(14, 30)

# NSE cash/FO holidays published for 2026-2027 (weekdays). Saturday Independence
# Day 2026 is listed so a trading_day() check matches the circular.
NSE_HOLIDAYS = {
    "2026-01-26": "Republic Day",
    "2026-03-03": "Holi",
    "2026-03-31": "Id-Ul-Fitr",
    "2026-04-03": "Good Friday",
    "2026-04-14": "Dr. Baba Saheb Ambedkar Jayanti",
    "2026-05-01": "Maharashtra Day",
    "2026-05-27": "Bakri Id",
    "2026-06-26": "Muharram",
    "2026-08-15": "Independence Day",
    "2026-09-14": "Ganesh Chaturthi",
    "2026-10-02": "Mahatma Gandhi Jayanti",
    "2026-10-20": "Dussehra",
    "2026-11-08": "Diwali Laxmi Pujan",
    "2026-11-09": "Diwali-Balipratipada",
    "2026-11-24": "Gurunanak Jayanti",
    "2026-12-25": "Christmas",
    "2027-01-26": "Republic Day",
    "2027-03-08": "Holi",
    "2027-03-22": "Ugadi / Gudi Padwa",
    "2027-03-26": "Good Friday",
    "2027-04-14": "Dr. Baba Saheb Ambedkar Jayanti",
    "2027-04-21": "Ram Navami",
    "2027-05-01": "Maharashtra Day",
    "2027-08-15": "Independence Day",
    "2027-10-02": "Mahatma Gandhi Jayanti",
    "2027-10-09": "Dussehra",
    "2027-10-29": "Diwali Laxmi Pujan",
    "2027-10-30": "Diwali-Balipratipada",
    "2027-11-14": "Gurunanak Jayanti",
    "2027-12-25": "Christmas",
}

# Special short session, not a full trading day for new day trades.
MUHURAT = {
    "2026-11-08": "Diwali Muhurat",
    "2027-10-29": "Diwali Muhurat",
}


class ClockError(Exception):
    pass


def to_ist(utc):
    return utc.replace(tzinfo=None) + IST_OFFSET


def ist_to_utc(local):
    return local - IST_OFFSET


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


def parse_now(text):
    """ISO time -> naive UTC. A time without an offset is taken as IST."""
    if not text:
        return utc_now()
    t = text.strip().replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(t)
    except ValueError:
        raise ClockError('--now wants a time like "2026-10-19 10:15" (IST) or ...Z (UTC)')
    if dt.tzinfo is None:
        return ist_to_utc(dt)
    return (dt - dt.utcoffset()).replace(tzinfo=None)


def parse_hhmm(text, flag="--at"):
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", text or "")
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise ClockError("%s wants an IST time like 10:15" % flag)
    return datetime.time(int(m.group(1)), int(m.group(2)))


def ts_to_ist(ts):
    return to_ist(datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=int(ts)))


def trading_day(d):
    """(is_trading_day, reason). Weekends and the NSE holiday list."""
    if d.weekday() >= 5:
        return False, "weekend"
    name = NSE_HOLIDAYS.get(d.isoformat())
    if name:
        if d.isoformat() in MUHURAT:
            return False, "Muhurat session only (%s); this pack does not day-trade it" % name
        return False, name
    return True, None


def session(d):
    ok, _ = trading_day(d)
    if not ok:
        return None
    return OPEN, CLOSE


def clock_label(t):
    return t.strftime("%H:%M")


def ist_iso(now_utc):
    local = to_ist(now_utc).replace(microsecond=0)
    return local.isoformat() + "+05:30"


def in_dead_zone(t):
    return DEAD_ZONE_START <= t < DEAD_ZONE_END


def day_type_known(t):
    return t >= DAY_TYPE_READY
