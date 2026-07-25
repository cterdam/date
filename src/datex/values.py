"""The enumerated value types of the axes.

Every enum doubles as a primitive. Weekday and Month are IntEnums — their
numbers are semantic (ISO numbering, month ordinals) — so members
interchange freely with raw ints. The rest are StrEnums whose values are
the canonical string forms (Zodiac("Virgo"), Tiangan("甲"), CnMonth("閏八月")),
so members interchange freely with those strings; the Chinese enums get
their values from auto() (the member name itself), Zodiac writes the
customary capitalized forms explicitly.
"""

from __future__ import annotations

import enum
from enum import auto


def _idx(member) -> int:
    """The 0-based definition position of an enum member."""
    return list(type(member)).index(member)


class Weekday(enum.IntEnum):
    """ISO weekday: 1=Monday … 7=Sunday."""

    MON = 1
    TUE = 2
    WED = 3
    THU = 4
    FRI = 5
    SAT = 6
    SUN = 7


class Month(enum.IntEnum):
    """Gregorian month, 1=January … 12=December."""

    JAN = 1
    FEB = 2
    MAR = 3
    APR = 4
    MAY = 5
    JUN = 6
    JUL = 7
    AUG = 8
    SEP = 9
    OCT = 10
    NOV = 11
    DEC = 12


class Zodiac(enum.StrEnum):
    """Western zodiac sign, by the customary tropical date ranges."""

    ARIES = "Aries"
    TAURUS = "Taurus"
    GEMINI = "Gemini"
    CANCER = "Cancer"
    LEO = "Leo"
    VIRGO = "Virgo"
    LIBRA = "Libra"
    SCORPIO = "Scorpio"
    SAGITTARIUS = "Sagittarius"
    CAPRICORN = "Capricorn"
    AQUARIUS = "Aquarius"
    PISCES = "Pisces"


class Tiangan(enum.StrEnum):
    """天干 (heavenly stem), 甲…癸."""

    甲 = auto()
    乙 = auto()
    丙 = auto()
    丁 = auto()
    戊 = auto()
    己 = auto()
    庚 = auto()
    辛 = auto()
    壬 = auto()
    癸 = auto()

    @property
    def yinyang(self) -> str:
        return "陽" if _idx(self) % 2 == 0 else "陰"

    @property
    def wuxing(self) -> str:
        return "木木火火土土金金水水"[_idx(self)]

    @property
    def label(self) -> str:
        """The composite display form: 甲陽木 … 癸陰水."""
        return f"{self.name}{self.yinyang}{self.wuxing}"


class Dizhi(enum.StrEnum):
    """地支 (earthly branch), 子…亥."""

    子 = auto()
    丑 = auto()
    寅 = auto()
    卯 = auto()
    辰 = auto()
    巳 = auto()
    午 = auto()
    未 = auto()
    申 = auto()
    酉 = auto()
    戌 = auto()
    亥 = auto()

    @property
    def yinyang(self) -> str:
        return "陽" if _idx(self) % 2 == 0 else "陰"

    @property
    def wuxing(self) -> str:
        return "水土木木土火火土金金土水"[_idx(self)]

    @property
    def zodiac(self) -> str:
        """The Chinese zodiac animal of this branch: 鼠 … 豬."""
        return "鼠牛虎兔龍蛇馬羊猴雞狗豬"[_idx(self)]

    @property
    def label(self) -> str:
        """The composite display form: 子鼠 … 亥豬."""
        return f"{self.name}{self.zodiac}"


class CnMonth(enum.StrEnum):
    """Chinese lunisolar month, in chronological order within a year: each
    regular month followed by its potential leap (閏) month."""

    正月 = auto()
    閏正月 = auto()
    二月 = auto()
    閏二月 = auto()
    三月 = auto()
    閏三月 = auto()
    四月 = auto()
    閏四月 = auto()
    五月 = auto()
    閏五月 = auto()
    六月 = auto()
    閏六月 = auto()
    七月 = auto()
    閏七月 = auto()
    八月 = auto()
    閏八月 = auto()
    九月 = auto()
    閏九月 = auto()
    十月 = auto()
    閏十月 = auto()
    十一月 = auto()
    閏十一月 = auto()
    十二月 = auto()
    閏十二月 = auto()

    @property
    def leap(self) -> bool:
        """Whether this is a 閏 (leap) month."""
        return self.name.startswith("閏")

    @property
    def number(self) -> int:
        """The month ordinal 1-12 (a leap month shares its host's)."""
        return _idx(self) // 2 + 1


class CnDay(enum.StrEnum):
    """Chinese lunisolar day of the month, 初一 … 三十."""

    初一 = auto()
    初二 = auto()
    初三 = auto()
    初四 = auto()
    初五 = auto()
    初六 = auto()
    初七 = auto()
    初八 = auto()
    初九 = auto()
    初十 = auto()
    十一 = auto()
    十二 = auto()
    十三 = auto()
    十四 = auto()
    十五 = auto()
    十六 = auto()
    十七 = auto()
    十八 = auto()
    十九 = auto()
    二十 = auto()
    廿一 = auto()
    廿二 = auto()
    廿三 = auto()
    廿四 = auto()
    廿五 = auto()
    廿六 = auto()
    廿七 = auto()
    廿八 = auto()
    廿九 = auto()
    三十 = auto()

    @property
    def number(self) -> int:
        """The day ordinal, 1-30."""
        return _idx(self) + 1
