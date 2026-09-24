"""Metric result and calculated metric models."""

from __future__ import annotations
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import date


@dataclass
class MetricResult:
    """Result of a single metric calculation.

    Uses dataclass for lightweight use inside pure calculation functions.
    """

    value: Optional[float]
    label: str
    unit: str = ""  # "%", "x", "₹ Cr", "days", etc.
    formula: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    note: Optional[str] = None  # explanation of why value is None, or a warning
    is_available: bool = True

    def __post_init__(self) -> None:
        if self.value is None:
            self.is_available = False

    @property
    def display_value(self) -> str:
        if self.value is None:
            return self.note or "Not available"
        if self.unit == "%":
            return f"{self.value:.1f}%"
        if self.unit == "x":
            return f"{self.value:.1f}x"
        if self.unit == "days":
            return f"{self.value:.0f} days"
        return f"{self.value:.2f}"


@dataclass
class TrendPoint:
    """Single data point in a time series."""

    period_label: str
    fiscal_year: int
    value: Optional[float]
    fiscal_quarter: Optional[int] = None


@dataclass
class TrendResult:
    """Result of a trend analysis over a series of values."""

    metric_name: str
    data_points: list[TrendPoint]
    direction: str = "insufficient_history"  # improving, declining, stable, mixed
    cagr_3y: Optional[float] = None
    cagr_5y: Optional[float] = None
    cagr_10y: Optional[float] = None
    avg_3y: Optional[float] = None
    avg_5y: Optional[float] = None
    avg_10y: Optional[float] = None
    median_3y: Optional[float] = None
    median_5y: Optional[float] = None
    median_10y: Optional[float] = None
    latest: Optional[float] = None
    previous: Optional[float] = None
    abs_change: Optional[float] = None
    pct_change: Optional[float] = None
    consecutive_increases: int = 0
    consecutive_decreases: int = 0
    volatility: Optional[float] = None
    note: Optional[str] = None


from pydantic import BaseModel  # noqa: E402 — after dataclass section


class CalculatedMetric(BaseModel):
    """Persisted calculated metric row."""

    company_id: int
    statement_type: str
    period_type: str
    period_end_date: Optional[date] = None
    metric_name: str
    metric_value: Optional[float] = None
    calculation_version: str = "1.0"
    source_basis: Optional[str] = None
