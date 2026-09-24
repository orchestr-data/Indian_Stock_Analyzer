"""Leverage and solvency metrics.

Definitions:
  Debt/Equity       = Interest-Bearing Debt / Shareholders' Equity
  Net Debt          = Interest-Bearing Debt − Cash and Cash Equivalents
  Net Debt/EBITDA   = Net Debt / EBITDA  (negative = net cash company)
  Interest Coverage = EBIT / Interest Expense
  Debt/Assets       = Total Debt / Total Assets
"""

from __future__ import annotations
from typing import Optional

from src.calculations.helpers import safe_div, is_valid
from src.models.metrics import MetricResult


def debt_equity(
    borrowings: Optional[float],
    shareholders_equity: Optional[float],
) -> MetricResult:
    """Debt / Equity ratio."""
    formula = "Interest-Bearing Debt / Shareholders' Equity"
    val, note = safe_div(borrowings, shareholders_equity)

    if val is not None and shareholders_equity < 0:  # type: ignore[operator]
        return MetricResult(
            value=None, label="Debt/Equity", unit="x", formula=formula,
            inputs={"borrowings": borrowings, "equity": shareholders_equity},
            note="Equity is negative — D/E ratio not meaningful",
        )

    return MetricResult(
        value=round(val, 2) if val is not None else None,
        label="Debt/Equity", unit="x", formula=formula,
        inputs={"borrowings": borrowings, "equity": shareholders_equity},
        note=note if val is None else None,
    )


def net_debt(
    borrowings: Optional[float],
    cash: Optional[float],
) -> MetricResult:
    """Net Debt = Borrowings − Cash.

    Negative result means net cash position.
    """
    if not is_valid(borrowings):
        return MetricResult(value=None, label="Net Debt", unit="₹ Cr",
                            note="Borrowings unavailable")
    cash_val = cash if is_valid(cash) else 0.0
    value = borrowings - cash_val  # type: ignore[operator]
    note = "Net cash position" if value < 0 else None
    return MetricResult(
        value=round(value, 2),
        label="Net Debt",
        unit="₹ Cr",
        formula="Borrowings − Cash and Cash Equivalents",
        inputs={"borrowings": borrowings, "cash": cash_val},
        note=note,
    )


def net_debt_ebitda(
    borrowings: Optional[float],
    cash: Optional[float],
    ebitda: Optional[float],
) -> MetricResult:
    """Net Debt / EBITDA.

    Negative result: net cash company.
    Not meaningful when EBITDA is negative or zero.
    """
    formula = "( Borrowings − Cash ) / EBITDA"

    if not is_valid(ebitda):
        return MetricResult(value=None, label="Net Debt/EBITDA", unit="x", formula=formula,
                            note="EBITDA unavailable")
    if ebitda <= 0:
        return MetricResult(value=None, label="Net Debt/EBITDA", unit="x", formula=formula,
                            inputs={"ebitda": ebitda},
                            note="Net Debt/EBITDA not meaningful when EBITDA ≤ 0")

    nd_result = net_debt(borrowings, cash)
    if nd_result.value is None:
        return MetricResult(value=None, label="Net Debt/EBITDA", unit="x", formula=formula,
                            note="Net debt unavailable")

    value = nd_result.value / ebitda  # type: ignore[operator]
    return MetricResult(
        value=round(value, 2),
        label="Net Debt/EBITDA",
        unit="x",
        formula=formula,
        inputs={"net_debt": nd_result.value, "ebitda": ebitda},
    )


def interest_coverage(
    ebit: Optional[float],
    interest_expense: Optional[float],
) -> MetricResult:
    """Interest Coverage = EBIT / Interest Expense.

    Below 1.0: interest exceeds EBIT.
    Below 0: negative EBIT.
    """
    formula = "EBIT / Interest Expense"

    if not is_valid(ebit) or not is_valid(interest_expense):
        return MetricResult(value=None, label="Interest Coverage", unit="x", formula=formula,
                            note="EBIT or interest expense unavailable")
    if interest_expense <= 0:
        return MetricResult(
            value=None, label="Interest Coverage", unit="x", formula=formula,
            inputs={"ebit": ebit, "interest": interest_expense},
            note="Interest expense is zero or negative — coverage not applicable",
        )

    value = ebit / interest_expense  # type: ignore[operator]
    note = None
    if value < 0:
        note = "Negative: EBIT is negative"
    elif value < 1.0:
        note = "Below 1.0: interest expense exceeds EBIT"

    return MetricResult(
        value=round(value, 2),
        label="Interest Coverage",
        unit="x",
        formula=formula,
        inputs={"ebit": ebit, "interest": interest_expense},
        note=note,
    )


def debt_to_assets(
    borrowings: Optional[float],
    total_assets: Optional[float],
) -> MetricResult:
    """Total Debt / Total Assets."""
    val, note = safe_div(borrowings, total_assets)
    return MetricResult(
        value=round(val, 3) if val is not None else None,
        label="Debt/Assets",
        unit="x",
        formula="Interest-Bearing Debt / Total Assets",
        inputs={"borrowings": borrowings, "total_assets": total_assets},
        note=note if val is None else None,
    )
