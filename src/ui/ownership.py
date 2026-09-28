"""Ownership / shareholding page."""

from __future__ import annotations
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src.analysis.ownership_analysis import build_ownership_history
from src.analysis.corporate_actions import analyze_share_count
from src.calculations.helpers import is_valid
from src.ui.charts import stacked_area_chart, line_chart
from src.ui.components import section_header


def render(shareholding_df: pd.DataFrame, income_df: pd.DataFrame) -> None:
    section_header("Ownership", "Promoter holding, institutional ownership, and share dilution trends")

    if shareholding_df is None or shareholding_df.empty:
        st.info("No shareholding data available.")
        return

    history = build_ownership_history(shareholding_df)
    if not history:
        return

    periods = [h.period for h in history]

    # Promoter holding trend
    promoter_vals = [h.promoter_pct for h in history]
    pledge_vals = [h.promoter_pledge_pct for h in history]
    fii_vals = [h.fii_pct for h in history]
    dii_vals = [h.dii_pct for h in history]
    public_vals = [h.public_pct for h in history]

    # Latest snapshot
    latest = history[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Promoter Holding", f"{latest.promoter_pct:.1f}%" if is_valid(latest.promoter_pct) else "N/A")
    col2.metric("Promoter Pledge",
                f"{latest.promoter_pledge_pct:.1f}%" if is_valid(latest.promoter_pledge_pct) else "N/A")
    col3.metric("FII", f"{latest.fii_pct:.1f}%" if is_valid(latest.fii_pct) else "N/A")
    col4.metric("DII", f"{latest.dii_pct:.1f}%" if is_valid(latest.dii_pct) else "N/A")

    if is_valid(latest.promoter_pledge_pct) and latest.promoter_pledge_pct > 0:
        st.warning(
            f"⚠️ Promoter shares pledged: {latest.promoter_pledge_pct:.1f}% of promoter holding. "
            "Investigate the purpose and monitor for changes."
        )

    st.divider()

    # Ownership composition chart
    series = {}
    if any(v is not None for v in promoter_vals):
        series["Promoter"] = [v or 0 for v in promoter_vals]
    if any(v is not None for v in fii_vals):
        series["FII"] = [v or 0 for v in fii_vals]
    if any(v is not None for v in dii_vals):
        series["DII"] = [v or 0 for v in dii_vals]
    if any(v is not None for v in public_vals):
        series["Public"] = [v or 0 for v in public_vals]

    if series:
        st.plotly_chart(
            stacked_area_chart(periods, series, "Shareholding Composition (%)"),
            use_container_width=True,
        )

    # Promoter holding trend line
    st.plotly_chart(
        line_chart(periods, promoter_vals, "Promoter Holding (%)", "%"),
        use_container_width=True,
    )

    # Pledge
    if any(v is not None and v > 0 for v in pledge_vals):
        st.markdown("#### Promoter Pledge Trend")
        st.plotly_chart(
            line_chart(periods, pledge_vals, "Promoter Pledge (% of Promoter Holding)", "%",
                       color="warning"),
            use_container_width=True,
        )

    # Share count dilution
    st.divider()
    st.markdown("#### Share Count History")
    if income_df is not None and not income_df.empty:
        share_analysis = analyze_share_count(income_df.sort_values("fiscal_year"))
        if share_analysis.series:
            syears = [f"FY{yr}" for yr, _ in share_analysis.series]
            svals = [v for _, v in share_analysis.series]
            st.plotly_chart(
                line_chart(syears, svals, "Weighted Avg Shares (Cr)", "Cr shares"),
                use_container_width=True,
            )
            if share_analysis.total_change_pct is not None:
                chg = share_analysis.total_change_pct
                if abs(chg) > 1:
                    st.caption(
                        f"Share count {'increased' if chg > 0 else 'decreased'} by "
                        f"{abs(chg):.1f}% over the available history. "
                        "Investigate ESOPs, QIPs, buybacks, or splits if applicable."
                    )
    else:
        st.caption("Share count data requires income statement data with weighted average shares.")
