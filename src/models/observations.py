"""Observation models — structured factual findings, no buy/sell verdicts."""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ObservationCategory(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    WARNING = "warning"
    INVESTIGATE = "investigate"
    DATA_QUALITY = "data_quality"


class ObservationSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Observation(BaseModel):
    """A single factual observation about a company metric.

    Severity indicates how important this is to investigate — not an investment rating.
    """

    category: ObservationCategory
    severity: ObservationSeverity
    metric: str
    period: Optional[str] = None
    starting_value: Optional[float] = None
    ending_value: Optional[float] = None
    starting_label: Optional[str] = None
    ending_label: Optional[str] = None
    message: str
    reason: Optional[str] = None
    suggested_investigation: Optional[str] = None
    unit: str = ""

    @property
    def value_change_display(self) -> str:
        if self.starting_value is None or self.ending_value is None:
            return ""
        fmt = f".1f" if self.unit in ("%", "x") else ".0f"
        s = f"{self.starting_value:{fmt}}{self.unit}"
        e = f"{self.ending_value:{fmt}}{self.unit}"
        return f"{s} → {e}"
