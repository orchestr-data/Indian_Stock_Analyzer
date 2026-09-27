"""Growth analysis page."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.calculations import revenue_cagr, pat_cagr, eps_cagr, ebitda_cagr, fcf_cagr
from src.analysis.trends import TrendAnalyzer
from src.ui.charts import bar_chart, line_chart
from src.ui.components import section_header, cagr_table, not_available


def render(
    income_df: pd.DataFrame,
    cashflow_df: pd.DataFrame,
    statement_type: str,
) -> None:
    section_header("Growth Analysis", "Historical growth rates — CAGR across 3, 5, and 10 years")

    if income_df is None or income_df.empty:
        st.info("No income statement data available.")
        return

    income_df = income_df.sort_values("fiscal_year")
    years_label = [f"FY{y}" for y in income_df["fiscal_year"]]
    years = income_df["fiscal_year"].tolist()
    analyzer = TrendAnalyzer()

    metrics_to_show = [
        ("Revenue", "revenue", "₹ Cr", income_df),
        ("EBITDA", "ebitda", "₹ Cr", income_df),
        ("EBIT", "ebit", "₹ Cr", income_df),
        ("PAT", "pat", "₹ Cr", income_df),
        ("EPS (Basic)", "basic_eps", "₹", income_df),
    ]

    for label, col, unit, df in metrics_to_show:
        if col not in df.columns:
            continue
        values = df[col].tolist()
        if all(v is None for v in values):
            continue

        st.markdown(f"#### {label}")
        c3 = _cagr(values, 3, years)
        c5 = _cagr(values, 5, years)
        c10 = _cagr(values, 10, years)
        cagr_table(label, c3, c5, c10)

        trend = analyzer.analyze(label, values, years_label, years)
        if trend.direction != "insufficient_history":
            st.caption(f"Trend: **{trend.direction.title()}**")

        st.plotly_chart(
            bar_chart(years_label, values, f"{label} ({unit})", unit),
            use_container_width=True,
        )
        st.divider()

    # FCF growth
    if cashflow_df is not None and not cashflow_df.empty and "free_cash_flow" in cashflow_df.columns:
        cf_df = cashflow_df.sort_values("fiscal_year")
        fcf_vals = cf_df["free_cash_flow"].tolist()
        cf_fiscal_years = cf_df["fiscal_year"].tolist()
        cf_years = [f"FY{y}" for y in cf_fiscal_years]
        st.markdown("#### Free Cash Flow")
        fc3 = _cagr(fcf_vals, 3, cf_fiscal_years)
        fc5 = _cagr(fcf_vals, 5, cf_fiscal_years)
        cagr_table("FCF", fc3, fc5, None)
        st.plotly_chart(
            bar_chart(cf_years, fcf_vals, "Free Cash Flow (₹ Cr)", "₹ Cr"),
            use_container_width=True,
        )


def _cagr(values: list, years: int, fiscal_years: list | None = None):
    from src.calculations.growth import _cagr_from_series
    r = _cagr_from_series(values, years, f"{years}Y", fiscal_years=fiscal_years)
    return r.value
