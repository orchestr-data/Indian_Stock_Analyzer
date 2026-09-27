"""Overview page — company snapshot and key metrics summary."""

from __future__ import annotations
from typing import Optional

import pandas as pd
import streamlit as st

from src.calculations import (
    roe, roce, roa, debt_equity, cfo_pat_ratio, free_cash_flow, fcf_yield,
    operating_margin, revenue_cagr, pat_cagr, eps_cagr, pb_ratio,
)
from src.calculations.helpers import is_valid
from src.ui.charts import bar_chart, line_with_bar, format_inr
from src.ui.components import (
    section_header, statement_type_badge, not_available, cagr_table,
)

_FINANCIAL_SECTORS = frozenset({"BANKING", "NBFC", "INSURANCE"})


def render(
    company: dict,
    income_df: pd.DataFrame,
    balance_df: pd.DataFrame,
    cashflow_df: pd.DataFrame,
    market_data: Optional[dict],
    statement_type: str,
    sector: str = "DEFAULT",
) -> None:
    """Render the Overview page."""
    # Company header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(company.get("company_name", "Unknown Company"))
        ticker = company.get("ticker", "")
        nse = company.get("nse_symbol")
        bse = company.get("bse_code")
        symbol_str = f"NSE: {nse}" if nse else (f"BSE: {bse}" if bse else ticker)
        st.markdown(f"**{symbol_str}** | Sector: **{company.get('sector', 'N/A')}**")
    with col2:
        statement_type_badge(statement_type)
        if income_df is not None and not income_df.empty:
            latest_fy = int(income_df["fiscal_year"].max())
            st.caption(f"Latest data: FY{latest_fy}")

    st.divider()

    # Key metrics cards
    if income_df is None or income_df.empty:
        st.info("No financial data imported yet. Use the sidebar to import a Screener Excel file.")
        return

    income_df = income_df.sort_values("fiscal_year")
    latest = income_df.iloc[-1]
    prev = income_df.iloc[-2] if len(income_df) >= 2 else None

    section_header("Key Metrics Snapshot")

    is_financial = sector in _FINANCIAL_SECTORS

    col1, col2, col3, col4 = st.columns(4)

    pat = latest.get("pat")
    eq = prev_eq = borr = cash = assets = prev_assets = None
    if balance_df is not None and not balance_df.empty:
        bl = balance_df.sort_values("fiscal_year")
        bl_latest = bl.iloc[-1]
        eq = bl_latest.get("shareholders_equity")
        prev_eq = bl.iloc[-2].get("shareholders_equity") if len(bl) >= 2 else None
        borr = bl_latest.get("borrowings")
        cash = bl_latest.get("cash_and_equivalents")
        assets = bl_latest.get("total_assets")
        prev_assets = bl.iloc[-2].get("total_assets") if len(bl) >= 2 else None

    with col1:
        if market_data:
            mc = market_data.get("market_cap")
            st.metric("Market Cap", format_inr(mc) if is_valid(mc) else "N/A")
            price = market_data.get("price")
            st.metric("Price", f"₹{price:.2f}" if is_valid(price) else "N/A")
        else:
            not_available("Market data not imported")

    with col2:
        pe = market_data.get("pe") if market_data else None
        st.metric("P/E", f"{pe:.1f}x" if is_valid(pe) else "N/A")

        if is_financial:
            # P/B is the primary valuation metric for financial companies
            pb = market_data.get("pb") if market_data else None
            st.metric("P/B", f"{pb:.2f}x" if is_valid(pb) else "N/A")
        else:
            rev = latest.get("revenue")
            op = latest.get("operating_profit")
            om = operating_margin(op, rev)
            st.metric("OPM", f"{om.value:.1f}%" if is_valid(om.value) else "N/A")

    with col3:
        r = roe(pat, eq, prev_eq, minority_interest=latest.get("minority_interest"))
        st.metric("ROE", f"{r.value:.1f}%" if is_valid(r.value) else "N/A")

        if is_financial:
            # ROA is the primary returns metric for banks (ROCE excluded)
            r_roa = roa(pat, assets, prev_assets)
            st.metric("ROA", f"{r_roa.value:.2f}%" if is_valid(r_roa.value) else "N/A")
        else:
            ebit = latest.get("ebit")
            rc = roce(ebit, eq, borr, cash)
            st.metric("ROCE", f"{rc.value:.1f}%" if is_valid(rc.value) else "N/A")

    with col4:
        cfo = None
        if cashflow_df is not None and not cashflow_df.empty:
            cf = cashflow_df.sort_values("fiscal_year").iloc[-1]
            cfo = cf.get("operating_cash_flow")
        cfo_r = cfo_pat_ratio(cfo, pat)
        st.metric("CFO/PAT", f"{cfo_r.value:.2f}x" if is_valid(cfo_r.value) else "N/A")

        if is_financial:
            # D/E is excluded for financial companies; show Total Assets instead
            st.metric("Total Assets", format_inr(assets) if is_valid(assets) else "N/A")
        else:
            de = debt_equity(borr, eq)
            st.metric("D/E", f"{de.value:.2f}x" if is_valid(de.value) else "N/A")

    st.divider()

    # CAGR Summary
    section_header("Growth Summary (CAGR)")

    revenue_list = income_df["revenue"].tolist()
    pat_list = income_df["pat"].tolist()
    eps_list = income_df["basic_eps"].tolist() if "basic_eps" in income_df.columns else [None] * len(income_df)

    tab1, tab2, tab3 = st.tabs(["Revenue CAGR", "PAT CAGR", "EPS CAGR"])
    with tab1:
        r3 = revenue_cagr(revenue_list, 3)
        r5 = revenue_cagr(revenue_list, 5)
        r10 = revenue_cagr(revenue_list, 10)
        cagr_table("Revenue", r3.value, r5.value, r10.value)

    with tab2:
        p3 = pat_cagr(pat_list, 3)
        p5 = pat_cagr(pat_list, 5)
        p10 = pat_cagr(pat_list, 10)
        cagr_table("PAT", p3.value, p5.value, p10.value)

    with tab3:
        e3 = eps_cagr(eps_list, 3)
        e5 = eps_cagr(eps_list, 5)
        e10 = eps_cagr(eps_list, 10)
        cagr_table("EPS", e3.value, e5.value, e10.value)

    # Revenue & Profit trend charts
    st.divider()
    section_header("Financial Trends")

    years = [f"FY{y}" for y in income_df["fiscal_year"].tolist()]
    revenues = income_df["revenue"].tolist()
    pats = income_df["pat"].tolist()

    col_r, col_p = st.columns(2)
    with col_r:
        st.plotly_chart(
            bar_chart(years, revenues, "Revenue (₹ Cr)", "₹ Cr"),
            use_container_width=True,
        )
    with col_p:
        st.plotly_chart(
            bar_chart(years, pats, "Net Profit (₹ Cr)", "₹ Cr", color="positive"),
            use_container_width=True,
        )
