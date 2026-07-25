"""The arithmetic calendar layer: exact, closed-form, in-house.

Civil (proleptic Gregorian, astronomical year numbering) ↔ JDN conversions
after Howard Hinnant's era-based algorithms, plus each arithmetic axis's
evaluator (jdn2X: day → value) and its span end (the first day the value
changes — every evaluator is a step function of the day, and the engine
jumps between those boundaries rather than stepping days).

The sexagenary day anchor: 1949-10-01 was a 甲子 day (index 0), giving
``index(j) = (j + 49) % 60`` — cross-checked against sxtwl at development
time and pinned by golden tests.
"""

from __future__ import annotations

from .values import Dizhi, Month, Tiangan, Weekday, Zodiac

GREGORIAN_PERIOD = 146_097  # days per 400 Gregorian years; divisible by 7
PILLAR_K = 49  # (jdn + 49) % 60 is the sexagenary day index, 0 = 甲子

_JDN_UNIX = 2_440_588  # JDN of 1970-01-01

_TIANGAN = tuple(Tiangan)
_DIZHI = tuple(Dizhi)


# -- civil ↔ jdn -----------------------------------------------------------


def civil2jdn(y: int, m: int, d: int) -> int:
    """JDN of a proleptic-Gregorian date (astronomical year numbering)."""
    y -= m <= 2
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m + (9 if m <= 2 else -3)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146_097 + doe - 719_468 + _JDN_UNIX


def jdn2civil(j: int) -> tuple[int, int, int]:
    """(year, month, day) of a JDN, proleptic Gregorian."""
    z = j - _JDN_UNIX + 719_468
    era = z // 146_097
    doe = z - era * 146_097
    yoe = (doe - doe // 1460 + doe // 36_524 - doe // 146_096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    return y + (m <= 2), m, d


def is_leap(y: int) -> bool:
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def days_in_month(y: int, m: int) -> int:
    if m == 2:
        return 29 if is_leap(y) else 28
    return 31 if m in (1, 3, 5, 7, 8, 10, 12) else 30


def iso_weeks_in(y: int) -> int:
    """Number of ISO weeks (52 or 53) in ISO year `y`."""
    wd_jan1 = civil2jdn(y, 1, 1) % 7 + 1
    return 53 if wd_jan1 == 4 or (is_leap(y) and wd_jan1 == 3) else 52


def pillar_index_of(j: int) -> int:
    return (j + PILLAR_K) % 60


# Sign start dates (month, day): each sign runs from its start to the next.
_ZODIAC_STARTS = (
    (1, 20, Zodiac.AQUARIUS),
    (2, 19, Zodiac.PISCES),
    (3, 21, Zodiac.ARIES),
    (4, 20, Zodiac.TAURUS),
    (5, 21, Zodiac.GEMINI),
    (6, 21, Zodiac.CANCER),
    (7, 23, Zodiac.LEO),
    (8, 23, Zodiac.VIRGO),
    (9, 23, Zodiac.LIBRA),
    (10, 23, Zodiac.SCORPIO),
    (11, 22, Zodiac.SAGITTARIUS),
    (12, 22, Zodiac.CAPRICORN),
)


# -- jdn2X: day → value ----------------------------------------------------


def jdn2year(j: int) -> int:
    return jdn2civil(j)[0]


def jdn2month(j: int) -> Month:
    return Month(jdn2civil(j)[1])


def jdn2day(j: int) -> int:
    return jdn2civil(j)[2]


def jdn2weekday(j: int) -> Weekday:
    return Weekday(j % 7 + 1)


def jdn2doy(j: int) -> int:
    return j - civil2jdn(jdn2civil(j)[0], 1, 1) + 1


def jdn2leap(j: int) -> bool:
    return is_leap(jdn2civil(j)[0])


def jdn2week(j: int) -> tuple[int, int]:
    """(ISO year, ISO week number)."""
    y = jdn2civil(j)[0]
    w = (jdn2doy(j) - int(jdn2weekday(j)) + 10) // 7
    if w == 0:
        return y - 1, iso_weeks_in(y - 1)
    if w == 53 and iso_weeks_in(y) == 52:
        return y + 1, 1
    return y, w


def jdn2zodiac(j: int) -> Zodiac:
    _, m, d = jdn2civil(j)
    sign = Zodiac.CAPRICORN  # before Jan 20
    for mm, dd, s in _ZODIAC_STARTS:
        if (m, d) >= (mm, dd):
            sign = s
    return sign


def jdn2cn_day_tiangan(j: int) -> Tiangan:
    return _TIANGAN[pillar_index_of(j) % 10]


def jdn2cn_day_dizhi(j: int) -> Dizhi:
    return _DIZHI[pillar_index_of(j) % 12]


# -- span ends --------------------------------------------------------------
#
# Every jdn2X is a step function: constant over spans of days. X_span_end(j)
# is the first day after j where the value changes — the boundaries the
# engine jumps between, so enumeration costs runs, never days.


def daily(j: int) -> int:
    return j + 1


def year_span_end(j: int) -> int:
    return civil2jdn(jdn2civil(j)[0] + 1, 1, 1)


def month_span_end(j: int) -> int:
    y, m, _ = jdn2civil(j)
    return civil2jdn(y, m, 1) + days_in_month(y, m)


def week_span_end(j: int) -> int:
    return j + 7 - j % 7  # the next Monday (weekday(j) = j % 7 + 1)


def zodiac_span_end(j: int) -> int:
    y, m, d = jdn2civil(j)
    for mm, dd, _ in _ZODIAC_STARTS:
        if (m, d) < (mm, dd):
            return civil2jdn(y, mm, dd)
    return civil2jdn(y + 1, 1, 20)  # inside Capricorn's wrap into January
