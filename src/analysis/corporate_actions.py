"""Corporate action awareness — share count changes, dividends, buybacks."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
from src.calculations.helpers import is_valid


@dataclass
class ShareCountAnalysis:
    series: list[tuple[int, Optional[float]]] = field(default_factory=list)
    total_change_pct: Optional[float] = None
    notes: list[str] = field(default_factory=list)


def analyze_share_count(income_df: pd.DataFrame) -> ShareCountAnalysis:
    """Analyze share count history for dilution/buyback trends."""
    result = ShareCountAnalysis()
    if income_df.empty or "weighted_avg_shares" not in income_df.columns:
        return result

    df = income_df.sort_values("fiscal_year")
    for _, row in df.iterrows():
        shares = row.get("weighted_avg_shares")
        result.series.append((int(row["fiscal_year"]), shares if is_valid(shares) else None))

    valid = [(yr, s) for yr, s in result.series if s is not None]
    if len(valid) >= 2:
        first = valid[0][1]
        last = valid[-1][1]
        if first and first > 0:
            result.total_change_pct = (last - first) / first * 100.0
            if result.total_change_pct > 10:
                result.notes.append(
                    f"Share count increased by {result.total_change_pct:.1f}% from "
                    f"FY{valid[0][0]} to FY{valid[-1][0]} — check for dilutive events "
                    "(rights issue, ESOP vesting, QIP)."
                )
            elif result.total_change_pct < -5:
                result.notes.append(
                    f"Share count reduced by {abs(result.total_change_pct):.1f}% from "
                    f"FY{valid[0][0]} to FY{valid[-1][0]} — buyback programme detected."
                )

    return result


@dataclass
class DividendHistory:
    series: list[tuple[int, Optional[float]]] = field(default_factory=list)
    payout_series: list[tuple[int, Optional[float]]] = field(default_factory=list)
    has_data: bool = False


def analyze_dividend_history(
    cashflow_df: pd.DataFrame,
    income_df: pd.DataFrame,
) -> DividendHistory:
    """Extract dividend paid per year and compute payout ratio where possible."""
    result = DividendHistory()

    if cashflow_df.empty or "dividends_paid" not in cashflow_df.columns:
        return result

    cf = cashflow_df.sort_values("fiscal_year")
    inc = income_df.sort_values("fiscal_year") if income_df is not None and not income_df.empty else pd.DataFrame()

    for _, row in cf.iterrows():
        fy = int(row["fiscal_year"])
        div = row.get("dividends_paid")
        div_abs = abs(div) if is_valid(div) else None
        result.series.append((fy, div_abs))

        payout = None
        if is_valid(div_abs) and not inc.empty:
            pat_row = inc[inc["fiscal_year"] == fy]
            if not pat_row.empty:
                pat = pat_row.iloc[0].get("pat")
                if is_valid(pat) and pat > 0:
                    payout = round(div_abs / pat * 100, 1)
        result.payout_series.append((fy, payout))

    result.has_data = any(v is not None for _, v in result.series)
    return result


@dataclass
class BuybackHistory:
    series: list[tuple[int, Optional[float]]] = field(default_factory=list)
    total_cr: Optional[float] = None
    has_data: bool = False


def analyze_buyback_history(cashflow_df: pd.DataFrame) -> BuybackHistory:
    """Extract buyback amounts per year from cash flow data."""
    result = BuybackHistory()

    if cashflow_df.empty or "buybacks" not in cashflow_df.columns:
        return result

    cf = cashflow_df.sort_values("fiscal_year")
    total = 0.0
    for _, row in cf.iterrows():
        fy = int(row["fiscal_year"])
        bb = row.get("buybacks")
        bb_abs = abs(bb) if is_valid(bb) else None
        result.series.append((fy, bb_abs))
        if bb_abs:
            total += bb_abs

    result.has_data = any(v is not None for _, v in result.series)
    result.total_cr = round(total, 0) if total > 0 else None
    return result
