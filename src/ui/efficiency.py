"""Working capital efficiency page."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.calculations import receivable_days, inventory_days, payable_days, cash_conversion_cycle, asset_turnover
from src.calculations.helpers import is_valid
from src.ui.charts import line_chart
from src.ui.components import section_header
from src.ui.constants import FINANCIAL_SECTORS as _FINANCIAL_SECTORS


def render(
    income_df: pd.DataFrame,
    balance_df: pd.DataFrame,
    statement_type: str,
    sector: str = "DEFAULT",
) -> None:
    is_financial = sector in _FINANCIAL_SECTORS
    section_header("Efficiency", "Working capital utilization and asset efficiency")

    if income_df is None or income_df.empty or balance_df is None or balance_df.empty:
        st.info("Income and balance sheet data required for efficiency analysis.")
        return

    if is_financial:
        _render_financial_efficiency(income_df, balance_df)
        return

    inc = income_df.sort_values("fiscal_year")
    bal = balance_df.sort_values("fiscal_year")

    merged = inc[["fiscal_year", "revenue", "expenses"]].merge(
        bal[["fiscal_year", "receivables", "inventory", "payables", "total_assets"]],
        on="fiscal_year", how="inner",
    )

    if merged.empty:
        st.info("Could not merge income and balance sheet data.")
        return

    years_label = [f"FY{y}" for y in merged["fiscal_year"]]
    rec_days_vals, inv_days_vals, pay_days_vals, ccc_vals = [], [], [], []

    for _, row in merged.iterrows():
        rev = row.get("revenue")
        exp = row.get("expenses")
        rec = row.get("receivables")
        inv = row.get("inventory")
        pay = row.get("payables")

        rd = receivable_days(rec, rev)
        id_ = inventory_days(inv, revenue=rev)
        pd_ = payable_days(pay, exp)

        rec_days_vals.append(rd.value)
        inv_days_vals.append(id_.value)
        pay_days_vals.append(pd_.value)

        ccc = cash_conversion_cycle(rd.value, id_.value, pd_.value)
        ccc_vals.append(ccc.value)

    # Latest snapshot
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Receivable Days", f"{rec_days_vals[-1]:.0f}" if is_valid(rec_days_vals[-1]) else "N/A")
    col2.metric("Inventory Days", f"{inv_days_vals[-1]:.0f}" if is_valid(inv_days_vals[-1]) else "N/A")
    col3.metric("Payable Days", f"{pay_days_vals[-1]:.0f}" if is_valid(pay_days_vals[-1]) else "N/A")
    col4.metric("CCC (days)", f"{ccc_vals[-1]:.0f}" if is_valid(ccc_vals[-1]) else "N/A")

    st.divider()
    col_r, col_i = st.columns(2)
    with col_r:
        st.plotly_chart(
            line_chart(years_label, rec_days_vals, "Receivable Days", "days"),
            use_container_width=True,
        )
    with col_i:
        if any(v is not None for v in inv_days_vals):
            st.plotly_chart(
                line_chart(years_label, inv_days_vals, "Inventory Days", "days", color="neutral"),
                use_container_width=True,
            )
        else:
            st.caption("Inventory data not available for this company.")

    st.plotly_chart(
        line_chart(years_label, ccc_vals, "Cash Conversion Cycle (days)", "days", color="secondary"),
        use_container_width=True,
    )

    # Asset turnover
    at_vals = []
    prev_assets = None
    for _, row in merged.iterrows():
        rev = row.get("revenue")
        assets = row.get("total_assets")
        at = asset_turnover(rev, assets, prev_assets)
        at_vals.append(at.value)
        prev_assets = assets

    st.divider()
    st.markdown("#### Asset Turnover")
    st.plotly_chart(
        line_chart(years_label, at_vals, "Asset Turnover (x)", "x", color="primary"),
        use_container_width=True,
    )


def _render_financial_efficiency(income_df: pd.DataFrame, balance_df: pd.DataFrame) -> None:
    """Efficiency page for banking/NBFC/insurance — working capital metrics don't apply."""
    st.info(
        "Inventory days, payable days, and cash conversion cycle (CCC) do not apply to "
        "financial intermediaries. Key efficiency metrics for banks (NIM, Cost-to-Income, "
        "GNPA) are on the **Sector Analysis** page."
    )

    inc = income_df.sort_values("fiscal_year")
    bal = balance_df.sort_values("fiscal_year")

    merged = inc[["fiscal_year", "revenue"]].merge(
        bal[["fiscal_year", "total_assets"]],
        on="fiscal_year", how="inner",
    )
    if merged.empty:
        return

    years_label = [f"FY{y}" for y in merged["fiscal_year"]]

    # Asset turnover is still meaningful (even for banks it shows revenue productivity)
    at_vals = []
    prev_assets = None
    for _, row in merged.iterrows():
        rev = row.get("revenue")
        assets = row.get("total_assets")
        at = asset_turnover(rev, assets, prev_assets)
        at_vals.append(at.value)
        prev_assets = assets

    st.markdown("#### Asset Turnover")
    st.caption("Revenue / Average Total Assets — lower than manufacturing companies is normal for banks.")
    st.plotly_chart(
        line_chart(years_label, at_vals, "Asset Turnover (x)", "x", color="primary"),
        use_container_width=True,
    )

    # Approximate cost-to-income from P&L
    ci_vals = []
    for _, row in inc.iterrows():
        rev = row.get("revenue")
        exp = row.get("expenses")
        if rev and exp and rev > 0:
            ci_vals.append(round(exp / rev * 100, 1))
        else:
            ci_vals.append(None)

    if any(v is not None for v in ci_vals):
        inc_years = [f"FY{y}" for y in inc["fiscal_year"]]
        st.markdown("#### Cost-to-Income Ratio (Approximate)")
        st.caption("Expenses / Revenue — approximation from Screener data; may differ from reported C/I ratio.")
        st.plotly_chart(
            line_chart(inc_years, ci_vals, "Cost-to-Income (%)", "%", color="neutral"),
            use_container_width=True,
        )
