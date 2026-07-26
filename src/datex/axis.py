"""The Axis enum: a pure table — every axis declared exactly once, with its
value kind, jdn-periodicity, evaluator (from_jdn: day → value), span end
(the first day after j where the value changes), and whether it is
astronomical (backed by chinese.py rather than closed-form arithmetic).

The generic behaviors the engine derives from the table live beside it as
module functions. normalize() gates only the FORM of an input value (its
type); whether any day actually carries a well-formed value is the
engine's business — Date(day=32) is the empty set, exactly like Feb 30,
not a bounds error.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Callable

from . import arithmetic as ar
from . import chinese as ch
from .values import CnDay, CnMonth, Dizhi, Month, Tiangan, Weekday, Zodiac

_CYCLE = ar.GREGORIAN_PERIOD

# Sentinel kind for the one axis whose values are not one plain type.
_WEEK = object()  # (iso_year, week) int pair


# eq=False: definitions compare by identity, so axes with identical specs
# (e.g. the three Tiangan-valued pillars) never alias as enum members.
@dataclass(frozen=True, eq=False)
class _Def:
    kind: object
    period: int | None
    from_jdn: Callable[[int], object]
    span_end: Callable[[int], int]
    astro: bool = False
    # seek(j, sign, vs): first day >= j satisfying the atom, in closed form.
    # Set wherever the value is invertible in the day; the engine jumps to
    # it instead of walking span boundaries.
    seek: Callable[[int, bool, frozenset], int] | None = None


class Axis(enum.Enum):
    """A projection/constraint axis. Definition order is the canonical
    projection order."""

    jdn = _Def(
        kind=range,
        period=None,
        from_jdn=lambda j: j,
        span_end=ar.daily,
    )
    year = _Def(
        kind=int,
        period=None,
        from_jdn=ar.jdn2year,
        span_end=ar.year_span_end,
    )
    month = _Def(
        kind=Month,
        period=_CYCLE,
        from_jdn=ar.jdn2month,
        span_end=ar.month_span_end,
        seek=ar.month_seek,
    )
    day = _Def(
        kind=int,
        period=_CYCLE,
        from_jdn=ar.jdn2day,
        span_end=ar.daily,
        seek=ar.day_seek,
    )
    weekday = _Def(
        kind=Weekday,
        period=7,
        from_jdn=ar.jdn2weekday,
        span_end=ar.daily,
        seek=ar.weekday_seek,
    )
    week = _Def(
        kind=_WEEK,
        period=None,
        from_jdn=ar.jdn2week,
        span_end=ar.week_span_end,
    )
    doy = _Def(
        kind=int,
        period=_CYCLE,
        from_jdn=ar.jdn2doy,
        span_end=ar.daily,
        seek=ar.doy_seek,
    )
    leap = _Def(
        kind=bool,
        period=_CYCLE,
        from_jdn=ar.jdn2leap,
        span_end=ar.year_span_end,
    )
    zodiac = _Def(
        kind=Zodiac,
        period=_CYCLE,
        from_jdn=ar.jdn2zodiac,
        span_end=ar.zodiac_span_end,
    )
    cn_year = _Def(
        kind=int,
        period=None,
        from_jdn=ch.jdn2cn_year,
        span_end=ch.cn_year_span_end,
        astro=True,
    )
    cn_year_tiangan = _Def(
        kind=Tiangan,
        period=None,
        from_jdn=ch.jdn2cn_year_tiangan,
        span_end=ch.cn_year_span_end,
        astro=True,
    )
    cn_year_dizhi = _Def(
        kind=Dizhi,
        period=None,
        from_jdn=ch.jdn2cn_year_dizhi,
        span_end=ch.cn_year_span_end,
        astro=True,
    )
    cn_month = _Def(
        kind=CnMonth,
        period=None,
        from_jdn=ch.jdn2cn_month,
        span_end=ch.cn_month_span_end,
        astro=True,
    )
    cn_month_tiangan = _Def(
        kind=Tiangan,
        period=None,
        from_jdn=ch.jdn2cn_month_tiangan,
        span_end=ch.cn_month_pillar_span_end,
        astro=True,
    )
    cn_month_dizhi = _Def(
        kind=Dizhi,
        period=None,
        from_jdn=ch.jdn2cn_month_dizhi,
        span_end=ch.cn_month_pillar_span_end,
        astro=True,
    )
    cn_day = _Def(
        kind=CnDay,
        period=None,
        from_jdn=ch.jdn2cn_day,
        span_end=ar.daily,
        astro=True,
        seek=ch.cn_day_seek,
    )
    cn_day_tiangan = _Def(
        kind=Tiangan,
        period=60,
        from_jdn=ar.jdn2cn_day_tiangan,
        span_end=ar.daily,
        seek=ar.cn_day_tiangan_seek,
    )
    cn_day_dizhi = _Def(
        kind=Dizhi,
        period=60,
        from_jdn=ar.jdn2cn_day_dizhi,
        span_end=ar.daily,
        seek=ar.cn_day_dizhi_seek,
    )

    def __init__(self, d: _Def) -> None:
        self.kind = d.kind
        self.period = d.period
        self.from_jdn = d.from_jdn
        self.span_end = d.span_end
        self.astro = d.astro
        self.seek = d.seek


# The monotone axes: nondecreasing in the day, so their values enumerate
# ascending along runs and their positive constraints bound the day-set.
MONOTONE = frozenset({Axis.jdn, Axis.year, Axis.week, Axis.cn_year})


def normalize(axis: Axis, v):
    """The canonical form of one constraint value — a check of form only:
    TypeError for the wrong kind of value, ValueError for a name or number
    outside a closed vocabulary. Satisfiability is not checked here."""
    k = axis.kind
    if k is range:
        if not isinstance(v, range):
            raise TypeError(
                "jdn must be a range of days (a single day is range(x, x + 1)), "
                f"got {type(v).__name__}"
            )
        if v.step != 1:
            raise TypeError("jdn ranges must have step 1")
        return v
    if k is _WEEK:
        if (
            isinstance(v, (tuple, list))
            and len(v) == 2
            and all(isinstance(c, int) and not isinstance(c, bool) for c in v)
        ):
            return (v[0], v[1])
        raise TypeError("week value must be an (iso_year, week) pair of ints")
    if k is bool:
        if not isinstance(v, bool):
            raise TypeError(f"{axis.name} must be a bool, got {type(v).__name__}")
        return v
    if k is int:
        if isinstance(v, bool) or not isinstance(v, int):
            raise TypeError(f"{axis.name} must be an int, got {type(v).__name__}")
        return v
    # enum kinds validate through their own constructors: IntEnums double as
    # ints, StrEnums as their canonical strings
    if isinstance(v, k):
        return v
    if isinstance(v, bool):
        raise TypeError("bool is not a valid value for this axis")
    primitive = int if issubclass(k, enum.IntEnum) else str
    if isinstance(v, primitive):
        return k(v)  # ValueError if unknown
    raise TypeError(
        f"{axis.name} must be a {k.__name__} or {primitive.__name__}, "
        f"got {type(v).__name__}"
    )


def is_scalar(axis: Axis, raw) -> bool:
    """Whether a raw constraint value is one value (vs an iterable of
    values). A jdn value is itself a range and a week value a 2-tuple, so
    for those axes only the other container forms count; str is never a
    container."""
    if axis is Axis.jdn:
        return not isinstance(raw, (list, tuple, set, frozenset))
    if axis is Axis.week:
        return not isinstance(raw, (list, set, frozenset))
    return not isinstance(raw, (list, tuple, set, frozenset, range))


def sort_key(axis: Axis) -> Callable:
    """The natural ordering of the axis's values: definition order for
    enums, range start for jdn, numeric/lexicographic otherwise."""
    k = axis.kind
    if k is range:  # constraint values are ranges; projected elements too
        return lambda v: v.start if isinstance(v, range) else v
    if isinstance(k, type) and issubclass(k, enum.Enum):
        return {m: i for i, m in enumerate(k)}.__getitem__
    return lambda v: v
