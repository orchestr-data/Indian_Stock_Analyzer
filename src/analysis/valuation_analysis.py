"""Valuation analysis — historical context for valuation multiples."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
from src.calculations.helpers import is_valid, median


@dataclass
class ValuationHistory:
    metric_name: str
    current: Optional[float]
    median_3y: Optional[float] = None
    median_5y: Optional[float] = None
    median_10y: Optional[float] = None
    premium_to_5y_median_pct: Optional[float] = None
    series: list[tuple[str, Optional[float]]] = field(default_factory=list)


@dataclass
class SyntheticMultiples:
    """Current market cap divided by historical PAT and equity.

    NOT the same as historical P/E — these use today's market cap against
    past earnings, showing how current price relates to historical fundamentals.
    """
    market_cap: Optional[float]
    mc_over_pat: list[tuple[int, Optional[float]]] = field(default_factory=list)
    mc_over_equity: list[tuple[int, Optional[float]]] = field(default_factory=list)
    median_mc_over_pat_3y: Optional[float] = None
    median_mc_over_pat_5y: Optional[float] = None
    median_mc_over_equity_3y: Optional[float] = None
    median_mc_over_equity_5y: Optional[float] = None


def _window_median(dates: list[pd.Timestamp], values: list[float], years: int) -> Optional[float]:
    """Median of values dated within `years` of the latest date.

    Works for any sampling frequency (year-end, monthly, daily). Requires at
    least `years` observations in the window so that e.g. a "5Y median" is
    never computed from two data points.
    """
    if not values:
        return None
    cutoff = dates[-1] - pd.DateOffset(years=years)
    window = [v for d, v in zip(dates, values) if d > cutoff]
    return median(window) if len(window) >= years else None


def _analyze_history(market_df: pd.DataFrame, column: str, label: str) -> ValuationHistory:
    if market_df is None or market_df.empty or column not in market_df.columns:
        return ValuationHistory(label, None)

    df = market_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").dropna(subset=[column])
    df = df[df[column].apply(is_valid)]
    if df.empty:
        return ValuationHistory(label, None)

    dates = list(df["date"])
    values = [float(v) for v in df[column]]
    series = [(str(d)[:10], v) for d, v in zip(dates, values)]

    current = values[-1]
    med3 = _window_median(dates, values, 3)
    med5 = _window_median(dates, values, 5)
    med10 = _window_median(dates, values, 10)

    premium = None
    if is_valid(med5) and med5 > 0:  # type: ignore[operator]
        premium = (current - med5) / med5 * 100.0  # type: ignore[operator]

    return ValuationHistory(label, current, med3, med5, med10, premium, series)


def analyze_pe_history(market_df: pd.DataFrame) -> ValuationHistory:
    """P/E historical context from market data snapshots (any frequency)."""
    return _analyze_history(market_df, "pe", "P/E")


def analyze_pb_history(market_df: pd.DataFrame) -> ValuationHistory:
    """P/B historical context from market data snapshots (any frequency)."""
    return _analyze_history(market_df, "pb", "P/B")


def compute_synthetic_multiples(
    income_df: pd.DataFrame,
    balance_df: pd.DataFrame | None,
    market_cap: Optional[float],
) -> SyntheticMultiples:
    """Compute current market cap divided by historical PAT and equity.

    These show what multiple today's price represents on each year's earnings /
    book value.  They are NOT historical P/E — historical prices are not used.
    """
    result = SyntheticMultiples(market_cap=market_cap)

    if not is_valid(market_cap) or income_df is None or income_df.empty:
        return result

    for _, row in income_df.sort_values("fiscal_year").iterrows():
        fy = int(row["fiscal_year"])
        pat = row.get("pat")
        if is_valid(pat) and pat > 0:  # type: ignore[operator]
            result.mc_over_pat.append((fy, round(market_cap / pat, 1)))  # type: ignore[operator]
        else:
            result.mc_over_pat.append((fy, None))

    if balance_df is not None and not balance_df.empty:
        for _, row in balance_df.sort_values("fiscal_year").iterrows():
            fy = int(row["fiscal_year"])
            eq = row.get("shareholders_equity")
            if is_valid(eq) and eq > 0:  # type: ignore[operator]
                result.mc_over_equity.append((fy, round(market_cap / eq, 2)))  # type: ignore[operator]
            else:
                result.mc_over_equity.append((fy, None))

    # Medians over trailing years
    pat_vals = [v for _, v in result.mc_over_pat]
    result.median_mc_over_pat_3y = median(pat_vals[-3:]) if len(pat_vals) >= 3 else None
    result.median_mc_over_pat_5y = median(pat_vals[-5:]) if len(pat_vals) >= 5 else None

    eq_vals = [v for _, v in result.mc_over_equity]
    result.median_mc_over_equity_3y = median(eq_vals[-3:]) if len(eq_vals) >= 3 else None
    result.median_mc_over_equity_5y = median(eq_vals[-5:]) if len(eq_vals) >= 5 else None

    return result
