"""Dev-time validator and golden generator for the lunisolar layer — the
drift check of our in-house astronomy against independent implementations.

Requires sxtwl (and optionally pyswisseph as an instant-level arbiter);
neither is ever a package dependency. Run manually:

    PYTHONPATH=src python tests/golden/gen_chinese.py sweep   # day-for-day vs sxtwl
    PYTHONPATH=src python tests/golden/gen_chinese.py goldens # emit test fixtures

(from the repo root)

Expected sweep result: 1929-2100 matches sxtwl exactly (day-level, all of
lunar year/month/leap/day and the 節氣-based month pillar). Pre-1929
divergences are decreed: the imposed standard slices days at UTC+8
uniformly, while historical calendars used Beijing local (apparent) time.
A couple of boundary events per few centuries far from the present are
irreducible instant-level differences between approximating ephemerides.
"""

import datetime
import sys

import sxtwl

from datex import arithmetic as ar
from datex import chinese as ch


def sweep(y0=1929, y1=2101):
    bad = []
    d0 = datetime.date(y0, 1, 1).toordinal()
    d1 = datetime.date(y1, 1, 1).toordinal()
    for o in range(d0, d1):
        dd = datetime.date.fromordinal(o)
        j = ar.civil2jdn(dd.year, dd.month, dd.day)
        sd = sxtwl.fromSolar(dd.year, dd.month, dd.day)
        start, num, leap, ly = ch._month_of(j)
        idx = ch.month_pillar_index_of(j)
        mgz = sd.getMonthGZ()
        if (num, bool(leap), j - start + 1, ly) != (
            sd.getLunarMonth(), bool(sd.isLunarLeap()), sd.getLunarDay(),
            sd.getLunarYear(),
        ) or (idx % 10, idx % 12) != (mgz.tg, mgz.dz):
            bad.append(dd)
    print(f"{y0}-{y1 - 1}: {len(bad)} mismatching days", bad[:10])


def goldens(y0=1984, y1=2051):
    print("_CNY_GOLDENS = {")
    for y in range(y0, y1):
        j = ch.cny_day(y)
        dd = datetime.date(*ar.jdn2civil(j))
        sd = sxtwl.fromSolar(dd.year, dd.month, dd.day)
        assert (sd.getLunarMonth(), sd.getLunarDay(), bool(sd.isLunarLeap())) == (1, 1, False)
        print(f"    {y}: ({dd.year}, {dd.month}, {dd.day}),")
    print("}")
    print("_LEAP_GOLDENS = {")
    for y in range(y0, y1):
        leaps = [
            n
            for yy in (y, y + 1)
            for s, n, l, ly in ch._sui(yy)[0]
            if l and ly == y
        ]
        print(f"    {y}: {leaps[0] if leaps else None},")
    print("}")


if __name__ == "__main__":
    (sweep if "sweep" in sys.argv[1:] else goldens)()
