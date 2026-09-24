"""Cash Flow analysis page."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.calculations import free_cash_flow, cfo_pat_ratio, fcf_pat_ratio
from src.calculations.helpers import is_valid
from src.ui.charts import dual_bar_chart, line_chart, bar_chart
from src.ui.components import section_header


def render(
    income_df: pd.DataFrame,
    cashflow_df: pd.DataFrame,
    balance_df: pd.DataFrame | None,
    market_data: dict | None,
    statement_type: str,
) -> None:
    section_header("Cash Flow Analysis", "Cash generation quality and capital allocation")

    if cashflow_df is None or cashflow_df.empty:
        st.info("No cash flow data available.")
        return

    cf = cashflow_df.sort_values("fiscal_year")
    inc = income_df.sort_values("fiscal_year") if income_df is not None and not income_df.empty else pd.DataFrame()
    years_cf = [f"FY{y}" for y in cf["fiscal_year"]]

    # Compute FCF
    cfo_vals = cf["operating_cash_flow"].tolist()
    capex_vals = cf["capital_expenditure"].tolist() if "capital_expenditure" in cf.columns else [None] * len(cf)

    fcf_vals = []
    for cfo, capex in zip(cfo_vals, capex_vals):
        r = free_cash_flow(cfo, capex)
        fcf_vals.append(r.value)

    # Latest metrics
    latest_cfo = cfo_vals[-1] if cfo_vals else None
    latest_fcf = fcf_vals[-1] if fcf_vals else None
    latest_pat = inc.iloc[-1].get("pat") if not inc.empty else None

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CFO (Latest)", f"₹{latest_cfo:,.0f} Cr" if is_valid(latest_cfo) else "N/A")
    col2.metric("FCF (Latest)", f"₹{latest_fcf:,.0f} Cr" if is_valid(latest_fcf) else "N/A")

    cfo_r = cfo_pat_ratio(latest_cfo, latest_pat)
    col3.metric("CFO/PAT", f"{cfo_r.value:.2f}x" if is_valid(cfo_r.value) else "N/A")

    fcf_r = fcf_pat_ratio(latest_fcf, latest_pat)
    col4.metric("FCF/PAT", f"{fcf_r.value:.2f}x" if is_valid(fcf_r.value) else "N/A")

    st.divider()

    # PAT vs CFO and FCF vs CFO charts
    if not inc.empty and "pat" in inc.columns:
        merged_years = []
        merged_pats = []
        merged_cfos = []
        for fy in cf["fiscal_year"]:
            inc_row = inc[inc["fiscal_year"] == fy]
            if not inc_row.empty:
                merged_years.append(f"FY{fy}")
                merged_pats.append(inc_row.iloc[0].get("pat"))
                merged_cfos.append(cf[cf["fiscal_year"] == fy].iloc[0].get("operating_cash_flow"))

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.plotly_chart(
                dual_bar_chart(merged_years, merged_pats, "PAT", merged_cfos, "CFO",
                               "PAT vs Operating Cash Flow (₹ Cr)"),
                use_container_width=True,
            )
        with col_c2:
            st.plotly_chart(
                dual_bar_chart(years_cf, fcf_vals, "FCF", cfo_vals, "CFO",
                               "FCF vs CFO (₹ Cr)"),
                use_container_width=True,
            )

    # CapEx trend
    if capex_vals and any(v is not None for v in capex_vals):
        capex_abs = [abs(v) if v is not None else None for v in capex_vals]
        st.markdown("#### Capital Expenditure")
        st.plotly_chart(
            bar_chart(years_cf, capex_abs, "Capital Expenditure (₹ Cr)", "₹ Cr", color="warning"),
            use_container_width=True,
        )

    # CFO/PAT trend
    cfo_pat_series = []
    if not inc.empty:
        for fy in cf["fiscal_year"]:
            cf_row = cf[cf["fiscal_year"] == fy]
            inc_row = inc[inc["fiscal_year"] == fy]
            if not cf_row.empty and not inc_row.empty:
                r = cfo_pat_ratio(
                    cf_row.iloc[0].get("operating_cash_flow"),
                    inc_row.iloc[0].get("pat"),
                )
                cfo_pat_series.append(r.value)
            else:
                cfo_pat_series.append(None)

        st.divider()
        st.markdown("#### CFO/PAT Ratio Trend")
        st.caption("Values consistently below 0.7 warrant investigation into cash quality.")
        st.plotly_chart(
            line_chart(years_cf, cfo_pat_series, "CFO/PAT", "x",
                       reference_line=0.7, reference_label="0.7 threshold"),
            use_container_width=True,
        )

    # ------------------------------------------------------------------
    # Earnings Quality — EarningsQualityAnalyzer
    # ------------------------------------------------------------------
    if not inc.empty:
        _render_earnings_quality(inc, cf, balance_df)


def _render_earnings_quality(
    inc: pd.DataFrame,
    cf: pd.DataFrame,
    balance_df: pd.DataFrame | None,
) -> None:
    """Render the Earnings Quality section using EarningsQualityAnalyzer."""
    from src.analysis.earnings_quality import EarningsQualityAnalyzer

    bal = balance_df.sort_values("fiscal_year") if balance_df is not None and not balance_df.empty else pd.DataFrame()

    try:
        result = EarningsQualityAnalyzer().analyze(inc, cf, bal)
    except Exception:
        return

    st.divider()
    st.markdown("#### Earnings Quality")
    st.caption(
        "Earnings quality measures how well reported accounting profit is backed by actual cash flows. "
        "High-quality earnings are closely matched by operating cash."
    )

    # Divergence warning — most actionable signal
    if result.divergence_note:
        st.warning(result.divergence_note)

    # 5Y PAT vs CFO CAGR comparison
    has_growth = result.pat_growth_5y is not None or result.cfo_growth_5y is not None
    if has_growth:
        col1, col2, col3 = st.columns(3)
        col1.metric(
            "PAT 5Y CAGR",
            f"{result.pat_growth_5y:.1f}%" if result.pat_growth_5y is not None else "N/A",
        )
        col2.metric(
            "CFO 5Y CAGR",
            f"{result.cfo_growth_5y:.1f}%" if result.cfo_growth_5y is not None else "N/A",
        )
        if result.pat_growth_5y is not None and result.cfo_growth_5y is not None:
            diff = result.pat_growth_5y - result.cfo_growth_5y
            col3.metric(
                "PAT − CFO CAGR Spread",
                f"{diff:+.1f}pp",
                help="Positive means PAT grew faster than CFO. Above +20pp is a concern.",
            )

    # FCF/PAT trend
    if result.fcf_pat_series:
        years_fcf = [f"FY{y}" for y, _ in result.fcf_pat_series]
        vals_fcf = [v for _, v in result.fcf_pat_series]
        if any(v is not None for v in vals_fcf):
            st.plotly_chart(
                line_chart(
                    years_fcf, vals_fcf, "FCF/PAT", "x",
                    reference_line=0.7, reference_label="0.7 threshold",
                ),
                use_container_width=True,
            )

    # Other Income / PBT %
    if result.other_income_pbt_pct:
        years_oi = [f"FY{y}" for y, _ in result.other_income_pbt_pct]
        vals_oi = [v for _, v in result.other_income_pbt_pct]
        if any(v is not None for v in vals_oi):
            st.markdown("##### Other Income as % of PBT")
            st.caption(
                "A high or rising share of other income in PBT suggests profits may depend on "
                "non-operating or potentially non-recurring sources (e.g., interest income, asset sales)."
            )
            st.plotly_chart(
                line_chart(years_oi, vals_oi, "Other Income / PBT (%)", "%"),
                use_container_width=True,
            )
