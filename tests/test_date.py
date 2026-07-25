"""Unit tests for date.core.Date — the set object and its algebra."""

import itertools
import unittest

from datex import Axis, Date, Month, Weekday, Zodiac

_REF = 2_451_545  # 2000-01-01 (J2000.0), a Saturday


def days(d):
    """Day-count of a finite Date, by the stdlib spelling."""
    return sum(len(r) for (r,) in d.project((Axis.jdn,)))


class ConstructionTest(unittest.TestCase):
    def test_concrete_day(self):
        d = Date(year=2000, month=1, day=1)
        self.assertEqual(list(d.project((Axis.jdn,))), [(range(_REF, _REF + 1),)])
        self.assertEqual(days(d), 1)

    def test_iterable_is_disjunction(self):
        self.assertEqual(days(Date(year=[1999, 2001], month=1, day=1)), 2)

    def test_contradiction_is_empty(self):
        self.assertFalse(Date(year=2000, month=1, day=1, weekday=Weekday.TUE))
        self.assertFalse(Date(month=2, day=30))
        self.assertFalse(Date(month=[4, 6, 9, 11], day=31))
        self.assertFalse(Date(zodiac=Zodiac.VIRGO, month=10))

    def test_empty_iterable_is_empty(self):
        self.assertFalse(Date(month=[]))

    def test_no_constraints_is_the_universe(self):
        self.assertTrue(Date())
        self.assertIn(1, Date())

    def test_closed_vocabularies_raise(self):
        with self.assertRaises(ValueError):
            Date(month=13)
        with self.assertRaises(ValueError):
            Date(weekday=8)
        with self.assertRaises(ValueError):
            Date(zodiac="Vurgo")

    def test_unsatisfiable_values_are_empty_not_errors(self):
        self.assertFalse(Date(day=32))
        self.assertFalse(Date(doy=0))
        self.assertFalse(Date(doy=400))
        self.assertFalse(Date(jdn=range(0, 1)))  # before the universe
        self.assertFalse(Date(week=(2005, 53)))  # 2005 has 52 weeks
        self.assertTrue(Date(day=31))

    def test_wrong_types_raise(self):
        with self.assertRaises(TypeError):
            Date(month="9")
        with self.assertRaises(TypeError):
            Date(leap=1)
        with self.assertRaises(TypeError):
            Date(weekday=True)
        with self.assertRaises(TypeError):
            Date(birthday=1)  # unknown axis
        with self.assertRaises(TypeError):
            Date(jdn=_REF)  # a single day is range(x, x + 1)
        with self.assertRaises(TypeError):
            Date(jdn=range(1, 10, 2))

    def test_jdn_values_coalesce_at_construction(self):
        self.assertEqual(repr(Date(jdn=[range(1, 3), range(3, 5)])), "Date(jdn=range(1, 5))")

    def test_value_flavors(self):
        self.assertTrue(Date(zodiac="Virgo"))
        self.assertTrue(Date(cn_day_tiangan="甲"))
        self.assertEqual(days(Date(jdn=range(2_451_545, 2_451_552))), 7)
        self.assertEqual(days(Date(jdn=[range(1, 3), range(7, 9)])), 4)
        self.assertEqual(days(Date(week=(2004, 53))), 7)

    def test_month_enum_and_int_interchange(self):
        self.assertEqual(Date(month=Month.SEP), Date(month=9))


class ProtocolTest(unittest.TestCase):
    def test_truthiness_is_nonemptiness(self):
        self.assertTrue(Date(month=9))
        self.assertFalse(Date(month=9) & Date(month=10))

    def test_contains(self):
        self.assertIn(_REF, Date(month=1))
        self.assertNotIn(_REF, Date(month=10))
        self.assertNotIn(True, Date())
        self.assertNotIn(0, Date())

    def test_day_count_spelling(self):
        self.assertEqual(days(Date(year=2026)), 365)
        self.assertEqual(days(Date(year=2024)), 366)

    def test_value_count_spelling(self):
        self.assertEqual(sum(1 for _ in Date(year=2026).project((Axis.month,))), 12)

    def test_subset_and_equality(self):
        self.assertLessEqual(Date(month=9), Date(month=[9, 10]))
        self.assertLess(Date(month=9), Date(month=[9, 10]))
        self.assertGreaterEqual(Date(month=[9, 10]), Date(month=9))
        self.assertEqual(Date(month=9) | Date(month=10), Date(month=[9, 10]))
        self.assertNotEqual(Date(month=9), Date(month=10))

    def test_repr(self):
        r = repr(Date(month=9, day=2))
        self.assertIn("Month.SEP", r)
        self.assertIn("day=2", r)
        self.assertIn("!=", repr(Date() - Date(month=2)))


class AlgebraTest(unittest.TestCase):
    def test_and_matches_conjunction(self):
        self.assertEqual(Date(month=9) & Date(day=2), Date(month=9, day=2))

    def test_and_same_axis_intersects_values(self):
        got = list((Date(month=[9, 10]) & Date(month=[10, 11])).project((Axis.month,)))
        self.assertEqual(got, [(Month.OCT,)])

    def test_and_jdn_intersects_day_sets(self):
        self.assertEqual(days(Date(jdn=range(1, 10)) & Date(jdn=range(5, 15))), 5)
        self.assertFalse(Date(jdn=range(1, 2)) & Date(jdn=range(2, 3)))

    def test_and_with_derived_operand(self):
        d = (Date(year=1999) | Date(year=2001)) & Date(month=1)
        self.assertEqual(days(d), 62)
        self.assertIn(2_451_180, d)  # 1999-01-01

    def test_or(self):
        d = Date(year=1999) | Date(year=2001)
        self.assertEqual(days(d), 730)
        self.assertNotIn(2_451_545, d)  # 2000-01-01
        got = list((Date(weekday=Weekday.SAT) | Date(weekday=Weekday.SUN)).project((Axis.weekday,)))
        self.assertEqual(got, [(Weekday.SAT,), (Weekday.SUN,)])

    def test_sub(self):
        self.assertEqual(days(Date(year=2000) - Date(month=2)), 366 - 29)
        e = Date(weekday=[Weekday.SAT, Weekday.SUN]) - Date(weekday=Weekday.SUN)
        self.assertEqual(list(e.project((Axis.weekday,))), [(Weekday.SAT,)])

    def test_xor(self):
        self.assertFalse(Date(month=9) ^ Date(month=9))
        d = Date(month=9) ^ Date(month=[9, 10])
        self.assertEqual(list(d.project((Axis.month,))), [(Month.OCT,)])

    def test_de_morgan_identity(self):
        a, b = Date(year=2000, month=[1, 2]), Date(year=2000, weekday=Weekday.MON)
        self.assertEqual(days(a - b), days(a) - days(a & b))

    def test_decree_respects_the_arithmetic_skeleton(self):
        # an astro atom cannot resurrect an arithmetically-empty set
        self.assertFalse(Date(day=32, cn_month="正月"))
        self.assertLessEqual(Date(day=32), Date(cn_month="正月"))

    def test_codomain_clipping_normalizes(self):
        self.assertEqual(Date(day=[31, 32]), Date(day=31))

    def test_emptiness_ignores_irrelevant_horizons(self):
        # a negative monotone atom far away must not slow or change the answer
        self.assertTrue(Date(weekday=Weekday.MON) - Date(year=10**9))
        self.assertFalse(Date(month=2, day=30) - Date(year=10**9))

    def test_strict_superset(self):
        self.assertGreater(Date(month=[9, 10]), Date(month=9))
        self.assertFalse(Date(month=9) > Date(month=9))

    def test_complement_blowup_guard(self):
        import functools as ft
        import operator

        big = ft.reduce(
            operator.or_,
            (Date(month=m, day=m) for m in range(1, 13)),
        ) | Date(month=1, day=2)
        with self.assertRaises(NotImplementedError):
            Date() - big

    def test_repr_forms(self):
        self.assertEqual(repr(Date()), "Date()")
        self.assertEqual(repr(Date(month=9) & Date(month=10)), "Date(<empty>)")


class CrossAxisTest(unittest.TestCase):
    def test_libra_days_in_september(self):
        got = [v for (v,) in Date(zodiac=Zodiac.LIBRA, month=9).project((Axis.day,))]
        self.assertEqual(got, list(range(23, 31)))

    def test_doy_366_pins_the_calendar(self):
        d = Date(doy=366)
        self.assertEqual(list(d.project((Axis.leap,))), [(True,)])
        self.assertEqual(list(d.project((Axis.month, Axis.day))), [(Month.DEC, 31)])

    def test_capricorn_wraps_the_year(self):
        jan = [v for (v,) in Date(zodiac="Capricorn", month=1).project((Axis.day,))]
        self.assertEqual(jan, list(range(1, 20)))
        dec = [v for (v,) in Date(zodiac="Capricorn", month=12).project((Axis.day,))]
        self.assertEqual(dec, list(range(22, 32)))

    def test_pillar_cycle_is_sixty_days(self):
        p = Date(cn_day_tiangan="甲", cn_day_dizhi="子").project((Axis.jdn,))
        (r0,), (r1,) = itertools.islice(p, 2)
        self.assertEqual(r1.start - r0.start, 60)

    def test_week_straddles_the_year(self):
        d = Date(week=(2004, 53))  # Mon 2004-12-27 … Sun 2005-01-02
        self.assertEqual(list(d.project((Axis.year,))), [(2004,), (2005,)])
        self.assertEqual(list(d.project((Axis.month,))), [(Month.JAN,), (Month.DEC,)])

    def test_week_projection(self):
        got = [w for (w,) in Date(year=2026, month=1).project((Axis.week,))]
        self.assertEqual(got, [(2026, w) for w in range(1, 6)])
        joint = list(Date(year=2026, month=1).project((Axis.week, Axis.weekday)))
        self.assertEqual(joint, sorted(joint))
        self.assertEqual(len(joint), 31)

    def test_week_disjunction_forms(self):
        self.assertEqual(days(Date(week=[(2004, 1), (2004, 2)])), 14)
        with self.assertRaises(TypeError):
            Date(week=((2004, 1), (2004, 2)))


if __name__ == "__main__":
    unittest.main()
