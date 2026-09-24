"""Insurance-specific financial metrics."""

from __future__ import annotations
from typing import Optional

from src.calculations.helpers import safe_pct
from src.models.metrics import MetricResult


def vnb_margin(
    vnb: Optional[float],
    ape: Optional[float],
) -> MetricResult:
    """VNB Margin = Value of New Business / Annualized Premium Equivalent × 100."""
    value = safe_pct(vnb, ape)
    return MetricResult(
        value=round(value, 1) if value is not None else None,
        label="VNB Margin",
        unit="%",
        formula="VNB / APE × 100",
        inputs={"vnb": vnb, "ape": ape},
        note=None if value is not None else "VNB or APE unavailable",
    )


def combined_ratio(
    claims_ratio: Optional[float],
    expense_ratio: Optional[float],
) -> MetricResult:
    """Combined Ratio = Claims Ratio + Expense Ratio (general insurance).

    Below 100%: underwriting profit.
    Above 100%: underwriting loss.
    """
    if claims_ratio is None or expense_ratio is None:
        return MetricResult(value=None, label="Combined Ratio", unit="%",
                            note="Claims ratio or expense ratio unavailable")
    value = claims_ratio + expense_ratio
    note = None
    if value > 100:
        note = "Above 100%: underwriting loss (investment income may still yield profit)"
    return MetricResult(
        value=round(value, 1),
        label="Combined Ratio",
        unit="%",
        formula="Claims Ratio + Expense Ratio",
        inputs={"claims_ratio": claims_ratio, "expense_ratio": expense_ratio},
        note=note,
    )


def solvency_ratio_check(
    solvency_ratio: Optional[float],
    required_minimum: float = 150.0,
) -> MetricResult:
    """Solvency ratio with regulatory context (IRDAI minimum: 150%)."""
    if solvency_ratio is None:
        return MetricResult(value=None, label="Solvency Ratio", unit="%",
                            note="Solvency ratio unavailable")
    note = None
    if solvency_ratio < required_minimum:
        note = f"Below regulatory minimum of {required_minimum}%"
    return MetricResult(
        value=round(solvency_ratio, 1),
        label="Solvency Ratio",
        unit="%",
        formula="Available Solvency Margin / Required Solvency Margin × 100",
        inputs={"solvency_ratio": solvency_ratio, "required_minimum": required_minimum},
        note=note,
    )
