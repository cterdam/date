"""The Chinese lunisolar calendar under the imposed modern rule.

Decrees (GB/T 33661-2017 in spirit, extrapolated proleptically):

- Instants come from astro.py (the truncated Meeus series — themselves part
  of the standard); a day is the UTC+8 civil day containing the instant.
- Months begin on new-moon days; the month containing the winter solstice
  is month 11 (十一月). When a solstice-to-solstice suì holds 13 months, the
  first after 十一月 that contains no major solar term (中氣) is the leap (閏)
  month (無中氣置閏).
- The lunar year Y runs from its 正月初一 (CNY); the year pillar changes at
  CNY, with index (Y − 4) mod 60 (1984 = 甲子年).
- The month pillar is 節氣-delimited (八字 school): it advances at each 節
  (minor term: 立春, 驚蟄, …), forming a continuous sexagenary count
  anchored at 立春 1984 = 丙寅月.
"""

from __future__ import annotations

import bisect
import functools
import math

from . import arithmetic as ar
from . import astro
from .values import CnDay, CnMonth, Dizhi, Tiangan

_TIANGAN = tuple(Tiangan)
_DIZHI = tuple(Dizhi)
_CN_MONTHS = tuple(CnMonth)
_CN_DAYS = tuple(CnDay)

_TZ = 8.0 / 24.0  # UTC+8 day slicing


def _jdn_of_jde(jde: float) -> int:
    """The UTC+8 civil day (JDN) containing a TT instant."""
    y = 2000.0 + (jde - 2451545.0) / 365.2425
    jd_ut = jde - astro.delta_t_seconds(y) / 86400.0
    return math.floor(jd_ut + _TZ + 0.5)


# -- new moons and solar terms, as civil days ------------------------------


@functools.lru_cache(maxsize=None)
def _nm_day(k: int) -> int:
    return _jdn_of_jde(astro.new_moon_jde(k))


def _k_on_or_before(j: int) -> int:
    """The greatest lunation number k with new-moon day <= j."""
    k = round((j - 2451550.1) / 29.5306)
    while _nm_day(k) > j:
        k -= 1
    while _nm_day(k + 1) <= j:
        k += 1
    return k


@functools.lru_cache(maxsize=None)
def _winter_solstice_jde(y: int) -> float:
    return astro.solve_solar_longitude(270.0, float(ar.civil2jdn(y, 12, 21)))


@functools.lru_cache(maxsize=None)
def _jie_days(y: int) -> tuple[int, ...]:
    """The 12 節 (minor-term) days of Gregorian year y, ascending:
    小寒(285°) through 大雪(255°)."""
    out = []
    est = float(ar.civil2jdn(y, 1, 6))
    for i, deg in enumerate((285, 315, 345, 15, 45, 75, 105, 135, 165, 195, 225, 255)):
        out.append(_jdn_of_jde(astro.solve_solar_longitude(deg, est + i * 30.437)))
    return tuple(out)


# -- the suì builder (無中氣置閏) -------------------------------------------


@functools.lru_cache(maxsize=None)
def _sui(y: int):
    """The months of the suì anchored at the winter solstices of years y-1
    and y: a list of (start_day, month_number 1-12, is_leap, lunar_year),
    from 十一月 (containing solstice y-1) up to but excluding 十一月
    (containing solstice y), plus that next start as the exclusive end."""
    ws0_jde = _winter_solstice_jde(y - 1)
    ws0 = _jdn_of_jde(ws0_jde)
    ws1 = _jdn_of_jde(_winter_solstice_jde(y))
    k0 = _k_on_or_before(ws0)
    k1 = _k_on_or_before(ws1)
    n = k1 - k0
    assert n in (12, 13), (y, n)
    starts = [_nm_day(k) for k in range(k0, k1 + 1)]

    leap_idx = None
    if n == 13:
        # major-term (中氣) days across the suì, walked from the solstice
        majors = [ws0]
        jde, deg = ws0_jde, 270.0
        for _ in range(13):
            deg = (deg + 30.0) % 360.0
            jde = astro.solve_solar_longitude(deg, jde + 30.437)
            majors.append(_jdn_of_jde(jde))
        for i in range(1, n):
            if not any(starts[i] <= d < starts[i + 1] for d in majors):
                leap_idx = i
                break
        assert leap_idx is not None, y

    months = []
    num, lunar_year = 11, y - 1
    for i in range(n):
        # month 0 contains the solstice (a major term), so leap_idx >= 1
        if i and i != leap_idx:
            num = num % 12 + 1
            if num == 1:
                lunar_year = y
        months.append((starts[i], num, i == leap_idx, lunar_year))
    return months, starts[n]


def _sui_of(j: int):
    """The (months, end) of the suì covering day j."""
    y = ar.jdn2civil(j)[0]
    for yy in (y, y + 1, y - 1):
        months, end = _sui(yy)
        if months[0][0] <= j < end:
            return months, end
    raise AssertionError(f"no suì covers day {j}")


def _month_of(j: int) -> tuple[int, int, bool, int]:
    """(start_day, month_number, is_leap, lunar_year) of the month holding j.
    Uncached per day — the per-suì cache above keeps this cheap while day
    streams stay memory-bounded."""
    months, _ = _sui_of(j)
    for start, num, leap, ly in reversed(months):
        if start <= j:
            return start, num, leap, ly
    raise AssertionError(f"day {j} precedes its suì")


@functools.lru_cache(maxsize=None)
def cny_day(lunar_year: int) -> int:
    """The 正月初一 (Chinese New Year day) of `lunar_year`."""
    for start, num, leap, ly in _sui(lunar_year)[0]:
        if num == 1 and not leap and ly == lunar_year:
            return start
    raise AssertionError(f"no CNY found for {lunar_year}")


# -- per-day evaluators ----------------------------------------------------


def jdn2cn_year(j: int) -> int:
    return _month_of(j)[3]


def jdn2cn_month(j: int) -> CnMonth:
    _, num, leap, _ = _month_of(j)
    return _CN_MONTHS[(num - 1) * 2 + leap]


def jdn2cn_day(j: int) -> CnDay:
    return _CN_DAYS[j - _month_of(j)[0]]


def year_pillar_index_of(j: int) -> int:
    return (jdn2cn_year(j) - 4) % 60


def jdn2cn_year_tiangan(j: int) -> Tiangan:
    return _TIANGAN[year_pillar_index_of(j) % 10]


def jdn2cn_year_dizhi(j: int) -> Dizhi:
    return _DIZHI[year_pillar_index_of(j) % 12]


# The month pillar: a continuous sexagenary count over 節 boundaries.
# 立春 1984 begins the 丙寅 month (index 2).


def _jie_ordinal(j: int) -> int:
    """Number of 節 days <= j, as 12·year + count within that year's list.
    Year-agnostic: in the far future the terms drift into the previous civil
    December (first breach: 小寒 of 9233 falls on 9232-12-31), so the year
    whose list holds the last 節 <= j may be the civil year's neighbour."""
    y = ar.jdn2civil(j)[0]
    for yy in (y + 1, y, y - 1):
        c = bisect.bisect_right(_jie_days(yy), j)
        if c:
            return 12 * yy + c
    raise AssertionError(f"no 節 precedes day {j}")


@functools.lru_cache(maxsize=None)
def _anchor_ordinal() -> int:
    return _jie_ordinal(_jie_days(1984)[1])  # 立春 1984 = 丙寅月


def month_pillar_index_of(j: int) -> int:
    return (2 + _jie_ordinal(j) - _anchor_ordinal()) % 60


def jdn2cn_month_tiangan(j: int) -> Tiangan:
    return _TIANGAN[month_pillar_index_of(j) % 10]


def jdn2cn_month_dizhi(j: int) -> Dizhi:
    return _DIZHI[month_pillar_index_of(j) % 12]


# -- span ends --------------------------------------------------------------


def cn_year_span_end(j: int) -> int:
    """First day of the next lunar year (also the year pillar's span end)."""
    return cny_day(jdn2cn_year(j) + 1)


def cn_month_span_end(j: int) -> int:
    """First day of the next lunisolar month."""
    months, end = _sui_of(j)
    return min((s for s, _, _, _ in months if s > j), default=end)


def cn_month_pillar_span_end(j: int) -> int:
    """The next 節 day after j (the month pillar advances there). Checks the
    next civil year too — beyond year 9233 a 節 can land in the previous
    civil December, so 'the next 節' need not lie in j's own year's list."""
    y = ar.jdn2civil(j)[0]
    for yy in (y, y + 1):
        for jd in _jie_days(yy):
            if jd > j:
                return jd
    raise AssertionError(f"no 節 follows day {j}")
