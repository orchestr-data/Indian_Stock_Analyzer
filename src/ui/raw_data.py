"""Raw Data page — inspect imported data and source lineage."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.ui.components import section_header


def render(
    company_id: int,
    income_df: pd.DataFrame,
    balance_df: pd.DataFrame,
    cashflow_df: pd.DataFrame,
    shareholding_df: pd.DataFrame,
    import_history_df: pd.DataFrame,
    statement_type: str,
) -> None:
    section_header("Raw Data", "Inspect underlying imported data — for verification and debugging")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Income Statement", "Balance Sheet", "Cash Flow", "Shareholding", "Import History"
    ])

    with tab1:
        _show_df(income_df, "Annual Income Statement")

    with tab2:
        _show_df(balance_df, "Balance Sheet")

    with tab3:
        _show_df(cashflow_df, "Cash Flow Statement")

    with tab4:
        _show_df(shareholding_df, "Shareholding Pattern")

    with tab5:
        if import_history_df is not None and not import_history_df.empty:
            st.dataframe(import_history_df, use_container_width=True)
        else:
            st.info("No import history available.")

    st.divider()
    st.caption(
        "Raw data is stored exactly as parsed from source files. "
        "Values are in ₹ Crore unless otherwise noted. "
        "None/NaN values indicate the field was not present in the source."
    )


def _show_df(df: pd.DataFrame, label: str) -> None:
    if df is None or df.empty:
        st.info(f"No {label.lower()} data available.")
        return
    st.markdown(f"**{label}** — {len(df)} row(s)")
    st.dataframe(
        df.sort_values("fiscal_year") if "fiscal_year" in df.columns else df,
        use_container_width=True,
    )
