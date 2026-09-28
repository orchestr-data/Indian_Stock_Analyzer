"""Profitability metrics: margins, ROE, ROCE, ROA.

Definitions used:

Operating Margin = Operating Profit / Revenue × 100
EBITDA Margin    = EBITDA / Revenue × 100
EBIT Margin      = EBIT / Revenue × 100
Net Margin       = PAT / Revenue × 100

ROE  = PAT attributable to equity shareholders / Average Shareholders' Equity × 100
       Average Equity = (Current Equity + Previous Equity) / 2

ROCE = EBIT / Average Capital Employed × 100
       Capital Employed = Shareholders' Equity + Interest-Bearing Debt - Cash

ROA  = PAT / Average Total Assets × 100

Note: other databases may define these differently.
This application always shows the formula and input values.
"""

from __future__ import annotations
from typing import Optional

from src.calculations.helpers import safe_pct, is_valid
from src.models.metrics import MetricResult


def operating_margin(
    operating_profit: Optional[float],
    revenue: Optional[float],
) -> MetricResult:
    value = safe_pct(operating_profit, revenue)
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="Operating Margin",
        unit="%",
        formula="Operating Profit / Revenue × 100",
        inputs={"operating_profit": operating_profit, "revenue": revenue},
        note=None if value is not None else "Unavailable: operating profit or revenue missing",
    )


def ebitda_margin(
    ebitda: Optional[float],
    revenue: Optional[float],
) -> MetricResult:
    value = safe_pct(ebitda, revenue)
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="EBITDA Margin",
        unit="%",
        formula="EBITDA / Revenue × 100",
        inputs={"ebitda": ebitda, "revenue": revenue},
        note=None if value is not None else "Unavailable: EBITDA or revenue missing",
    )


def ebit_margin(
    ebit: Optional[float],
    revenue: Optional[float],
) -> MetricResult:
    value = safe_pct(ebit, revenue)
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="EBIT Margin",
        unit="%",
        formula="EBIT / Revenue × 100",
        inputs={"ebit": ebit, "revenue": revenue},
        note=None if value is not None else "Unavailable: EBIT or revenue missing",
    )


def net_margin(
    pat: Optional[float],
    revenue: Optional[float],
) -> MetricResult:
    value = safe_pct(pat, revenue)
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="Net Profit Margin",
        unit="%",
        formula="PAT / Revenue × 100",
        inputs={"pat": pat, "revenue": revenue},
        note=None if value is not None else "Unavailable: PAT or revenue missing",
    )


def roe(
    pat: Optional[float],
    equity_current: Optional[float],
    equity_previous: Optional[float] = None,
    minority_interest: Optional[float] = None,
) -> MetricResult:
    """Return on Equity.

    Uses PAT attributable to equity shareholders (PAT minus minority interest).
    When minority_interest is unavailable, total PAT is used and a note is added
    — this can overstate ROE for consolidated statements with significant minorities.
    Uses average equity when previous year equity is available.
    """
    formula = "PAT (attributable) / Average Shareholders' Equity × 100"
    inputs = {
        "pat": pat,
        "minority_interest": minority_interest,
        "equity_current": equity_current,
        "equity_previous": equity_previous,
    }

    if not is_valid(pat) or not is_valid(equity_current):
        return MetricResult(value=None, label="ROE", unit="%", formula=formula,
                            inputs=inputs, note="PAT or equity unavailable")

    if equity_current <= 0:  # type: ignore[operator]
        return MetricResult(value=None, label="ROE", unit="%", formula=formula,
                            inputs=inputs, note="Equity is zero or negative — ROE not meaningful")

    if is_valid(minority_interest):
        pat_attributable = pat - minority_interest  # type: ignore[operator]
        mi_note = None
    else:
        pat_attributable = pat
        mi_note = "Minority interest unavailable — total PAT used; may overstate ROE for consolidated accounts"

    if is_valid(equity_previous) and equity_previous > 0:  # type: ignore[operator]
        avg_equity = (equity_current + equity_previous) / 2.0  # type: ignore[operator]
        eq_note = None
    else:
        avg_equity = equity_current
        eq_note = "Using current equity only (prior year unavailable)"

    note = "; ".join(n for n in (mi_note, eq_note) if n) or None
    value = (pat_attributable / avg_equity) * 100.0  # type: ignore[operator]
    return MetricResult(
        value=round(value, 2), label="ROE", unit="%", formula=formula,
        inputs={**inputs, "pat_attributable": pat_attributable, "avg_equity": avg_equity},
        note=note,
    )


def roce(
    ebit: Optional[float],
    equity: Optional[float],
    borrowings: Optional[float],
    cash: Optional[float],
    equity_prev: Optional[float] = None,
    borrowings_prev: Optional[float] = None,
    cash_prev: Optional[float] = None,
) -> MetricResult:
    """Return on Capital Employed.

    Capital Employed = Shareholders' Equity + Interest-Bearing Debt − Cash
    Uses average capital employed when prior year data is available.
    """
    formula = (
        "EBIT / Capital Employed × 100\n"
        "Capital Employed = Equity + Debt − Cash\n"
        "(averaged with prior year when prior year data is available)"
    )
    inputs = {
        "ebit": ebit,
        "equity": equity,
        "borrowings": borrowings,
        "cash": cash,
    }

    if not is_valid(ebit):
        return MetricResult(value=None, label="ROCE", unit="%", formula=formula,
                            inputs=inputs, note="EBIT unavailable")

    if not is_valid(equity) or not is_valid(borrowings):
        return MetricResult(value=None, label="ROCE", unit="%", formula=formula,
                            inputs=inputs, note="Equity or borrowings unavailable")

    cash_val = cash if is_valid(cash) else 0.0
    ce_current = equity + borrowings - cash_val  # type: ignore[operator]

    has_prev = (is_valid(equity_prev) and is_valid(borrowings_prev))
    if has_prev:
        cash_prev_val = cash_prev if is_valid(cash_prev) else 0.0
        ce_prev = equity_prev + borrowings_prev - cash_prev_val  # type: ignore[operator]
        avg_ce = (ce_current + ce_prev) / 2.0
        note = None
    else:
        avg_ce = ce_current
        note = "Using current-year capital employed (prior year unavailable)"

    if avg_ce <= 0:
        return MetricResult(value=None, label="ROCE", unit="%", formula=formula,
                            inputs={**inputs, "capital_employed": avg_ce},
                            note="Capital employed is zero or negative")

    value = (ebit / avg_ce) * 100.0  # type: ignore[operator]
    return MetricResult(
        value=round(value, 2), label="ROCE", unit="%", formula=formula,
        inputs={**inputs, "capital_employed": avg_ce}, note=note,
    )


def roa(
    pat: Optional[float],
    total_assets_current: Optional[float],
    total_assets_previous: Optional[float] = None,
) -> MetricResult:
    """Return on Assets — primarily used for banks."""
    formula = "PAT / Average Total Assets × 100"
    if not is_valid(pat) or not is_valid(total_assets_current):
        return MetricResult(value=None, label="ROA", unit="%", formula=formula,
                            note="PAT or total assets unavailable")

    if is_valid(total_assets_previous) and total_assets_previous > 0:  # type: ignore[operator]
        avg_assets = (total_assets_current + total_assets_previous) / 2.0  # type: ignore[operator]
        note = None
    else:
        avg_assets = total_assets_current
        note = "Using current total assets only"

    if avg_assets <= 0:
        return MetricResult(value=None, label="ROA", unit="%", formula=formula,
                            note="Total assets zero or negative")

    value = (pat / avg_assets) * 100.0  # type: ignore[operator]
    return MetricResult(
        value=round(value, 4), label="ROA", unit="%", formula=formula,
        inputs={"pat": pat, "avg_assets": avg_assets}, note=note,
    )
