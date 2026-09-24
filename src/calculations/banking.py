"""Banking-specific financial metrics.

Standard corporate leverage and EV/EBITDA metrics are NOT appropriate for banks.
This module provides banking-specific calculations.
"""

from __future__ import annotations
from typing import Optional

from src.calculations.helpers import safe_pct, safe_div, is_valid
from src.models.metrics import MetricResult


def net_interest_margin(
    net_interest_income: Optional[float],
    avg_interest_earning_assets: Optional[float],
) -> MetricResult:
    """NIM = Net Interest Income / Average Interest-Earning Assets × 100."""
    value = safe_pct(net_interest_income, avg_interest_earning_assets)
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="NIM",
        unit="%",
        formula="Net Interest Income / Average Interest-Earning Assets × 100",
        inputs={"nii": net_interest_income, "assets": avg_interest_earning_assets},
        note=None if value is not None else "NII or interest-earning assets unavailable",
    )


def gnpa_ratio(
    gross_npa: Optional[float],
    gross_advances: Optional[float],
) -> MetricResult:
    """GNPA % = Gross NPA / Gross Advances × 100."""
    value = safe_pct(gross_npa, gross_advances)
    if value is None:
        note = "GNPA or advances unavailable"
    elif value > 5.0:
        note = f"GNPA above 5% — elevated asset quality stress"
    else:
        note = None
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="GNPA %",
        unit="%",
        formula="Gross NPA / Gross Advances × 100",
        inputs={"gross_npa": gross_npa, "gross_advances": gross_advances},
        note=note,
    )


def nnpa_ratio(
    net_npa: Optional[float],
    net_advances: Optional[float],
) -> MetricResult:
    """NNPA % = Net NPA / Net Advances × 100."""
    value = safe_pct(net_npa, net_advances)
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="NNPA %",
        unit="%",
        formula="Net NPA / Net Advances × 100",
        inputs={"net_npa": net_npa, "net_advances": net_advances},
        note=None if value is not None else "NNPA or net advances unavailable",
    )


def provision_coverage_ratio(
    provisions: Optional[float],
    gross_npa: Optional[float],
) -> MetricResult:
    """PCR = Provisions / Gross NPA × 100."""
    value = safe_pct(provisions, gross_npa)
    if value is None:
        note = "Provisions or GNPA unavailable"
    elif value < 60.0:
        note = f"PCR below 60% — book may be under-provisioned"
    else:
        note = None
    return MetricResult(
        value=round(value, 1) if value is not None else None,
        label="Provision Coverage Ratio",
        unit="%",
        formula="Loan Loss Provisions / Gross NPA × 100",
        inputs={"provisions": provisions, "gross_npa": gross_npa},
        note=note,
    )


def casa_ratio(
    casa_deposits: Optional[float],
    total_deposits: Optional[float],
) -> MetricResult:
    """CASA Ratio = CASA Deposits / Total Deposits × 100."""
    value = safe_pct(casa_deposits, total_deposits)
    return MetricResult(
        value=round(value, 1) if value is not None else None,
        label="CASA Ratio",
        unit="%",
        formula="Current + Savings Account Deposits / Total Deposits × 100",
        inputs={"casa": casa_deposits, "total_deposits": total_deposits},
        note=None if value is not None else "CASA or total deposits unavailable",
    )


def credit_cost(
    provisions: Optional[float],
    avg_advances: Optional[float],
) -> MetricResult:
    """Credit Cost = Provisions / Average Advances × 100."""
    value = safe_pct(provisions, avg_advances)
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="Credit Cost",
        unit="%",
        formula="Provisions / Average Advances × 100",
        inputs={"provisions": provisions, "avg_advances": avg_advances},
        note=None if value is not None else "Provisions or advances unavailable",
    )


def cost_to_income_ratio(
    operating_expenses: Optional[float],
    net_income: Optional[float],
) -> MetricResult:
    """Cost-to-Income = Operating Expenses / (NII + Other Income) × 100."""
    value = safe_pct(operating_expenses, net_income)
    if value is None:
        note = "Operating expenses or income unavailable"
    elif value > 60.0:
        note = f"C/I above 60% — expense efficiency concern"
    else:
        note = None
    return MetricResult(
        value=round(value, 1) if value is not None else None,
        label="Cost-to-Income",
        unit="%",
        formula="Operating Expenses / Net Total Income × 100",
        inputs={"opex": operating_expenses, "income": net_income},
        note=note,
    )
