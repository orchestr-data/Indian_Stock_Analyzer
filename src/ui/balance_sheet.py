"""Balance Sheet analysis page."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.calculations import debt_equity, net_debt, net_debt_ebitda, interest_coverage
from src.ui.charts import bar_chart, line_chart, dual_bar_chart, format_inr
from src.ui.components import section_header, not_available
from src.ui.constants import FINANCIAL_SECTORS as _FINANCIAL_SECTORS


def render(
    balance_df: pd.DataFrame,
    income_df: pd.DataFrame,
    statement_type: str,
    sector: str = "DEFAULT",
) -> None:
    is_financial = sector in _FINANCIAL_SECTORS

    if is_financial:
        section_header(
            "Balance Sheet Analysis",
            "Asset structure and capitalization — D/E and EV/EBITDA excluded for financial sector",
        )
    else:
        section_header("Balance Sheet Analysis", "Debt, equity, and asset structure over time")

    if balance_df is None or balance_df.empty:
        st.info("No balance sheet data available.")
        return

    balance_df = balance_df.sort_values("fiscal_year")
    income_df = income_df.sort_values("fiscal_year") if income_df is not None and not income_df.empty else pd.DataFrame()
    years_label = [f"FY{y}" for y in balance_df["fiscal_year"]]

    latest_b = balance_df.iloc[-1]
    latest_inc = income_df.iloc[-1] if not income_df.empty else None

    borr = latest_b.get("borrowings")
    cash = latest_b.get("cash_and_equivalents")
    eq = latest_b.get("shareholders_equity")
    assets = latest_b.get("total_assets")
    ebitda = latest_inc.get("ebitda") if latest_inc is not None else None
    ebit = latest_inc.get("ebit") if latest_inc is not None else None
    interest = latest_inc.get("interest") if latest_inc is not None else None

    if is_financial:
        _render_financial_snapshot(
            balance_df, income_df, years_label,
            borr, cash, eq, assets, ebit, interest,
        )
    else:
        _render_standard_snapshot(
            balance_df, income_df, years_label,
            borr, cash, eq, ebitda, ebit, interest,
        )


def _render_financial_snapshot(balance_df, income_df, years_label, borr, cash, eq, assets, ebit, interest):
    """Balance sheet view for banking / NBFC / insurance — D/E and EV/EBITDA excluded."""
    st.caption(
        "For financial intermediaries, leverage is regulated via Capital Adequacy (see Sector Analysis page). "
        "D/E and Net Debt/EBITDA ratios are not meaningful here."
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Assets", format_inr(assets))
    col2.metric("Shareholders Equity", format_inr(eq))
    col3.metric("Borrowings / Liabilities", format_inr(borr))
    col4.metric("Cash & Equivalents", format_inr(cash))

    # Total assets trend — key metric for banks
    asset_vals = balance_df["total_assets"].tolist()
    eq_vals = balance_df["shareholders_equity"].tolist()

    st.divider()
    col_a, col_e = st.columns(2)
    with col_a:
        st.plotly_chart(
            bar_chart(years_label, asset_vals, "Total Assets (₹ Cr)", "₹ Cr"),
            use_container_width=True,
        )
    with col_e:
        st.plotly_chart(
            bar_chart(years_label, eq_vals, "Shareholders Equity (₹ Cr)", "₹ Cr", color="positive"),
            use_container_width=True,
        )

    # Borrowings trend (funding mix for bank)
    borr_vals = balance_df["borrowings"].tolist()
    cash_vals = balance_df["cash_and_equivalents"].tolist()
    col_b, col_c = st.columns(2)
    with col_b:
        st.plotly_chart(
            bar_chart(years_label, borr_vals, "Borrowings (₹ Cr)", "₹ Cr", color="neutral"),
            use_container_width=True,
        )
    with col_c:
        st.plotly_chart(
            bar_chart(years_label, cash_vals, "Cash & Equivalents (₹ Cr)", "₹ Cr"),
            use_container_width=True,
        )


def _render_standard_snapshot(balance_df, income_df, years_label, borr, cash, eq, ebitda, ebit, interest):
    """Standard balance sheet view for non-financial companies."""
    fy = int(balance_df.iloc[-1]["fiscal_year"])

    col1, col2, col3, col4 = st.columns(4)
    nd = net_debt(borr, cash, fiscal_year=fy)
    col1.metric("Borrowings", format_inr(borr))
    col2.metric("Cash", format_inr(cash))
    col3.metric("Net Debt", format_inr(nd.value) if nd.value is not None else "N/A",
                help=nd.note)

    de = debt_equity(borr, eq, fiscal_year=fy)
    col4.metric("D/E", f"{de.value:.2f}x" if de.value is not None else "N/A",
                help=de.note)

    col5, col6 = st.columns(2)
    nde = net_debt_ebitda(borr, cash, ebitda, fiscal_year=fy)
    ic = interest_coverage(ebit, interest)
    col5.metric("Net Debt/EBITDA", f"{nde.value:.1f}x" if nde.value is not None else "N/A")
    col6.metric("Interest Coverage", f"{ic.value:.1f}x" if ic.value is not None else "N/A")

    st.divider()

    borr_vals = balance_df["borrowings"].tolist()
    cash_vals = balance_df["cash_and_equivalents"].tolist()
    nd_vals = [
        (b - (c or 0)) if b is not None else None
        for b, c in zip(borr_vals, cash_vals)
    ]

    col_d, col_nd = st.columns(2)
    with col_d:
        st.plotly_chart(
            dual_bar_chart(years_label, borr_vals, "Borrowings", cash_vals, "Cash", "Debt vs Cash (₹ Cr)"),
            use_container_width=True,
        )
    with col_nd:
        st.plotly_chart(
            bar_chart(years_label, nd_vals, "Net Debt (₹ Cr)", "₹ Cr"),
            use_container_width=True,
        )

    if not income_df.empty and "ebit" in income_df.columns and "interest" in income_df.columns:
        ic_vals = []
        for _, row in income_df.iterrows():
            r = interest_coverage(row.get("ebit"), row.get("interest"))
            ic_vals.append(r.value)

        inc_years = [f"FY{y}" for y in income_df["fiscal_year"]]
        st.plotly_chart(
            line_chart(inc_years, ic_vals, "Interest Coverage (x)", "x",
                       reference_line=2.0, reference_label="Min. comfort"),
            use_container_width=True,
        )

    if "cwip" in balance_df.columns:
        cwip_vals = balance_df["cwip"].tolist()
        if any(v is not None and v > 0 for v in cwip_vals):
            st.divider()
            st.markdown("#### Capital Work in Progress (CWIP)")
            st.caption("High CWIP indicates ongoing capital investments. Monitor conversion to fixed assets.")
            st.plotly_chart(
                bar_chart(years_label, cwip_vals, "CWIP (₹ Cr)", "₹ Cr", color="neutral"),
                use_container_width=True,
            )
