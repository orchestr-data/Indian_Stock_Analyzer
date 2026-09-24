"""Peer comparison page."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.ui.components import section_header


def render(comparison_df: pd.DataFrame) -> None:
    section_header(
        "Peer Comparison",
        "Side-by-side comparison. No ranking. No scoring.",
    )

    if comparison_df is None or comparison_df.empty:
        st.info(
            "Select peer companies using the sidebar to compare. "
            "You can add up to 10 companies that have been imported."
        )
        return

    st.caption(
        "All values are from the latest available annual data for each company. "
        "Statement type may differ across companies."
    )

    display_cols = {
        "company_name": "Company",
        "ticker": "Ticker",
        "latest_fy": "Latest FY",
        "revenue_cr": "Revenue (₹ Cr)",
        "pat_cr": "PAT (₹ Cr)",
        "operating_margin_pct": "OPM (%)",
        "roe_pct": "ROE (%)",
        "roce_pct": "ROCE (%)",
        "debt_equity": "D/E",
        "cfo_pat": "CFO/PAT",
        "fcf_cr": "FCF (₹ Cr)",
    }

    available_cols = [c for c in display_cols if c in comparison_df.columns]
    display_df = comparison_df[available_cols].rename(columns=display_cols)

    # Format numerics
    numeric_fmts = {
        "Revenue (₹ Cr)": "{:,.0f}",
        "PAT (₹ Cr)": "{:,.0f}",
        "OPM (%)": "{:.1f}%",
        "ROE (%)": "{:.1f}%",
        "ROCE (%)": "{:.1f}%",
        "D/E": "{:.2f}x",
        "CFO/PAT": "{:.2f}x",
        "FCF (₹ Cr)": "{:,.0f}",
    }

    st.dataframe(display_df, use_container_width=True)

    st.divider()
    st.info(
        "Peer comparison is most meaningful when companies operate in the same sector "
        "and use the same accounting basis (Consolidated vs Standalone)."
    )
