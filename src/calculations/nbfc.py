"""NBFC-specific financial metrics."""

from __future__ import annotations
from typing import Optional

from src.calculations.helpers import safe_pct
from src.models.metrics import MetricResult


def aum_growth(
    aum_current: Optional[float],
    aum_previous: Optional[float],
) -> MetricResult:
    """AUM Year-over-Year Growth %."""
    from src.calculations.helpers import pct_change
    value = pct_change(aum_previous, aum_current)
    return MetricResult(
        value=round(value, 1) if value is not None else None,
        label="AUM Growth",
        unit="%",
        formula="( AUM_Current − AUM_Previous ) / AUM_Previous × 100",
        inputs={"aum_current": aum_current, "aum_previous": aum_previous},
        note=None if value is not None else "AUM data unavailable",
    )


def spread(
    yield_on_advances: Optional[float],
    cost_of_borrowings: Optional[float],
) -> MetricResult:
    """Spread = Yield on Advances − Cost of Borrowings."""
    if yield_on_advances is None or cost_of_borrowings is None:
        return MetricResult(value=None, label="Spread", unit="%",
                            note="Yield or cost of borrowings unavailable")
    value = yield_on_advances - cost_of_borrowings
    return MetricResult(
        value=round(value, 2),
        label="Spread",
        unit="%",
        formula="Yield on Advances − Cost of Borrowings",
        inputs={"yield": yield_on_advances, "cost": cost_of_borrowings},
    )
