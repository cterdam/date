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
_TIANGAN_IDX = {t: i for i, t in enumerate(_TIANGAN)}
_DIZHI_IDX = {z: i for i, z in enumerate(_DIZHI)}


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


# -- seeks -------------------------------------------------------------------
#
# X_seek(j, sign, vs) is the first day >= j whose value satisfies the atom
# (in vs when sign, out of vs when not). Where a value has a closed form in
# the day — the periodic axes and the civil fields — the engine jumps
# straight to the answer instead of stepping spans. _clean guarantees every
# atom is satisfiable within the codomain (a positive atom is nonempty, a
# negative one never covers everything), so a seek always lands.


def _seek_residue(j: int, good, mod: int) -> int:
    for off in range(mod):
        if (j + off) % mod in good:
            return j + off
    raise AssertionError("unsatisfiable modular atom escaped _clean")


def weekday_seek(j: int, sign: bool, vs) -> int:
    good = {int(v) - 1 for v in vs}  # weekday(j) = j % 7 + 1
    if not sign:
        good = set(range(7)) - good
    return _seek_residue(j, good, 7)


def cn_day_tiangan_seek(j: int, sign: bool, vs) -> int:
    # stem index is (j + PILLAR_K) % 10, so day residues shift by PILLAR_K
    good = {(_TIANGAN_IDX[v] - PILLAR_K) % 10 for v in vs}
    if not sign:
        good = set(range(10)) - good
    return _seek_residue(j, good, 10)


def cn_day_dizhi_seek(j: int, sign: bool, vs) -> int:
    good = {(_DIZHI_IDX[v] - PILLAR_K) % 12 for v in vs}
    if not sign:
        good = set(range(12)) - good
    return _seek_residue(j, good, 12)


def month_seek(j: int, sign: bool, vs) -> int:
    y, m, _ = jdn2civil(j)
    ms = {int(v) for v in vs}
    if (m in ms) == sign:
        return j
    while True:
        m += 1
        if m == 13:
            y, m = y + 1, 1
        if (m in ms) == sign:
            return civil2jdn(y, m, 1)


def day_seek(j: int, sign: bool, vs) -> int:
    y, m, d = jdn2civil(j)
    if sign:
        vals = sorted(vs)
        while True:
            dim = days_in_month(y, m)
            for v in vals:
                if d <= v <= dim:
                    return civil2jdn(y, m, v)
            y, m, d = (y + 1, 1, 1) if m == 12 else (y, m + 1, 1)
    while True:
        dim = days_in_month(y, m)
        while d <= dim:
            if d not in vs:
                return civil2jdn(y, m, d)
            d += 1
        y, m, d = (y + 1, 1, 1) if m == 12 else (y, m + 1, 1)


def doy_seek(j: int, sign: bool, vs) -> int:
    y = jdn2civil(j)[0]
    start = civil2jdn(y, 1, 1)
    cur = j - start + 1
    if sign:
        vals = sorted(vs)
        while True:
            n = 365 + is_leap(y)
            for v in vals:
                if cur <= v <= n:
                    return start + v - 1
            y += 1
            start, cur = civil2jdn(y, 1, 1), 1
    while True:
        n = 365 + is_leap(y)
        while cur <= n:
            if cur not in vs:
                return start + cur - 1
            cur += 1
        y += 1
        start, cur = civil2jdn(y, 1, 1), 1


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
