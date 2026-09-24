"""Period and statement type models."""

from __future__ import annotations
from enum import Enum
from datetime import date
from typing import Optional
from pydantic import BaseModel, field_validator


class PeriodType(str, Enum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    TTM = "ttm"
    HALF_YEARLY = "half_yearly"


class StatementType(str, Enum):
    CONSOLIDATED = "Consolidated"
    STANDALONE = "Standalone"
    UNKNOWN = "Unknown"


class Period(BaseModel):
    """Represents a financial reporting period."""

    period_type: PeriodType
    fiscal_year: int  # e.g. 2026 means FY2026 (April 2025 - March 2026)
    fiscal_quarter: Optional[int] = None  # 1-4, None for annual/TTM
    period_end_date: Optional[date] = None
    ttm_flag: bool = False

    @field_validator("fiscal_quarter")
    @classmethod
    def quarter_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in (1, 2, 3, 4):
            raise ValueError("fiscal_quarter must be 1-4")
        return v

    @property
    def label(self) -> str:
        """Human-readable period label."""
        if self.period_type == PeriodType.ANNUAL:
            return f"FY{self.fiscal_year}"
        if self.period_type == PeriodType.QUARTERLY and self.fiscal_quarter:
            return f"Q{self.fiscal_quarter} FY{self.fiscal_year}"
        if self.period_type == PeriodType.TTM and self.period_end_date:
            return f"TTM {self.period_end_date.strftime('%b %Y')}"
        return f"FY{self.fiscal_year}"

    @property
    def sort_key(self) -> tuple[int, int, int]:
        """Sortable key: (year, quarter_or_0, type_order)."""
        type_order = {PeriodType.ANNUAL: 0, PeriodType.QUARTERLY: 1, PeriodType.TTM: 2}
        q = self.fiscal_quarter or 0
        return (self.fiscal_year, q, type_order.get(self.period_type, 9))

    def __lt__(self, other: Period) -> bool:
        return self.sort_key < other.sort_key

    def __le__(self, other: Period) -> bool:
        return self.sort_key <= other.sort_key

    def __gt__(self, other: Period) -> bool:
        return self.sort_key > other.sort_key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Period):
            return NotImplemented
        return self.sort_key == other.sort_key

    def __hash__(self) -> int:
        return hash(self.sort_key)


def make_annual_period(fiscal_year: int) -> Period:
    """Convenience constructor for an annual period."""
    return Period(
        period_type=PeriodType.ANNUAL,
        fiscal_year=fiscal_year,
        period_end_date=date(fiscal_year, 3, 31),
    )


def make_quarterly_period(fiscal_year: int, quarter: int) -> Period:
    """Convenience constructor for a quarterly period."""
    quarter_end_months = {1: (6, 30), 2: (9, 30), 3: (12, 31), 4: (3, 31)}
    month, day = quarter_end_months[quarter]
    end_year = fiscal_year if quarter < 4 else fiscal_year
    calendar_year = fiscal_year - 1 if quarter <= 3 else fiscal_year
    return Period(
        period_type=PeriodType.QUARTERLY,
        fiscal_year=fiscal_year,
        fiscal_quarter=quarter,
        period_end_date=date(calendar_year if quarter < 4 else fiscal_year, month, day),
    )
