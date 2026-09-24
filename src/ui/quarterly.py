"""Quarterly results page."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.ui.charts import bar_chart, line_chart
from src.ui.components import section_header


def render(quarterly_df: pd.DataFrame, statement_type: str) -> None:
    section_header("Quarterly Results", "Quarter-on-quarter and year-on-year comparisons")

    if quarterly_df is None or quarterly_df.empty:
        st.info("No quarterly data available.")
        return

    df = quarterly_df.sort_values(["fiscal_year", "fiscal_quarter"]).copy()
    df["period_label"] = df.apply(lambda r: f"Q{int(r['fiscal_quarter'])} FY{int(r['fiscal_year'])}", axis=1)

    years_label = df["period_label"].tolist()
    rev_vals = df["revenue"].tolist()
    pat_vals = df["pat"].tolist()

    # QoQ and YoY comparisons
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            bar_chart(years_label[-8:], rev_vals[-8:], "Quarterly Revenue (₹ Cr)", "₹ Cr"),
            use_container_width=True,
        )
    with col2:
        st.plotly_chart(
            bar_chart(years_label[-8:], pat_vals[-8:], "Quarterly PAT (₹ Cr)", "₹ Cr", color="positive"),
            use_container_width=True,
        )

    # Operating margin quarterly
    if "operating_profit" in df.columns and "revenue" in df.columns:
        margin_vals = []
        for _, row in df.iterrows():
            rev = row.get("revenue")
            op = row.get("operating_profit")
            if rev and rev > 0 and op is not None:
                margin_vals.append(op / rev * 100.0)
            else:
                margin_vals.append(None)

        st.plotly_chart(
            line_chart(years_label[-8:], margin_vals[-8:], "Quarterly Operating Margin (%)", "%"),
            use_container_width=True,
        )

    st.divider()
    st.caption(
        "⚠️ Quarterly margins and EPS are NOT annualized. "
        "Comparing quarterly data directly to annual data can be misleading."
    )
    st.dataframe(df[["period_label", "revenue", "operating_profit", "pat", "eps"]].tail(12),
                 use_container_width=True)
