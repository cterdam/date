"""Dev-time generator for the sexagenary day-pillar goldens in
test_arithmetic.py — the drift check of our in-house pillar arithmetic
against an independent implementation.

Requires sxtwl (NOT a package dependency; install it in a scratch venv).
Run manually and paste the output over _PILLAR_GOLDENS when extending it.
"""

import datetime

import sxtwl

SAMPLES = [
    (1949, 10, 1), (2000, 1, 1), (2026, 7, 11), (1984, 2, 2),
    (1912, 2, 18), (2017, 1, 1), (1970, 1, 1), (2026, 1, 1), (1999, 12, 31),
    (2044, 5, 5), (1900, 3, 1), (2100, 2, 28), (1961, 4, 14), (1993, 12, 8),
]

if __name__ == "__main__":
    for y, m, d in SAMPLES:
        gz = sxtwl.fromSolar(y, m, d).getDayGZ()
        print(f"    ({y}, {m}, {d}, {gz.tg}, {gz.dz}),")
    # sanity: the anchor used by date.arithmetic
    a = datetime.date(1949, 10, 1).toordinal() + 1_721_425
    print(f"# jdn(1949-10-01) = {a}; K = (-a) % 60 = {(-a) % 60}")
