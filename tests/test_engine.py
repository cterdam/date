"""Engine-level guarantees: the structural emptiness certificates, the
closed-form seeks (checked day-for-day against brute force), and guards
against the enumeration cost regressing to day-walking."""

import time
import unittest

from datex import Axis, Date, Month, Weekday
from datex import arithmetic as ar


def days_of(d, lo, hi):
    """The set's member days within [lo, hi) via projection."""
    out = []
    for (r,) in (d & Date(jdn=range(lo, hi))).project((Axis.jdn,)):
        out.extend(r)
    return out


def brute(preds, lo, hi):
    """The same days by evaluating every predicate on every day."""
    return [j for j in range(lo, hi) if all(p(j) for p in preds)]


class CertificateTest(unittest.TestCase):
    def test_pillar_parity_all_levels(self):
        # stem index and branch index share the pillar index's parity, so
        # 甲 (0, even) never pairs with 丑 (1, odd) at any level
        for tg, dz in (
            ("cn_year_tiangan", "cn_year_dizhi"),
            ("cn_month_tiangan", "cn_month_dizhi"),
            ("cn_day_tiangan", "cn_day_dizhi"),
        ):
            self.assertFalse(Date(**{tg: "甲", dz: "丑"}), (tg, dz))
            self.assertTrue(Date(**{tg: "甲", dz: "子"}), (tg, dz))

    def test_pillar_parity_is_instant(self):
        t0 = time.perf_counter()
        bool(Date(cn_month_tiangan="甲", cn_month_dizhi="丑"))
        self.assertLess(time.perf_counter() - t0, 0.05)

    def test_parity_empty_equals_empty(self):
        self.assertEqual(Date(day=32), Date(cn_year_tiangan="甲", cn_year_dizhi="丑"))

    def test_cn_year_pins_year_pillar(self):
        # 2024 - 4 = 2020: stem index 0 (甲), branch index 4 (辰)
        self.assertTrue(Date(cn_year=2024, cn_year_tiangan="甲"))
        self.assertTrue(Date(cn_year=2024, cn_year_dizhi="辰"))
        self.assertFalse(Date(cn_year=2024, cn_year_tiangan="乙"))
        self.assertFalse(Date(cn_year=2024, cn_year_dizhi="卯"))
        self.assertTrue(Date(cn_year=[2024, 2025], cn_year_tiangan="乙"))

    def test_month_day_shape(self):
        self.assertFalse(Date(month=2, day=30))
        self.assertFalse(Date(month=[4, 6, 9, 11], day=31))
        self.assertTrue(Date(month=2, day=29))
        self.assertTrue(Date(month=[2, 3], day=31))

    def test_month_doy_shape(self):
        self.assertFalse(Date(month=1, doy=32))
        self.assertFalse(Date(month=12, doy=1))
        self.assertTrue(Date(month=12, doy=366))
        self.assertTrue(Date(month=3, doy=60))  # Mar 1 non-leap
        self.assertFalse(Date(month=3, doy=59))  # doy 59 is always in Feb

    def test_doy_leap_shape(self):
        self.assertFalse(Date(doy=366, leap=False))
        self.assertTrue(Date(doy=366, leap=True))
        self.assertTrue(Date(doy=365, leap=False))


class SeekDifferentialTest(unittest.TestCase):
    """Seek-driven enumeration must agree with per-day brute force."""

    LO, HI = 2_460_311, 2_461_100  # 2024-01-01 .. ~2026-03

    def check(self, d, *preds):
        self.assertEqual(days_of(d, self.LO, self.HI), brute(preds, self.LO, self.HI))

    def test_weekday(self):
        self.check(Date(weekday=Weekday.MON), lambda j: j % 7 == 0)

    def test_weekday_negative(self):
        self.check(
            Date() - Date(weekday=[Weekday.SAT, Weekday.SUN]),
            lambda j: j % 7 + 1 not in (6, 7),
        )

    def test_day(self):
        self.check(Date(day=31), lambda j: ar.jdn2day(j) == 31)

    def test_day_negative(self):
        self.check(
            Date() - Date(day=list(range(2, 32))), lambda j: ar.jdn2day(j) == 1
        )

    def test_doy(self):
        self.check(Date(doy=[1, 200, 366]), lambda j: ar.jdn2doy(j) in (1, 200, 366))

    def test_month(self):
        self.check(Date(month=Month.FEB), lambda j: ar.jdn2month(j) == 2)

    def test_day_pillars(self):
        self.check(
            Date(cn_day_tiangan="甲"), lambda j: (j + ar.PILLAR_K) % 10 == 0
        )
        self.check(
            Date(cn_day_dizhi="子"), lambda j: (j + ar.PILLAR_K) % 12 == 0
        )

    def test_joint_modular(self):
        # weekday ∧ both day pillars: moduli 7, 10, 12 jointly
        self.check(
            Date(weekday=Weekday.MON, cn_day_tiangan="甲", cn_day_dizhi="子"),
            lambda j: j % 7 == 0 and (j + ar.PILLAR_K) % 60 == 0,
        )

    def test_civil_modular_mix(self):
        self.check(
            Date(month=2, day=29, weekday=Weekday.THU),
            lambda j: ar.jdn2civil(j)[1:] == (2, 29) and j % 7 == 3,
        )

    def test_negative_month_positive_day(self):
        self.check(
            Date(day=13) - Date(month=[1, 2, 3, 4, 5, 6]),
            lambda j: ar.jdn2day(j) == 13 and ar.jdn2month(j) > 6,
        )


class CostGuardTest(unittest.TestCase):
    """The audited cliffs must not regress to day-walking."""

    def test_month_doy_joint(self):
        t0 = time.perf_counter()
        rows = list(Date(month=[9, 10]).project((Axis.month, Axis.doy)))
        self.assertLess(time.perf_counter() - t0, 5.0)  # was 35s pre-seek
        self.assertEqual(len(rows), 63)

    def test_mixed_period_emptiness(self):
        # lcm window here is 2,921,940 days; must answer in far under a second
        t0 = time.perf_counter()
        self.assertTrue(bool(Date(month=2, day=29, cn_day_tiangan="甲")))
        self.assertFalse(bool(Date(month=2, day=30, cn_day_tiangan="甲")))
        self.assertLess(time.perf_counter() - t0, 2.0)

    def test_semantic_equality_fast(self):
        t0 = time.perf_counter()
        self.assertEqual(Date(doy=366), Date(doy=366, leap=True))
        self.assertEqual(Date(month=2, day=29), Date(doy=60, leap=True))
        self.assertLess(time.perf_counter() - t0, 2.0)


if __name__ == "__main__":
    unittest.main()
