"""Working capital and asset efficiency metrics.

Definitions (using 365-day year):
  Receivable Days  = (Receivables / Revenue) × 365
  Inventory Days   = (Inventory / Cost of Goods Sold) × 365
                     Fallback: (Inventory / Revenue) × 365 if COGS unavailable
  Payable Days     = (Payables / Expenses) × 365
  CCC              = Receivable Days + Inventory Days − Payable Days
  Working Capital  = Current Assets − Current Liabilities
  Asset Turnover   = Revenue / Average Total Assets
"""

from __future__ import annotations
from typing import Optional

from src.calculations.helpers import safe_div, is_valid
from src.models.metrics import MetricResult

_DAYS_IN_YEAR = 365.0


def receivable_days(
    receivables: Optional[float],
    revenue: Optional[float],
) -> MetricResult:
    """Receivable Days = Receivables / Revenue × 365."""
    formula = "Receivables / Revenue × 365"
    val, note = safe_div(receivables, revenue)
    if val is None:
        return MetricResult(value=None, label="Receivable Days", unit="days",
                            formula=formula, note=note)
    return MetricResult(
        value=round(val * _DAYS_IN_YEAR, 1),
        label="Receivable Days",
        unit="days",
        formula=formula,
        inputs={"receivables": receivables, "revenue": revenue},
    )


def inventory_days(
    inventory: Optional[float],
    cogs: Optional[float] = None,
    revenue: Optional[float] = None,
) -> MetricResult:
    """Inventory Days.

    Uses COGS as denominator when available; falls back to Revenue.
    """
    if not is_valid(inventory):
        return MetricResult(value=None, label="Inventory Days", unit="days",
                            note="Inventory unavailable")

    if is_valid(cogs) and cogs > 0:  # type: ignore[operator]
        denom = cogs
        formula = "Inventory / COGS × 365"
        note = None
    elif is_valid(revenue) and revenue > 0:  # type: ignore[operator]
        denom = revenue
        formula = "Inventory / Revenue × 365 (COGS unavailable — Revenue used as proxy)"
        note = "Revenue used as COGS proxy — may overstate inventory days"
    else:
        return MetricResult(value=None, label="Inventory Days", unit="days",
                            note="COGS and revenue both unavailable")

    val, div_note = safe_div(inventory, denom)
    if val is None:
        return MetricResult(value=None, label="Inventory Days", unit="days",
                            formula=formula, note=div_note)
    return MetricResult(
        value=round(val * _DAYS_IN_YEAR, 1),
        label="Inventory Days",
        unit="days",
        formula=formula,
        inputs={"inventory": inventory, "denominator": denom},
        note=note,
    )


def payable_days(
    payables: Optional[float],
    expenses: Optional[float],
) -> MetricResult:
    """Payable Days = Payables / Expenses × 365."""
    formula = "Payables / Total Expenses × 365"
    val, note = safe_div(payables, expenses)
    if val is None:
        return MetricResult(value=None, label="Payable Days", unit="days",
                            formula=formula, note=note)
    return MetricResult(
        value=round(val * _DAYS_IN_YEAR, 1),
        label="Payable Days",
        unit="days",
        formula=formula,
        inputs={"payables": payables, "expenses": expenses},
    )


def cash_conversion_cycle(
    rec_days: Optional[float],
    inv_days: Optional[float],
    pay_days: Optional[float],
) -> MetricResult:
    """CCC = Receivable Days + Inventory Days − Payable Days.

    Accepts the numerical day values (not MetricResult objects).
    """
    formula = "Receivable Days + Inventory Days − Payable Days"
    if not is_valid(rec_days) or not is_valid(inv_days) or not is_valid(pay_days):
        available = {
            "receivable_days": rec_days,
            "inventory_days": inv_days,
            "payable_days": pay_days,
        }
        missing = [k for k, v in available.items() if not is_valid(v)]
        return MetricResult(
            value=None, label="Cash Conversion Cycle", unit="days", formula=formula,
            note=f"Missing: {', '.join(missing)}",
        )

    value = rec_days + inv_days - pay_days  # type: ignore[operator]
    return MetricResult(
        value=round(value, 1),
        label="Cash Conversion Cycle",
        unit="days",
        formula=formula,
        inputs={"receivable_days": rec_days, "inventory_days": inv_days,
                "payable_days": pay_days},
    )


def asset_turnover(
    revenue: Optional[float],
    total_assets_current: Optional[float],
    total_assets_previous: Optional[float] = None,
) -> MetricResult:
    """Asset Turnover = Revenue / Average Total Assets."""
    formula = "Revenue / Average Total Assets"
    if not is_valid(revenue) or not is_valid(total_assets_current):
        return MetricResult(value=None, label="Asset Turnover", unit="x",
                            formula=formula, note="Revenue or total assets unavailable")

    if is_valid(total_assets_previous) and total_assets_previous > 0:  # type: ignore[operator]
        avg_assets = (total_assets_current + total_assets_previous) / 2.0  # type: ignore[operator]
        note = None
    else:
        avg_assets = total_assets_current
        note = "Using current-year total assets only"

    val, div_note = safe_div(revenue, avg_assets)
    if val is None:
        return MetricResult(value=None, label="Asset Turnover", unit="x",
                            formula=formula, note=div_note)
    return MetricResult(
        value=round(val, 2),
        label="Asset Turnover",
        unit="x",
        formula=formula,
        inputs={"revenue": revenue, "avg_assets": avg_assets},
        note=note,
    )


def working_capital_days(
    working_capital: Optional[float],
    revenue: Optional[float],
) -> MetricResult:
    """Working Capital Days = Working Capital / Revenue × 365."""
    formula = "Working Capital / Revenue × 365"
    val, note = safe_div(working_capital, revenue)
    if val is None:
        return MetricResult(value=None, label="Working Capital Days", unit="days",
                            formula=formula, note=note)
    return MetricResult(
        value=round(val * _DAYS_IN_YEAR, 1),
        label="Working Capital Days",
        unit="days",
        formula=formula,
        inputs={"working_capital": working_capital, "revenue": revenue},
    )
