"""Cash flow quality metrics.

Definitions:
  FCF          = Operating Cash Flow − Capital Expenditure
  CFO/PAT      = Operating Cash Flow / PAT
  FCF/PAT      = FCF / PAT
  FCF Margin   = FCF / Revenue × 100
  FCF Yield    = FCF / Market Cap × 100
  CapEx/Rev    = Capital Expenditure / Revenue × 100
"""

from __future__ import annotations
from typing import Optional

from src.calculations.helpers import safe_div, safe_pct, is_valid
from src.models.metrics import MetricResult


def free_cash_flow(
    operating_cash_flow: Optional[float],
    capital_expenditure: Optional[float],
) -> MetricResult:
    """FCF = Operating Cash Flow − Capital Expenditure.

    CapEx is typically reported as a negative number in cash flow statements.
    This function accepts CapEx as either sign and normalizes.
    """
    if not is_valid(operating_cash_flow):
        return MetricResult(value=None, label="Free Cash Flow", unit="₹ Cr",
                            note="Operating cash flow unavailable")
    if not is_valid(capital_expenditure):
        return MetricResult(
            value=None, label="Free Cash Flow", unit="₹ Cr",
            note="Capital expenditure unavailable — cannot compute FCF",
        )

    # CapEx may come as negative from the investing section
    capex_abs = abs(capital_expenditure)  # type: ignore[arg-type]
    value = operating_cash_flow - capex_abs  # type: ignore[operator]
    return MetricResult(
        value=round(value, 2),
        label="Free Cash Flow",
        unit="₹ Cr",
        formula="Operating Cash Flow − Capital Expenditure",
        inputs={"cfo": operating_cash_flow, "capex": capex_abs},
    )


def cfo_pat_ratio(
    operating_cash_flow: Optional[float],
    pat: Optional[float],
) -> MetricResult:
    """CFO/PAT — measures how well accounting profit converts to cash.

    > 1.0: CFO exceeds accounting profit (strong cash quality)
    < 1.0: Accounting profit outpaces cash (warrants investigation)
    < 0.0: Negative CFO despite positive PAT (material concern)
    """
    formula = "Operating Cash Flow / PAT"

    if not is_valid(operating_cash_flow) or not is_valid(pat):
        return MetricResult(value=None, label="CFO/PAT", unit="x", formula=formula,
                            note="CFO or PAT unavailable")
    if pat == 0:
        return MetricResult(value=None, label="CFO/PAT", unit="x", formula=formula,
                            inputs={"cfo": operating_cash_flow, "pat": pat},
                            note="PAT is zero — ratio undefined")
    if pat < 0:
        return MetricResult(
            value=None, label="CFO/PAT", unit="x", formula=formula,
            inputs={"cfo": operating_cash_flow, "pat": pat},
            note="PAT is negative — CFO/PAT not meaningful",
        )

    value = operating_cash_flow / pat  # type: ignore[operator]
    note = None
    if value < 0:
        note = "Negative CFO despite positive PAT — investigate cash quality"
    elif value < 0.7:
        note = "CFO/PAT below 0.7 — earnings quality warrants investigation"

    return MetricResult(
        value=round(value, 2),
        label="CFO/PAT",
        unit="x",
        formula=formula,
        inputs={"cfo": operating_cash_flow, "pat": pat},
        note=note,
    )


def fcf_pat_ratio(
    fcf: Optional[float],
    pat: Optional[float],
) -> MetricResult:
    """FCF/PAT ratio."""
    formula = "Free Cash Flow / PAT"

    if not is_valid(fcf) or not is_valid(pat):
        return MetricResult(value=None, label="FCF/PAT", unit="x", formula=formula,
                            note="FCF or PAT unavailable")
    if pat == 0:
        return MetricResult(value=None, label="FCF/PAT", unit="x", formula=formula,
                            note="PAT is zero — ratio undefined")
    if pat < 0:
        return MetricResult(value=None, label="FCF/PAT", unit="x", formula=formula,
                            note="PAT is negative — FCF/PAT not meaningful")

    value = fcf / pat  # type: ignore[operator]
    return MetricResult(
        value=round(value, 2), label="FCF/PAT", unit="x", formula=formula,
        inputs={"fcf": fcf, "pat": pat},
    )


def fcf_margin(
    fcf: Optional[float],
    revenue: Optional[float],
) -> MetricResult:
    """FCF Margin = FCF / Revenue × 100."""
    value = safe_pct(fcf, revenue)
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="FCF Margin",
        unit="%",
        formula="Free Cash Flow / Revenue × 100",
        inputs={"fcf": fcf, "revenue": revenue},
        note=None if value is not None else "FCF or revenue unavailable",
    )


def fcf_yield(
    fcf: Optional[float],
    market_cap: Optional[float],
) -> MetricResult:
    """FCF Yield = FCF / Market Cap × 100."""
    value = safe_pct(fcf, market_cap)
    note = None
    if value is None:
        note = "FCF or market cap unavailable"
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="FCF Yield",
        unit="%",
        formula="Free Cash Flow / Market Capitalization × 100",
        inputs={"fcf": fcf, "market_cap": market_cap},
        note=note,
    )


def capex_revenue_pct(
    capital_expenditure: Optional[float],
    revenue: Optional[float],
) -> MetricResult:
    """CapEx as % of Revenue — capital intensity indicator."""
    capex_abs = abs(capital_expenditure) if is_valid(capital_expenditure) else None
    value = safe_pct(capex_abs, revenue)
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="CapEx/Revenue",
        unit="%",
        formula="Capital Expenditure / Revenue × 100",
        inputs={"capex": capex_abs, "revenue": revenue},
        note=None if value is not None else "CapEx or revenue unavailable",
    )
