"""Data Quality page."""

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
    section_header("Data Quality", "Validation results and data coverage summary")

    if import_history_df is not None and not import_history_df.empty:
        st.markdown("#### Import History")
        for _, row in import_history_df.iterrows():
            status = row.get("status", "unknown")
            color = "🟢" if status == "success" else "🟡" if status == "warning" else "🔴"
            st.markdown(
                f"{color} **{row.get('source_file', 'Unknown')}** — "
                f"{row.get('statement_type', '')} | "
                f"{str(row.get('import_timestamp', ''))[:19]}"
            )
            warnings = row.get("warnings")
            if warnings and str(warnings) != "nan":
                st.caption(f"Warnings: {warnings}")

    st.divider()

    # Data coverage
    st.markdown("#### Data Coverage")
    checks = []

    if income_df is not None and not income_df.empty:
        fy_range = f"FY{income_df['fiscal_year'].min()} – FY{income_df['fiscal_year'].max()}"
        checks.append(("✅", "Annual Income Statement", f"{len(income_df)} years ({fy_range})"))
    else:
        checks.append(("❌", "Annual Income Statement", "Not imported"))

    if balance_df is not None and not balance_df.empty:
        checks.append(("✅", "Balance Sheet", f"{len(balance_df)} years"))
    else:
        checks.append(("❌", "Balance Sheet", "Not imported"))

    if cashflow_df is not None and not cashflow_df.empty:
        checks.append(("✅", "Cash Flow Statement", f"{len(cashflow_df)} years"))
    else:
        checks.append(("❌", "Cash Flow Statement", "Not imported"))

    if shareholding_df is not None and not shareholding_df.empty:
        checks.append(("✅", "Shareholding Pattern", f"{len(shareholding_df)} periods"))
    else:
        checks.append(("❌", "Shareholding Pattern", "Not imported"))

    for icon, name, note in checks:
        st.markdown(f"{icon} **{name}:** {note}")

    st.divider()
    st.markdown("#### Missing Fields")
    if income_df is not None and not income_df.empty:
        null_counts = income_df.isnull().sum()
        missing = null_counts[null_counts > 0]
        if not missing.empty:
            st.caption("Fields with missing values in income statement:")
            st.write(missing.to_dict())
        else:
            st.success("No missing fields in income statement.")
