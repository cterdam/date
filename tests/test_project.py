"""Unit tests for Date.project — the one read-out."""

import datetime
import itertools
import unittest

from datex import Axis, CnDay, CnMonth, Date, Dizhi, Month, Tiangan, Weekday, Zodiac

_REF = 2_451_545  # 2000-01-01 (J2000.0)


class ContractTest(unittest.TestCase):
    def test_takes_one_tuple_of_axes(self):
        d = Date(year=2026)
        with self.assertRaises(TypeError):
            d.project([Axis.month])
        with self.assertRaises(TypeError):
            d.project(Axis.month)
        with self.assertRaises(TypeError):
            d.project(("month",))
        with self.assertRaises(ValueError):
            d.project(())
        with self.assertRaises(ValueError):
            d.project((Axis.month, Axis.month))

    def test_elements_are_tuples_of_the_same_arity(self):
        for t in Date(year=2026).project((Axis.month,)):
            self.assertIsInstance(t, tuple)
            self.assertEqual(len(t), 1)
        for t in Date(year=2026, month=1).project((Axis.month, Axis.weekday)):
            self.assertEqual(len(t), 2)

    def test_iterators_are_independent(self):
        d = Date(year=2026)
        i1, i2 = d.project((Axis.month,)), d.project((Axis.month,))
        self.assertEqual(next(i1), (Month.JAN,))
        self.assertEqual(list(i2), [(m,) for m in Month])
        self.assertEqual(list(i1), [(m,) for m in Month][1:])

    def test_sorted_and_duplicate_free(self):
        self.assertEqual(
            list(Date(year=2026).project((Axis.month,))), [(m,) for m in Month]
        )
        self.assertEqual(
            list(Date(year=2026).project((Axis.weekday,))), [(w,) for w in Weekday]
        )


class JdnRunTest(unittest.TestCase):
    def test_runs_are_maximally_contiguous(self):
        got = list(Date(jdn=[range(1, 3), range(3, 5), range(7, 9)]).project((Axis.jdn,)))
        self.assertEqual(got, [(range(1, 5),), (range(7, 9),)])

    def test_union_coalesces_across_terms(self):
        d = Date(jdn=range(1, 3)) | Date(jdn=range(3, 5))
        self.assertEqual(list(d.project((Axis.jdn,))), [(range(1, 5),)])

    def test_month_runs(self):
        p = Date(month=9).project((Axis.jdn,))
        (r0,), (r1,) = itertools.islice(p, 2)
        self.assertEqual(len(r0), 30)
        self.assertEqual(len(r1), 30)
        self.assertGreater(r1.start, r0.stop)  # non-adjacent: maximal

    def test_contains_agrees_with_runs(self):
        # membership and the enumerator are independent implementations
        d = Date(year=2026, weekday=Weekday.MON)
        runs = [r for (r,) in d.project((Axis.jdn,))]
        self.assertEqual(len(runs), 52)
        for r in runs:
            self.assertIn(r.start, d)
            self.assertIn(r.stop - 1, d)
            self.assertNotIn(r.start - 1, d)
            self.assertNotIn(r.stop, d)

    def test_joint_with_jdn_splits_at_constancy_boundaries(self):
        got = list(Date(year=2026, month=1).project((Axis.jdn, Axis.weekday)))
        self.assertEqual(len(got), 31)  # weekday changes daily
        (r0, w0), (r1, w1) = got[0], got[1]
        self.assertEqual((len(r0), len(r1)), (1, 1))
        self.assertEqual(r1.start, r0.stop)
        self.assertEqual(int(w1), int(w0) % 7 + 1)

    def test_unbounded_tail_raises(self):
        with self.assertRaises(NotImplementedError):
            next(Date().project((Axis.jdn,)))
        with self.assertRaises(NotImplementedError):
            next((Date() - Date(year=2026)).project((Axis.jdn,)))
        # an always-true negative on a non-monotone axis is cleaned away
        with self.assertRaises(NotImplementedError):
            next((Date() - Date(day=32)).project((Axis.jdn,)))
        # a full-codomain positive atom is cleaned away
        with self.assertRaises(NotImplementedError):
            next(Date(weekday=list(range(1, 8))).project((Axis.jdn,)))

    def test_union_emergent_tail_raises(self):
        with self.assertRaises(NotImplementedError):
            list((Date(leap=True) | Date(leap=False)).project((Axis.jdn,)))
        # a BOUNDED astro term must not disable the certificate
        d = Date(leap=True) | Date(leap=False) | Date(cn_year=2000, cn_day="初一")
        with self.assertRaises(NotImplementedError):
            list(d.project((Axis.jdn,)))

    def test_bounded_unions_do_not_false_positive(self):
        got = list((Date(year=1999) | Date(year=2001)).project((Axis.jdn,)))
        self.assertEqual(len(got), 2)  # two year-runs, no tail alarm
        d = Date(weekday=Weekday.MON) | Date(year=2026)
        (r0,), (r1,) = itertools.islice(d.project((Axis.jdn,)), 2)
        self.assertLess(r0.stop, r1.start)

    def test_empty_sets_project_to_nothing(self):
        self.assertEqual(list(Date(month=2, day=30).project((Axis.jdn,))), [])
        self.assertEqual(list(Date(day=32).project((Axis.jdn,))), [])
        self.assertEqual(
            list((Date(doy=366) - Date(leap=True)).project((Axis.jdn,))), []
        )


class StreamTest(unittest.TestCase):
    def test_leap_year_stream(self):
        p = Date(month=2, day=29).project((Axis.year,))
        self.assertEqual(
            list(itertools.islice(p, 3)), [(-4712,), (-4708,), (-4704,)]
        )

    def test_universe_minus_a_year_projects_years(self):
        p = (Date() - Date(year=2026)).project((Axis.year,))
        head = [y for (y,) in itertools.islice(p, 3)]
        self.assertEqual(head, [-4713, -4712, -4711])  # jdn 1 is -4713-11-25

    def test_sorted_unreachable_tail_semantics(self):
        # weekday-first over an infinite set: the MON prefix repeats forever
        p = Date(month=2, day=29).project((Axis.weekday, Axis.year))
        head = list(itertools.islice(p, 3))
        self.assertTrue(all(w is Weekday.MON for w, _ in head))
        self.assertEqual([y for _, y in head], sorted(y for _, y in head))

    def test_joint_is_not_a_product(self):
        got = list(Date(month=9, day=2).project((Axis.doy, Axis.leap)))
        self.assertEqual(got, [(245, False), (246, True)])

    def test_union_merges_monotone_terms(self):
        d = Date(year=1999) | Date(year=2001)
        self.assertEqual(list(d.project((Axis.year,))), [(1999,), (2001,)])

    def test_union_merges_monotone_terms_joint(self):
        d = Date(year=2001, month=1) | Date(year=1999, month=2)
        self.assertEqual(
            list(d.project((Axis.year, Axis.month))),
            [(1999, Month.FEB), (2001, Month.JAN)],
        )


class DifferentialTest(unittest.TestCase):
    def test_seeded_differential_against_brute_force(self):
        """The algebra and enumerator versus independent per-day evaluation
        over a two-year window: membership, run coverage, maximality, and
        subset relations must all agree with brute force."""
        import random

        from datex import arithmetic as ar
        from datex import chinese as ch

        LO, HI = ar.civil2jdn(2025, 1, 1), ar.civil2jdn(2027, 1, 1)
        window = Date(jdn=range(LO, HI))
        days = range(LO, HI)
        hole = range(LO + 300, LO + 450)
        atoms = [
            (Date(weekday=Weekday.MON), lambda j: j % 7 == 0),
            (Date(month=[2, 9]), lambda j: ar.jdn2civil(j)[1] in (2, 9)),
            (Date(day=list(range(1, 8))), lambda j: ar.jdn2civil(j)[2] < 8),
            (Date(doy=[1, 100, 366]), lambda j: ar.jdn2doy(j) in (1, 100, 366)),
            (Date(year=2025), lambda j: j < ar.civil2jdn(2026, 1, 1)),
            (Date(week=[(2025, 10), (2026, 10)]),
             lambda j: ar.jdn2week(j) in ((2025, 10), (2026, 10))),
            (Date(jdn=hole), lambda j: j in hole),
            (Date(zodiac="Virgo"), lambda j: ar.jdn2zodiac(j) is Zodiac.VIRGO),
            (Date(cn_day_dizhi="子"), lambda j: (j + 49) % 60 % 12 == 0),
            (Date(cn_day="初一"), lambda j: ch.jdn2cn_day(j) is CnDay.初一),
        ]
        brutes = [(d, frozenset(j for j in days if f(j))) for d, f in atoms]
        ops = [
            (lambda a, b: a & b, frozenset.__and__),
            (lambda a, b: a | b, frozenset.__or__),
            (lambda a, b: a - b, frozenset.__sub__),
            (lambda a, b: a ^ b, frozenset.__xor__),
        ]
        rng = random.Random(20260721)
        for _ in range(25):
            (d1, s1), (d2, s2), (d3, s3) = rng.sample(brutes, 3)
            (od1, os1), (od2, os2) = (ops[rng.randrange(4)] for _ in range(2))
            d, s = od2(od1(d1, d2), d3), os2(os1(s1, s2), s3)
            got = []
            for (r,) in (d & window).project((Axis.jdn,)):
                got.extend(r)
                self.assertNotIn(r.start - 1, s)  # maximality on both edges
                self.assertTrue(r.stop == HI or r.stop not in s)
            self.assertEqual(frozenset(got), s)
        for _ in range(8):
            (d1, s1), (d2, s2) = rng.sample(brutes, 2)
            self.assertEqual((d1 & window) <= (d2 & window), s1 <= s2)
            self.assertEqual((d1 & window) == (d2 & window), s1 == s2)


class AstroProjectionTest(unittest.TestCase):
    def test_expand_a_concrete_day(self):
        row = next(iter(Date(jdn=range(_REF, _REF + 1)).project(tuple(Axis))))
        iso = datetime.date(2000, 1, 1).isocalendar()
        self.assertEqual(
            row,
            (range(_REF, _REF + 1), 2000, 1, 1, Weekday.SAT, (iso[0], iso[1]),
             1, True, Zodiac.CAPRICORN, 1999, Tiangan.己, Dizhi.卯,
             CnMonth.十一月, Tiangan.丙, Dizhi.子, CnDay.廿五, Tiangan.戊,
             Dizhi.午),
        )

    def test_finite_codomain_over_astro_infinite_terminates(self):
        # once undecidable without saturation certificates; now each candidate
        # value is decided by the emptiness machinery
        got = list(Date(cn_month="八月").project((Axis.cn_month,)))
        self.assertEqual(got, [(CnMonth.八月,)])

    def test_lunar_year_months_in_order(self):
        got = [m for (m,) in Date(cn_year=1999).project((Axis.cn_month,))]
        self.assertEqual(got, [m for m in CnMonth if not m.leap])


if __name__ == "__main__":
    unittest.main()
