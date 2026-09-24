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


def analyze_pe_history(market_df: pd.DataFrame) -> ValuationHistory:
    """Build P/E historical context from accumulated market data snapshots."""
    if market_df.empty or "pe" not in market_df.columns:
        return ValuationHistory("P/E", None)

    df = market_df.sort_values("date").dropna(subset=["pe"])
    df = df[df["pe"].apply(is_valid)]
    values = [float(v) for v in df["pe"]]
    labels = [str(d)[:10] for d in df["date"]]
    series = list(zip(labels, values))

    if not values:
        return ValuationHistory("P/E", None)

    current = values[-1]
    # Use slice for yearly/daily data — median() already filters None
    med3 = median(values[-3 * 252 :]) if len(values) >= 3 else None
    med5 = median(values[-5 * 252 :]) if len(values) >= 5 else None
    med10 = median(values[-10 * 252 :]) if len(values) >= 10 else None

    premium = None
    if is_valid(current) and is_valid(med5) and med5 > 0:  # type: ignore[operator]
        premium = (current - med5) / med5 * 100.0  # type: ignore[operator]

    return ValuationHistory("P/E", current, med3, med5, med10, premium, series)


def analyze_pb_history(market_df: pd.DataFrame) -> ValuationHistory:
    """Build P/B historical context from accumulated market data snapshots."""
    if market_df.empty or "pb" not in market_df.columns:
        return ValuationHistory("P/B", None)

    df = market_df.sort_values("date").dropna(subset=["pb"])
    df = df[df["pb"].apply(is_valid)]
    values = [float(v) for v in df["pb"]]
    labels = [str(d)[:10] for d in df["date"]]
    series = list(zip(labels, values))

    if not values:
        return ValuationHistory("P/B", None)

    current = values[-1]
    med3 = median(values[-3 * 252 :]) if len(values) >= 3 else None
    med5 = median(values[-5 * 252 :]) if len(values) >= 5 else None
    med10 = median(values[-10 * 252 :]) if len(values) >= 10 else None

    premium = None
    if is_valid(current) and is_valid(med5) and med5 > 0:  # type: ignore[operator]
        premium = (current - med5) / med5 * 100.0  # type: ignore[operator]

    return ValuationHistory("P/B", current, med3, med5, med10, premium, series)


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
