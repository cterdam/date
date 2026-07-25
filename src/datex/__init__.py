"""datex — symbolic day-sets over the unbounded Julian Day Number universe.

Exact constraints, a gapless set algebra, and sorted joint projection across
calendar systems; every day is ultimately a JDN >= 1, and every answer is
exact.
"""

from .axis import Axis
from .core import Date
from .values import CnDay, CnMonth, Dizhi, Month, Tiangan, Weekday, Zodiac

__version__ = "0.1.1"

__all__ = [
    "Axis",
    "CnDay",
    "CnMonth",
    "Date",
    "Dizhi",
    "Month",
    "Tiangan",
    "Weekday",
    "Zodiac",
    "__version__",
]
