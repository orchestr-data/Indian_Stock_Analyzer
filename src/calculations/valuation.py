"""Valuation metrics.

Definitions:
  EPS (Basic)      = PAT attributable / Weighted Average Shares
  Book Value/Share = Shareholders' Equity / Shares Outstanding
  P/E              = Price / EPS
  P/B              = Price / Book Value per Share (or Market Cap / Equity)
  PEG              = P/E / EPS Growth %
  EV               = Market Cap + Net Debt   (Debt − Cash)
  EV/EBITDA        = Enterprise Value / EBITDA
  EV/EBIT          = Enterprise Value / EBIT
  Earnings Yield   = EPS / Price × 100  (inverse of P/E)
  Dividend Yield   = DPS / Price × 100
"""

from __future__ import annotations
from typing import Optional

from src.calculations.helpers import safe_div, safe_pct, is_valid
from src.models.metrics import MetricResult


def eps_calc(
    pat_attributable: Optional[float],
    weighted_avg_shares: Optional[float],
) -> MetricResult:
    """Basic EPS = PAT attributable / Weighted Average Shares."""
    val, note = safe_div(pat_attributable, weighted_avg_shares)
    return MetricResult(
        value=round(val, 2) if val is not None else None,
        label="EPS",
        unit="₹",
        formula="PAT (attributable to equity holders) / Weighted Average Shares",
        inputs={"pat": pat_attributable, "shares": weighted_avg_shares},
        note=note if val is None else None,
    )


def book_value_per_share(
    shareholders_equity: Optional[float],
    shares_outstanding: Optional[float],
) -> MetricResult:
    """Book Value per Share = Shareholders' Equity / Shares Outstanding."""
    val, note = safe_div(shareholders_equity, shares_outstanding)
    return MetricResult(
        value=round(val, 2) if val is not None else None,
        label="Book Value per Share",
        unit="₹",
        formula="Shareholders' Equity / Shares Outstanding",
        inputs={"equity": shareholders_equity, "shares": shares_outstanding},
        note=note if val is None else None,
    )


def pe_ratio(
    price: Optional[float],
    eps: Optional[float],
) -> MetricResult:
    """P/E = Price / EPS."""
    if is_valid(eps) and eps < 0:  # type: ignore[operator]
        return MetricResult(
            value=None, label="P/E", unit="x",
            formula="Price / EPS",
            inputs={"price": price, "eps": eps},
            note="P/E not meaningful when EPS is negative",
        )
    if is_valid(eps) and eps == 0:
        return MetricResult(
            value=None, label="P/E", unit="x",
            inputs={"price": price, "eps": eps},
            note="P/E undefined: EPS is zero",
        )
    val, note = safe_div(price, eps)
    return MetricResult(
        value=round(val, 1) if val is not None else None,
        label="P/E",
        unit="x",
        formula="Price / Earnings Per Share",
        inputs={"price": price, "eps": eps},
        note=note if val is None else None,
    )


def pb_ratio(
    market_cap: Optional[float],
    shareholders_equity: Optional[float],
) -> MetricResult:
    """P/B = Market Cap / Shareholders' Equity."""
    if is_valid(shareholders_equity) and shareholders_equity <= 0:
        return MetricResult(
            value=None, label="P/B", unit="x",
            formula="Market Cap / Shareholders' Equity",
            inputs={"market_cap": market_cap, "equity": shareholders_equity},
            note="P/B not meaningful when equity is zero or negative",
        )
    val, note = safe_div(market_cap, shareholders_equity)
    return MetricResult(
        value=round(val, 2) if val is not None else None,
        label="P/B",
        unit="x",
        formula="Market Capitalization / Shareholders' Equity",
        inputs={"market_cap": market_cap, "equity": shareholders_equity},
        note=note if val is None else None,
    )


def peg_ratio(
    pe: Optional[float],
    eps_growth_pct: Optional[float],
) -> MetricResult:
    """PEG = P/E / EPS Growth %.

    Not meaningful when P/E is negative or EPS growth is zero/negative.
    """
    formula = "P/E / EPS Growth %"
    if not is_valid(pe) or not is_valid(eps_growth_pct):
        return MetricResult(value=None, label="PEG", unit="x", formula=formula,
                            note="P/E or EPS growth unavailable")
    if pe <= 0:  # type: ignore[operator]
        return MetricResult(value=None, label="PEG", unit="x", formula=formula,
                            note="PEG not meaningful when P/E is negative")
    if eps_growth_pct <= 0:  # type: ignore[operator]
        return MetricResult(value=None, label="PEG", unit="x", formula=formula,
                            inputs={"pe": pe, "eps_growth_pct": eps_growth_pct},
                            note="PEG not meaningful when EPS growth is zero or negative")

    value = pe / eps_growth_pct  # type: ignore[operator]
    return MetricResult(
        value=round(value, 2), label="PEG", unit="x", formula=formula,
        inputs={"pe": pe, "eps_growth_pct": eps_growth_pct},
    )


def enterprise_value(
    market_cap: Optional[float],
    borrowings: Optional[float],
    cash: Optional[float],
) -> MetricResult:
    """EV = Market Cap + Borrowings − Cash."""
    formula = "Market Cap + Interest-Bearing Debt − Cash"
    if not is_valid(market_cap):
        return MetricResult(value=None, label="Enterprise Value", unit="₹ Cr",
                            formula=formula, note="Market cap unavailable")
    if not is_valid(borrowings):
        return MetricResult(value=None, label="Enterprise Value", unit="₹ Cr",
                            formula=formula, note="Borrowings unavailable")

    cash_val = cash if is_valid(cash) else 0.0
    value = market_cap + borrowings - cash_val  # type: ignore[operator]
    return MetricResult(
        value=round(value, 2),
        label="Enterprise Value",
        unit="₹ Cr",
        formula=formula,
        inputs={"market_cap": market_cap, "borrowings": borrowings, "cash": cash_val},
    )


def ev_ebitda(
    ev: Optional[float],
    ebitda: Optional[float],
) -> MetricResult:
    """EV/EBITDA."""
    if is_valid(ebitda) and ebitda <= 0:
        return MetricResult(
            value=None, label="EV/EBITDA", unit="x",
            inputs={"ev": ev, "ebitda": ebitda},
            note="EV/EBITDA not meaningful when EBITDA ≤ 0",
        )
    val, note = safe_div(ev, ebitda)
    return MetricResult(
        value=round(val, 1) if val is not None else None,
        label="EV/EBITDA", unit="x",
        formula="Enterprise Value / EBITDA",
        inputs={"ev": ev, "ebitda": ebitda},
        note=note if val is None else None,
    )


def ev_ebit(
    ev: Optional[float],
    ebit: Optional[float],
) -> MetricResult:
    """EV/EBIT."""
    if is_valid(ebit) and ebit <= 0:
        return MetricResult(
            value=None, label="EV/EBIT", unit="x",
            inputs={"ev": ev, "ebit": ebit},
            note="EV/EBIT not meaningful when EBIT ≤ 0",
        )
    val, note = safe_div(ev, ebit)
    return MetricResult(
        value=round(val, 1) if val is not None else None,
        label="EV/EBIT", unit="x",
        formula="Enterprise Value / EBIT",
        inputs={"ev": ev, "ebit": ebit},
        note=note if val is None else None,
    )


def earnings_yield(
    eps: Optional[float],
    price: Optional[float],
) -> MetricResult:
    """Earnings Yield = EPS / Price × 100 (inverse of P/E)."""
    value = safe_pct(eps, price)
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="Earnings Yield",
        unit="%",
        formula="EPS / Price × 100",
        inputs={"eps": eps, "price": price},
        note=None if value is not None else "EPS or price unavailable",
    )


def dividend_yield_calc(
    dps: Optional[float],
    price: Optional[float],
) -> MetricResult:
    """Dividend Yield = DPS / Price × 100."""
    value = safe_pct(dps, price)
    return MetricResult(
        value=round(value, 2) if value is not None else None,
        label="Dividend Yield",
        unit="%",
        formula="Dividends Per Share / Price × 100",
        inputs={"dps": dps, "price": price},
        note=None if value is not None else "DPS or price unavailable",
    )
