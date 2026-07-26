# datex

Symbolic day-sets over the unbounded Julian Day Number universe: exact
constraints, a gapless set algebra, sorted joint projection across calendar
systems. Zero dependencies, Python ≥ 3.11. `pip install datex`.

A `Date` is a *set* of days (JDNs ≥ 1, infinite above) described by
constraints; nothing is enumerated until asked, every answer is exact.

## Axes and types

Eighteen axes, in canonical order. Enums double as primitives:
`Weekday`/`Month` are IntEnums (ints accepted, bools rejected), the rest are
StrEnums whose values are the canonical strings (`Date(zodiac="Virgo")`,
`Date(cn_day="初一")`).

| axis | type | values |
|---|---|---|
| `jdn` | `range` (step 1) | a single day is `range(x, x+1)` |
| `year` | `int` | astronomical numbering — year 0 exists |
| `month` | `Month` | `JAN`…`DEC` = 1…12 |
| `day` | `int` | day of month |
| `weekday` | `Weekday` | ISO: `MON`…`SUN` = 1…7 |
| `week` | `(int, int)` | ISO (year, week) pair |
| `doy` | `int` | day of year |
| `leap` | `bool` | Gregorian leap year |
| `zodiac` | `Zodiac` | `"Aries"`…`"Pisces"`, customary tropical dates |
| `cn_year` | `int` | lunar year, changes at 正月初一 |
| `cn_year_tiangan` / `cn_year_dizhi` | `Tiangan` / `Dizhi` | year pillar 天干/地支 |
| `cn_month` | `CnMonth` | `正月`…`十二月` + `閏` forms |
| `cn_month_tiangan` / `cn_month_dizhi` | `Tiangan` / `Dizhi` | 節氣-delimited month pillar |
| `cn_day` | `CnDay` | `初一`…`三十` |
| `cn_day_tiangan` / `cn_day_dizhi` | `Tiangan` / `Dizhi` | day pillar, 1949-10-01 = 甲子 |

## Constructing sets

Keywords conjoin; an iterable value disjoins within its axis. Types gate
*form* only: a wrong type or unknown vocabulary member (`month=13`) raises;
a well-formed value no day carries (`day=32`, week 53 of a 52-week year) is
simply the empty set, exactly like Feb 30 — falsy, never an exception.

```python
from datex import Axis, Date, Weekday

Date(year=2026, month=7, weekday=Weekday.FRI)   # July 2026 Fridays
Date(year=[1999, 2001], month=1, day=1)         # two New Year's Days
Date(jdn=range(2451545, 2451546))               # one concrete day
bool(Date(month=2, day=30))                     # False
```

## Set algebra

Closed under `&`, `|`, `-`, `^` (complement: `Date() - d`); compare with
`==`, `<=`, `<`, `>=`, `>`. Pythonic protocols only: truthiness is
non-emptiness, `j in d` is day membership. No `len` — an infinite set
yields an unending iterator, which is more honest than a number.

```python
Date(cn_month="八月") | Date(cn_month="九月")     # every operation closes
Date(month=2, day=29) <= Date(leap=True)        # True — provably
Date(month=2, day=29) == Date(doy=60, leap=True)  # True, across bases
2451545 in Date(month=1)                        # True (2000-01-01)
bool(Date(cn_month="正月", cn_month_dizhi="酉"))  # False, by certificate
```

## Projection

`d.project(axes)` — the one read-out. Takes a *tuple* of `Axis` members;
yields sorted, duplicate-free value tuples of the same arity, each a
combination the set actually attains (a joint, never a product of
marginals). Every direction works; what varies is the shape of the answer.

**Onto periodic / finite-codomain axes — always terminates**, even over
infinite sets, in canonical value order:

```python
list(Date(year=2026, month=7, weekday=Weekday.FRI).project((Axis.day,)))
# [(3,), (10,), (17,), (24,), (31,)]
list(Date().project((Axis.weekday,)))            # whole universe: 7 rows
list(Date(cn_day_tiangan="甲").project((Axis.cn_day_dizhi,)))
# 6 rows (子寅辰午申戌) — stem/branch parity, decided without scanning
```

**Onto unbounded axes (`year`, `week`, `cn_year`, `jdn`) — a lazy sorted
stream**, infinite if the set is:

```python
from itertools import islice
islice(Date(month=2, day=29).project((Axis.year,)), 4)
# (-4712,), (-4708,), (-4704,), (-4696,)   — proleptic century rule intact
```

Sorted is *truly* sorted, so put unbounded axes first: `(year, weekday)`
interleaves forever, while `(weekday, year)` never leaves Monday — an
infinite prefix is honest, not a bug.

**Onto `jdn` — maximally contiguous ranges**, merged across constraint
boundaries, split exactly where any co-projected value changes:

```python
list((Date(year=2023) | Date(year=2024)).project((Axis.jdn,)))
# [(range(2459946, 2460677),)]             — one range, 731 days
list(Date(jdn=range(2460340, 2460345)).project((Axis.jdn, Axis.month)))
# [(range(2460340, 2460342), JAN), (range(2460342, 2460345), FEB)]
Date().project((Axis.jdn,))                # raises NotImplementedError:
# an unbounded contiguous tail cannot be a range — constrain any
# non-monotone axis first
```

**Joint and cross-system** — constraints and projection may mix arithmetic
and astronomical axes freely:

```python
list(Date(month=9, day=2).project((Axis.doy, Axis.leap)))
# [(245, False), (246, True)]              — joint, not 2×2
islice(Date(cn_month="八月", weekday=Weekday.FRI, cn_day="十五")
       .project((Axis.year, Axis.month, Axis.day)), 3)   # ~0.1 s
```

## Efficiency

Closed forms first, day-walking last. Emptiness is answered by
**structural certificates** where one exists (calendar shape, sexagenary
parity, the cn_year-pinned pillar, lunisolar-month/branch incompatibility)
— no scan at all. Enumeration **seeks**: a failing constraint jumps
straight to its next satisfying day (residue arithmetic for weekday and the
day pillars, O(1) civil conversions for month/day/doy, one month-table
lookup for cn_day), so cost tracks the *output*, not the days in between.
Only the astronomical evaluators, which have no inverse, walk span to span
— lunation-sized, cached per suì. Remaining exact scans are capped at one
lcm-period window (everything Gregorian repeats every 146,097 days).
Astronomical sets over an unbounded range answer truthiness by the
**drift-recurrence principle** (the decreed solar frame precesses through
the whole calendar, so every satisfiable combination recurs forever) —
instant, though the first witness may lie millennia away. One frontier: a
union of purely astronomical sets covering an unbounded contiguous tail has
no finite certificate and will not terminate when projected on `jdn`.

## The imposed standard

Out-of-span dates are decreed, not discovered: proleptic Gregorian,
astronomical year numbering; ISO weeks; customary tropical zodiac; day
pillar `(jdn + 49) % 60` anchored at 1949-10-01 = 甲子; the modern Chinese
lunisolar rule (truncated VSOP87/ELP-2000 instants per Meeus, Espenak–Meeus
ΔT, UTC+8 slicing, 無中氣置閏, CNY-boundary year pillar, 節氣-delimited
month pillar, 立春 1984 = 丙寅月) applied uniformly across all time.
Verified at development: matches sxtwl day-for-day 1929–2100; solar
longitude within 2″ and lunar within 14″ of Swiss Ephemeris 1600–2400;
`tests/golden/` holds the generators (never runtime dependencies).

## Development

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

Stdlib-only tests: `datetime` sweeps, literature anchors, cross-checked
goldens, and day-for-day differential checks of the seek engine against
brute force.
