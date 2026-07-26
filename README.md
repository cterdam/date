# datex

Symbolic day-sets over the unbounded Julian Day Number universe: exact
constraints, a gapless set algebra, and sorted joint projection across
calendar systems. `pip install datex`.

Every day is ultimately a JDN (an integer ≥ 1; the universe is infinite
above). A `Date` is a *set* of days described by constraints along any axes;
nothing is enumerated until you ask, and every answer is exact — there is no
heuristic mode. Zero runtime dependencies; all calendrical and astronomical
calculation is in-house.

```python
from datex import Axis, CnDay, CnMonth, Date, Dizhi, Month, Tiangan, Weekday, Zodiac

next(iter(Date(year=2000, month=1, day=1).project(tuple(Axis))))
# (range(2451545, 2451546), 2000, Month.JAN, 1, Weekday.SAT, (1999, 52),
#  1, True, Zodiac.CAPRICORN, 1999, Tiangan.己, Dizhi.卯, CnMonth.十一月,
#  Tiangan.丙, Dizhi.子, CnDay.廿五, Tiangan.戊, Dizhi.午)

list(Date(month=9, day=2).project((Axis.doy, Axis.leap)))
# joint, not a product of marginals: [(245, False), (246, True)]

Date(year=2000, month=1, day=1, weekday=Weekday.TUE)    # falsy — never an exception
bool(Date(cn_month="正月", cn_month_dizhi="酉"))          # False, by certificate
Date(cn_month="八月") | Date(cn_month="九月")             # every set operation closes
```

## The model

- **Universe** — days are JDNs ≥ 1, unbounded. No windows, no vendored
  tables: everything is calculated.
- **`Date(**constraints)`** — a symbolic conjunction across axes; an
  iterable value is a disjunction within its axis. Internally a Date is a
  union of conjunctions of signed atoms (disjunctive normal form), so the
  algebra is **closed with no gaps**: `&`, `|`, `-`, `^`, complements,
  subset/equality comparisons (`<=`, `<`, `==`, …) all work, for arithmetic
  and astronomical constraints alike. Types gate *form* only: a
  wrongly-typed value or an unknown member of a closed vocabulary
  (`month=13`) raises, while any well-formed value no day carries
  (`day=32`, week 53 of a 52-week year) is simply the empty set — exactly
  like Feb 30. jdn values are plain unit-step `range`s of days (a single
  day is `range(x, x + 1)`).
- **Pythonic set protocols, nothing else** — truthiness is non-emptiness
  (`bool(d)`, like every Python container), `j in d` is day membership, and
  the operators above. There is no `count`, `len`, or `is_empty`: day-count
  is `sum(len(r) for (r,) in d.project((Axis.jdn,)))`, value-count is
  `sum(1 for _ in it)`, emptiness is `not d`. An infinite set yields an
  unending iterator, which is more honest than a number.
- **`project(axes)`** — the one read-out. Takes a single *tuple* of `Axis`
  members; returns an iterator of value tuples of the same arity — sorted,
  duplicate-free, each a combination the day-set actually attains, with jdn
  components as **maximally contiguous ranges** (in a joint, maximal over
  spans where the other projected components are constant). Sorted is truly
  sorted: over an infinite set, combinations after an infinitely-repeating
  prefix are never reached (`(weekday, year)` never leaves Monday) — put
  unbounded axes first. A set with an unbounded contiguous tail (e.g. the
  whole universe) cannot express its tail as a `range` and raises when
  projected on jdn.

## Axes

Eighteen, in canonical order: `jdn`, `year`, `month`, `day`, `weekday`,
`week` (ISO year-week pair), `doy`, `leap`, `zodiac`, `cn_year`,
`cn_year_tiangan`, `cn_year_dizhi`, `cn_month`, `cn_month_tiangan`,
`cn_month_dizhi`, `cn_day`, `cn_day_tiangan`, `cn_day_dizhi`.

Each axis is one row of a declaration table: its value kind, its
jdn-periodicity, its evaluator `jdn2X` (every evaluator is a step function
of the day), and its span end (the first day the value changes). The
lunisolar layer behind the cn axes computes truncated VSOP87 apparent solar
longitude and ELP-2000 lunar longitude (Meeus), new moons root-solved as
true conjunctions, the Espenak–Meeus ΔT model, UTC+8 day slicing,
winter-solstice anchoring with 無中氣置閏, the CNY-boundary year pillar, and
the 節氣-delimited continuous month pillar (立春 1984 = 丙寅月).

Value types: every enum doubles as a primitive — `Weekday`/`Month` are
IntEnums (interchange with ints; bools rejected), `Zodiac`/`Tiangan`/
`Dizhi`/`CnMonth`/`CnDay` are StrEnums whose values are the canonical forms
(`Date(zodiac="Virgo")`, `Tiangan("甲")`). `year`/`cn_year`/`day`/`doy` are
ints, `leap` a bool, `week` an `(iso_year, week)` int pair.

## The engine

Enumeration **span-jumps**: a conjunction's runs are walked
boundary-to-boundary, so cost is proportional to runs — and to the finest
constrained axis — never to days at large. Wherever a value has a closed
form in the day, a failing predicate **seeks**: the walk jumps straight to
its next satisfying day (weekday and the day pillars by residue, month/day/
doy through the civil conversions); only the astronomical evaluators, which
have no inverse, fall back to span boundaries. Emptiness is decided by
**structural certificates** wherever a closed form exists — calendar shape
(Feb 30, day 31 in a 30-day month, doy 366 in a common year, doy/month
mismatches), sexagenary stem/branch parity at all three pillar levels, the
cn_year-pinned year pillar, and the lunisolar-month/節氣-branch
incompatibility — and only otherwise by scanning one lcm-period window per
driver span (everything Gregorian repeats every 146,097 days, weekdays
every 7, the day pillar every 60 — a full silent window proves emptiness).
Astronomically-constrained sets over an unbounded day range answer
truthiness by the **drift-recurrence principle** (part of the imposed
standard: the Gregorian year outpaces the decreed tropical year, so the
solar frame precesses through the whole calendar and every satisfiable
combination recurs forever); the decree never overrides a certificate or an
arithmetically-empty skeleton. The one open frontier: a union
of purely astronomical sets that happens to cover an unbounded contiguous
tail has no finite certificate and streams unboundedly on jdn.

## The imposed standard

Dates outside any calendar's historical span are decreed, not discovered:
proleptic Gregorian with astronomical year numbering (year 0 exists); ISO
weekdays and weeks; the customary tropical zodiac boundaries; the sexagenary
day count anchored at 1949-10-01 = 甲子 (`index(jdn) = (jdn + 49) % 60`);
the modern Chinese lunisolar rule applied uniformly (UTC+8 slicing also
before 1929, when historical calendars used Beijing local time), with
instants defined by the in-house truncated Meeus series extrapolated
proleptically; and the drift-recurrence principle above.

Verified at development time: 1929–2100 matches sxtwl day-for-day (lunar
year/month/leap/day and month pillar); solar longitude within 2″ and lunar
within 14″ of Swiss Ephemeris over 1600–2400; new moons within ~23 s over
1000–3000; suì invariants hold from −1000 to 3500. `tests/golden/` holds the
generators (sxtwl is never a dependency).

## Development

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

Requires Python ≥ 3.11. Tests are stdlib-only; oracles are `datetime`
sweeps, literature anchors (JDN 0 = −4713-11-24, J2000.0 = JDN 2451545),
and the dev-time cross-checked goldens.
