"""Earnings quality analysis — assesses how well accounting profit is supported by cash."""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass, field

import pandas as pd

from src.calculations.cashflow import cfo_pat_ratio, fcf_pat_ratio
from src.calculations.helpers import is_valid
from src.models.metrics import MetricResult


@dataclass
class EarningsQualityResult:
    """Summary of earnings quality analysis."""
    cfo_pat_series: list[tuple[int, Optional[float]]] = field(default_factory=list)
    fcf_pat_series: list[tuple[int, Optional[float]]] = field(default_factory=list)
    receivable_vs_revenue: list[tuple[int, float, float]] = field(default_factory=list)  # (yr, rec_days, rev_growth)
    inventory_vs_revenue: list[tuple[int, float, float]] = field(default_factory=list)
    other_income_pbt_pct: list[tuple[int, Optional[float]]] = field(default_factory=list)
    pat_growth_5y: Optional[float] = None
    cfo_growth_5y: Optional[float] = None
    divergence_note: Optional[str] = None


class EarningsQualityAnalyzer:
    """Analyzes earnings quality using multiple cash-flow based metrics."""

    def analyze(
        self,
        income_df: pd.DataFrame,
        cashflow_df: pd.DataFrame,
        balance_df: pd.DataFrame,
    ) -> EarningsQualityResult:
        result = EarningsQualityResult()

        if income_df.empty:
            return result

        income_df = income_df.sort_values("fiscal_year").reset_index(drop=True)
        if not cashflow_df.empty and "fiscal_year" in cashflow_df.columns:
            cashflow_df = cashflow_df.sort_values("fiscal_year").reset_index(drop=True)
        if not balance_df.empty and "fiscal_year" in balance_df.columns:
            balance_df = balance_df.sort_values("fiscal_year").reset_index(drop=True)

        # CFO/PAT series
        merged_cf = income_df[["fiscal_year", "pat"]].merge(
            cashflow_df[["fiscal_year", "operating_cash_flow"]], on="fiscal_year", how="inner"
        )
        for _, row in merged_cf.iterrows():
            r = cfo_pat_ratio(row.get("operating_cash_flow"), row.get("pat"))
            result.cfo_pat_series.append((int(row["fiscal_year"]), r.value))

        # FCF/PAT series
        cf_with_fcf = cashflow_df.copy()
        if "free_cash_flow" not in cf_with_fcf.columns:
            cf_with_fcf["free_cash_flow"] = None

        merged_fcf = income_df[["fiscal_year", "pat"]].merge(
            cf_with_fcf[["fiscal_year", "free_cash_flow"]], on="fiscal_year", how="inner"
        )
        for _, row in merged_fcf.iterrows():
            r = fcf_pat_ratio(row.get("free_cash_flow"), row.get("pat"))
            result.fcf_pat_series.append((int(row["fiscal_year"]), r.value))

        # PAT growth vs CFO growth (5Y)
        if len(income_df) >= 6 and len(merged_cf) >= 6:
            pat_series = income_df["pat"].tolist()
            cfo_series = merged_cf["operating_cash_flow"].tolist()
            from src.calculations.growth import cagr as cagr_fn
            pat_valid = [v for v in pat_series if is_valid(v)]
            cfo_valid = [v for v in cfo_series if is_valid(v)]
            if len(pat_valid) >= 6 and pat_valid[-6] > 0:
                r = cagr_fn(pat_valid[-6], pat_valid[-1], 5)
                result.pat_growth_5y = r.value
            if len(cfo_valid) >= 6 and cfo_valid[-6] > 0:
                r = cagr_fn(cfo_valid[-6], cfo_valid[-1], 5)
                result.cfo_growth_5y = r.value

            if result.pat_growth_5y and result.cfo_growth_5y:
                diff = result.pat_growth_5y - result.cfo_growth_5y
                if diff > 20:
                    result.divergence_note = (
                        f"PAT grew at {result.pat_growth_5y:.1f}% CAGR vs "
                        f"CFO at {result.cfo_growth_5y:.1f}% CAGR over 5 years. "
                        "Earnings growth has outpaced cash generation — investigate."
                    )

        # Other income / PBT
        for _, row in income_df.iterrows():
            oi = row.get("other_income")
            pbt = row.get("pbt")
            if is_valid(oi) and is_valid(pbt) and pbt > 0:
                result.other_income_pbt_pct.append((int(row["fiscal_year"]), oi / pbt * 100.0))

        return result
