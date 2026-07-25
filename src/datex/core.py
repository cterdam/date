"""Date: a symbolic set of days — the only noun in the package.

A Date is a union of conjunctions (disjunctive normal form) of signed
per-axis atoms: (axis, sign, values) meaning the day's value on that axis is
in `values` (sign True) or not (sign False). The form is closed under &, |,
-, ^ and complement, so the set algebra has no gaps. Types gate form only: a
wrongly-typed value or an unknown member of a closed vocabulary (month=13)
raises, while any well-formed value no day carries (day=32, week 53 of a
52-week year) is simply the empty set, exactly like Feb 30.

The engine enumerates by span-jumping: every axis evaluator is a step
function of the day, so a conjunction's runs are walked boundary-to-boundary
(cost proportional to runs, never days — while a predicate is false the walk
jumps to the last failing predicate's boundary). Emptiness of arithmetic
conjunctions is decided exactly by one lcm-period window per driver span
(the periodicity theorem); astronomically-constrained conjunctions over an
unbounded driver answer by the drift-recurrence decree, with the
lunisolar-month/節氣-branch incompatibility certificate proving the certain
empties.

project(axes) takes one tuple of Axis members and yields sorted, duplicate-
free value tuples of the same arity; jdn components are maximally contiguous
ranges. Sorted means truly sorted: over an infinite set, combinations after
an infinitely-repeating prefix are never reached — put unbounded axes first.
"""

from __future__ import annotations

import enum
import functools
import heapq
import math

from . import arithmetic as ar
from . import chinese as ch
from .axis import MONOTONE, Axis, is_scalar, normalize, sort_key
from .values import CnMonth, Dizhi

MIN_JDN = 1
_INF = math.inf
_MAX_TERMS = 4096

_DIZHI = tuple(Dizhi)


# -- range/span set helpers (sorted, disjoint; driver stops may be inf) ----


def _union_spans(pairs):
    out = []
    for s, e in sorted(pairs):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def _merge_ranges(ranges) -> tuple[range, ...]:
    return tuple(
        range(s, e) for s, e in _union_spans((r.start, r.stop) for r in ranges if r)
    )


def _spans(ranges):
    """Merged (start, stop) pairs of a collection of ranges."""
    return [(r.start, r.stop) for r in _merge_ranges(ranges)]


def _isect_spans(a, b):
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        s = max(a[i][0], b[j][0])
        e = min(a[i][1], b[j][1])
        if s < e:
            out.append((s, e))
        if a[i][1] <= b[j][1]:
            i += 1
        else:
            j += 1
    return out


def _sub_spans(a, sub):
    """a minus sub, both sorted span lists (sub finite)."""
    out = []
    for s, e in a:
        lo = s
        for rs, re in sub:
            if re <= lo or rs >= e:
                continue
            if rs > lo:
                out.append((lo, rs))
            lo = max(lo, re)
        if lo < e:
            out.append((lo, e))
    return out


# -- atoms and terms -------------------------------------------------------
#
# term: tuple of (axis, sign, values) sorted by axis order, one atom per
# axis. jdn values are pre-merged range tuples (frozenset of ranges).

_AXIS_ORDER = {a: i for i, a in enumerate(Axis)}


def _week_start(y: int, w: int) -> int:
    """The Monday starting ISO week (y, w) — by formula, unvalidated."""
    jan4 = ar.civil2jdn(y, 1, 4)
    return jan4 - jan4 % 7 + 7 * (w - 1)


def _canon(atoms) -> tuple:
    return tuple(sorted(atoms, key=lambda t: _AXIS_ORDER[t[0]]))


def _merge_two(t1: tuple, t2: tuple):
    """Conjunction of two terms, or None if locally contradictory."""
    d = {a: (sg, vs) for a, sg, vs in t1}
    for a, sg, vs in t2:
        if a not in d:
            d[a] = (sg, vs)
            continue
        sg0, vs0 = d[a]
        if a is Axis.jdn:
            s0, s1 = _spans(vs0), _spans(vs)
            if sg0 and sg:
                got = _isect_spans(s0, s1)
            elif sg0 and not sg:
                got = _sub_spans(s0, s1)
            elif sg and not sg0:
                got = _sub_spans(s1, s0)
            else:
                d[a] = (False, frozenset(_merge_ranges(vs0 | vs)))
                continue
            new = frozenset(range(s, e) for s, e in got)
            if not new:
                return None
            d[a] = (True, new)
        elif sg0 and sg:
            new = vs0 & vs
            if not new:
                return None
            d[a] = (True, new)
        elif not sg0 and not sg:
            d[a] = (False, vs0 | vs)
        else:
            pos, neg = (vs0, vs) if sg0 else (vs, vs0)
            new = pos - neg
            if not new:
                return None
            d[a] = (True, new)
    return _clean((a, sg, vs) for a, (sg, vs) in d.items())


_INT_CODOMAINS = {Axis.day: range(1, 32), Axis.doy: range(1, 367)}


def _codomain(axis):
    if axis in _INT_CODOMAINS:
        return _INT_CODOMAINS[axis]
    if axis.kind is bool:
        return (False, True)
    return tuple(axis.kind)


def _finite_codomain(axis):
    """The axis's full value set, or None when unbounded (jdn, year, week,
    cn_year)."""
    if axis in _INT_CODOMAINS or axis.kind is bool:
        return frozenset(_codomain(axis))
    if isinstance(axis.kind, type) and issubclass(axis.kind, enum.Enum):
        return frozenset(axis.kind)
    return None


def _clean(term):
    """The term with values clipped to each axis's codomain and
    trivially-true atoms dropped (a positive atom covering the whole
    codomain, a negative atom over nothing), or None when dead (a positive
    atom over nothing — day=32 dies here, exactly like Feb 30 — or a
    negative atom covering everything)."""
    out = []
    for a, sg, vs in term:
        cod = _finite_codomain(a)
        if cod is not None:
            vs = vs & cod
        if sg and not vs:
            return None
        if not sg and not vs:
            continue
        if cod is not None and cod <= vs:
            if sg:
                continue  # always true
            return None  # always false
        out.append((a, sg, vs))
    return _canon(out)


def _compatible(cm: CnMonth, dz: Dizhi) -> bool:
    """Whether any day of lunisolar month `cm` can carry 節氣-month branch
    `dz`: month 11 contains the winter solstice (子月's heart), so month n is
    centered on branch (n+1) mod 12 and touches only its neighbours — one
    further for a leap month, which sits one lunation later."""
    c = (cm.number + 1) % 12
    allowed = {(c - 1) % 12, c % 12, (c + 1) % 12}
    if cm.leap:
        allowed.add((c + 2) % 12)
    return _DIZHI.index(dz) in allowed


def _certified_empty(term) -> bool:
    d = {a: vs for a, sg, vs in term if sg}
    m, dz = d.get(Axis.cn_month), d.get(Axis.cn_month_dizhi)
    return (
        m is not None
        and dz is not None
        and not any(_compatible(cm, z) for cm in m for z in dz)
    )


# -- the span-jumping enumerator -------------------------------------------


def _driver(term):
    """Sorted disjoint (start, stop) spans bounding the term's days — the
    positive monotone atoms turned into day spans (stop may be inf)."""
    spans = [(MIN_JDN, _INF)]
    for a, sg, vs in term:
        if a is Axis.jdn:
            rs = _spans(vs)
            spans = _isect_spans(spans, rs) if sg else _sub_spans(spans, rs)
        elif sg and a is Axis.year:
            spans = _isect_spans(spans, _union_spans(
                (ar.civil2jdn(v, 1, 1), ar.civil2jdn(v + 1, 1, 1)) for v in vs))
        elif sg and a is Axis.week:
            got = [
                (s, s + 7)
                for y, w in vs
                if 1 <= w <= ar.iso_weeks_in(y)
                for s in (_week_start(y, w),)
            ]
            spans = _isect_spans(spans, _union_spans(got))
        elif sg and a is Axis.cn_year:
            spans = _isect_spans(spans, _union_spans(
                (ch.cny_day(v), ch.cny_day(v + 1)) for v in vs))
    return spans


def _preds(term):
    """The atoms the walk must evaluate: everything but jdn (folded into the
    driver, both signs) and the positive monotone atoms (already spans)."""
    return tuple(
        (a, sg, vs)
        for a, sg, vs in term
        if a is not Axis.jdn and not (sg and a in MONOTONE)
    )


def _step(preds, j):
    """(ok, next_boundary): while any predicate is false the verdict cannot
    flip before the LAST failing predicate's span end, so jump there."""
    false_ends = []
    true_ends = []
    for a, sg, vs in preds:
        if (a.from_jdn(j) in vs) == sg:
            true_ends.append(a.span_end(j))
        else:
            false_ends.append(a.span_end(j))
    if false_ends:
        return False, max(false_ends)
    return True, min(true_ends, default=_INF)


def _horizon_and_window(term, preds):
    """For an all-arithmetic term: (horizon, window) such that beyond
    `horizon` every negative monotone atom is constantly true and the
    remaining predicates repeat with period `window` — so any driver span
    scanned for one full window past the horizon with no hit has none."""
    window = math.lcm(*([a.period for a, _, _ in preds if a.period] or [1]))
    horizon = MIN_JDN
    for a, sg, vs in preds:
        if sg or a not in MONOTONE:
            continue
        if a is Axis.year:
            horizon = max(horizon, max(ar.civil2jdn(v + 1, 1, 1) for v in vs))
        elif a is Axis.week:
            horizon = max(horizon, max(_week_start(y, w) + 7 for y, w in vs))
    return horizon, window


def _first_day(term, start: int):
    """The first member day >= start, or None. Exact: arithmetic terms are
    capped by the periodicity window; astronomically-constrained terms over
    an unbounded driver scan under the drift-recurrence decree."""
    preds = _preds(term)
    astro = any(a.astro for a, _, _ in preds)
    if not astro:
        horizon, window = _horizon_and_window(term, preds)
    for s, e in _driver(term):
        j = max(s, start)
        stop = e if astro else min(e, max(j, horizon) + window)
        while j < stop:
            ok, b = _step(preds, j)
            if ok:
                return j
            j = b  # a failing step always has a finite boundary
    return None


def _term_runs(term):
    """Maximal runs of the term's day-set, ascending. The caller must have
    excluded terms with an unbounded contiguous tail."""
    preds = _preds(term)
    for s, e in _driver(term):
        j, run = s, None
        while j < e:
            ok, b = _step(preds, j)
            if ok and run is None:
                run = j
            elif not ok and run is not None:
                yield range(run, j)
                run = None
            if b >= e:
                break
            j = b
        if run is not None:
            if e == _INF:
                raise AssertionError("unbounded run must be pre-excluded")
            yield range(run, int(e))


def _tail_infinite(term) -> bool:
    """Whether the day-set provably contains [x, inf): unbounded driver and
    every predicate a negative atom on a monotone axis (eventually always
    true)."""
    drv = _driver(term)
    if not drv or drv[-1][1] != _INF:
        return False
    return all(not sg and a in MONOTONE for a, sg, _ in _preds(term))


def _reduce(term):
    """The term without its negative monotone atoms — a superset whose
    emptiness implies the term's, and whose nonemptiness implies the term's
    when the driver is unbounded (any periodic hit recurs beyond every
    horizon, where those negatives are constantly true)."""
    return tuple(x for x in term if x[1] or x[0] not in MONOTONE)


@functools.lru_cache(maxsize=None)
def _term_nonempty(term) -> bool:
    if any(sg and not vs for _, sg, vs in term):
        return False
    if _certified_empty(term):
        return False
    drv = _driver(term)
    if not drv:
        return False
    unbounded = drv[-1][1] == _INF
    preds = _preds(term)
    if not any(a.astro for a, _, _ in preds):
        if unbounded:  # O(window), horizons irrelevant by periodicity
            return _first_day(_reduce(term), MIN_JDN) is not None
        return _first_day(term, MIN_JDN) is not None
    if unbounded:
        # the decree presumes a satisfiable arithmetic skeleton
        skeleton = _reduce(tuple(x for x in term if not x[0].astro))
        return _first_day(skeleton, MIN_JDN) is not None  # drift-recurrence decree
    return _first_day(term, MIN_JDN) is not None


def _union_runs(terms, tail_guard=None):
    """Maximal runs of the union of the terms' day-sets, ascending.

    tail_guard = (H, L) certifies emergent unbounded tails for arithmetic
    unions: a coalesced run covering one full lcm window L beyond every
    horizon H repeats forever (each term is periodic there), so the tail is
    provably infinite and unrepresentable as a range."""
    streams = [_term_runs(t) for t in terms]
    cur = None
    for r in heapq.merge(*streams, key=lambda r: r.start):
        if cur is None:
            cur = [r.start, r.stop]
        elif r.start <= cur[1]:
            cur[1] = max(cur[1], r.stop)
        else:
            yield range(*cur)
            cur = [r.start, r.stop]
        if tail_guard is not None and cur[1] - max(cur[0], tail_guard[0]) >= tail_guard[1]:
            raise NotImplementedError(
                "the union has an unbounded contiguous tail; a range cannot "
                "represent it — constrain any non-monotone axis"
            )
    if cur is not None:
        yield range(*cur)


# -- projection ------------------------------------------------------------


def _atom_date(axis, v) -> Date:
    d = object.__new__(Date)
    d._terms = (((axis, True, frozenset((v,))),),)
    return d


def _monotone_values(d: Date, axis):
    """The set's distinct values on a monotone axis, ascending."""
    start = MIN_JDN
    while True:
        firsts = [f for t in d._terms if (f := _first_day(t, start)) is not None]
        if not firsts:
            return
        j = min(firsts)
        yield axis.from_jdn(j)
        start = axis.span_end(j)


def _project(d: Date, axes):
    a0 = axes[0]
    if a0 is Axis.jdn:
        terms = tuple(t for t in d._terms if _term_nonempty(t))
        for t in terms:
            if _tail_infinite(t):
                raise NotImplementedError(
                    "the day-set has an unbounded contiguous tail; a range "
                    "cannot represent it — constrain any non-monotone axis"
                )
        # emergent-tail certificate: only arithmetic terms with an unbounded
        # driver can conspire to cover a tail (an all-astro universe cover
        # would stream unboundedly — the documented frontier)
        tail_guard = None
        unbounded = [t for t in terms if _driver(t)[-1][1] == _INF]
        if unbounded and not any(
            a.astro for t in unbounded for a, _, _ in _preds(t)
        ):
            hs, ws = [], []
            for t in terms:
                h, w = _horizon_and_window(t, _preds(t))
                drv = _driver(t)
                hs.append(max(h, drv[-1][0]))
                if drv[-1][1] != _INF:
                    hs.append(drv[-1][1])
                else:
                    ws.append(w)
            tail_guard = (max(hs), math.lcm(*ws))
        rest = axes[1:]
        for r in _union_runs(terms, tail_guard):
            j, cur, cs = r.start, None, r.start
            while j < r.stop:
                vals = tuple(a.from_jdn(j) for a in rest)
                b = min([r.stop] + [a.span_end(j) for a in rest])
                if cur is None:
                    cur, cs = vals, j
                elif vals != cur:
                    yield (range(cs, j), *cur)
                    cur, cs = vals, j
                j = b
            yield (range(cs, r.stop), *cur)
        return
    values = (
        _monotone_values(d, a0)
        if a0 in MONOTONE
        else (v for v in _codomain(a0) if d & _atom_date(a0, v))
    )
    for v in values:
        if len(axes) == 1:
            yield (v,)
        else:
            sub = d & _atom_date(a0, v)
            yield from ((v, *rest) for rest in _project(sub, axes[1:]))


# -- Date ------------------------------------------------------------------


class Date:
    __slots__ = ("_terms",)

    def __init__(self, **constraints):
        atoms = []
        for name, raw in constraints.items():
            try:
                axis = Axis[name]
            except KeyError:
                raise TypeError(
                    f"unknown axis {name!r}; axes: {', '.join(a.name for a in Axis)}"
                ) from None
            values = [raw] if is_scalar(axis, raw) else list(raw)
            vs = frozenset(normalize(axis, v) for v in values)
            if axis is Axis.jdn:
                vs = frozenset(_merge_ranges(vs))
            atoms.append((axis, True, vs))
        term = _clean(atoms)
        self._terms = () if term is None else (term,)

    @classmethod
    def _make(cls, terms) -> Date:
        d = object.__new__(cls)
        seen, out = set(), []
        for t in terms:
            if t not in seen:
                seen.add(t)
                out.append(t)
        if len(out) > _MAX_TERMS:
            raise NotImplementedError(f"normal form exceeds {_MAX_TERMS} terms")
        d._terms = tuple(out)
        return d

    # -- the set protocol --------------------------------------------------

    def __and__(self, other):
        if not isinstance(other, Date):
            return NotImplemented
        return Date._make(
            m
            for t1 in self._terms
            for t2 in other._terms
            if (m := _merge_two(t1, t2)) is not None
        )

    def __or__(self, other):
        if not isinstance(other, Date):
            return NotImplemented
        return Date._make(self._terms + other._terms)

    def _complement(self) -> Date:
        result = [()]
        for term in self._terms:
            result = [
                m
                for conj in result
                for a, sg, vs in term
                if (m := _merge_two(conj, ((a, not sg, vs),))) is not None
            ]
            if len(result) > _MAX_TERMS:
                raise NotImplementedError(f"normal form exceeds {_MAX_TERMS} terms")
        return Date._make(result)

    def __sub__(self, other):
        if not isinstance(other, Date):
            return NotImplemented
        return self & other._complement()

    def __xor__(self, other):
        if not isinstance(other, Date):
            return NotImplemented
        return (self - other) | (other - self)

    def __bool__(self) -> bool:
        return any(_term_nonempty(t) for t in self._terms)

    def __contains__(self, j: object) -> bool:
        if isinstance(j, bool) or not isinstance(j, int) or j < MIN_JDN:
            return False
        for term in self._terms:
            for a, sg, vs in term:
                if a is Axis.jdn:
                    if any(j in r for r in vs) != sg:
                        break
                elif (a.from_jdn(j) in vs) != sg:
                    break
            else:
                return True
        return False

    def __eq__(self, other):
        if not isinstance(other, Date):
            return NotImplemented
        return not self ^ other

    def __le__(self, other):
        if not isinstance(other, Date):
            return NotImplemented
        return not self - other

    def __lt__(self, other):
        if not isinstance(other, Date):
            return NotImplemented
        return not self - other and bool(other - self)

    def __ge__(self, other):
        if not isinstance(other, Date):
            return NotImplemented
        return not other - self

    def __gt__(self, other):
        if not isinstance(other, Date):
            return NotImplemented
        return not other - self and bool(self - other)

    # -- projection --------------------------------------------------------

    def project(self, axes):
        """Sorted, duplicate-free value tuples over the given tuple of axes;
        jdn components are maximally contiguous ranges."""
        if not isinstance(axes, tuple):
            raise TypeError(f"project takes a tuple of Axis members, got {type(axes).__name__}")
        for a in axes:
            if not isinstance(a, Axis):
                raise TypeError(f"project takes Axis members, got {a!r}")
        if not axes:
            raise ValueError("project needs at least one axis")
        if len(set(axes)) != len(axes):
            raise ValueError("duplicate projection axes")
        return _project(self, axes)

    def __repr__(self) -> str:
        if not self._terms:
            return "Date(<empty>)"

        def atom(a, sg, vs):
            shown = sorted(vs, key=sort_key(a))
            body = repr(shown[0]) if len(shown) == 1 else repr(shown)
            return f"{a.name}{'=' if sg else '!='}{body}"

        terms = [
            "Date(" + ", ".join(atom(*x) for x in t) + ")" if t else "Date()"
            for t in self._terms
        ]
        return " | ".join(terms)
