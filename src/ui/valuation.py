"""Valuation page — current multiples and historical context."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.calculations import pe_ratio, pb_ratio, peg_ratio, enterprise_value, ev_ebitda, ev_ebit, fcf_yield
from src.calculations.helpers import is_valid, median
from src.ui.charts import line_chart, bar_chart
from src.ui.components import section_header, not_available

_FINANCIAL_SECTORS = frozenset({"BANKING", "NBFC", "INSURANCE"})


def render(
    income_df: pd.DataFrame,
    balance_df: pd.DataFrame,
    cashflow_df: pd.DataFrame,
    market_data: dict | None,
    market_history_df: pd.DataFrame,
    statement_type: str,
    sector: str = "DEFAULT",
) -> None:
    section_header(
        "Valuation",
        "Current multiples and historical context — no cheap/expensive labels",
    )

    if market_data is None:
        st.info("No market data available. Market data is not automatically fetched.")
        st.caption("Import a Screener Excel export that includes market data (price, P/E, P/B) to enable this page.")
        return

    income_df = income_df.sort_values("fiscal_year") if income_df is not None and not income_df.empty else pd.DataFrame()
    balance_df = balance_df.sort_values("fiscal_year") if balance_df is not None and not balance_df.empty else pd.DataFrame()
    cashflow_df = cashflow_df.sort_values("fiscal_year") if cashflow_df is not None and not cashflow_df.empty else pd.DataFrame()

    pe = market_data.get("pe")
    pb = market_data.get("pb")
    mc = market_data.get("market_cap")
    is_financial = sector in _FINANCIAL_SECTORS

    # ------------------------------------------------------------------ current multiples
    st.markdown("#### Current Valuation Multiples")

    borr, cash_val, ebitda_val, latest_fcf = None, None, None, None
    if not balance_df.empty:
        bl = balance_df.iloc[-1]
        borr = bl.get("borrowings")
        cash_val = bl.get("cash_and_equivalents")
    if not income_df.empty:
        ebitda_val = income_df.iloc[-1].get("ebitda")
    if not cashflow_df.empty and "free_cash_flow" in cashflow_df.columns:
        latest_fcf = cashflow_df.iloc[-1].get("free_cash_flow")

    ev = enterprise_value(mc, borr, cash_val)
    ev_eb = ev_ebitda(ev.value, ebitda_val)
    fy = fcf_yield(latest_fcf, mc)

    if is_financial:
        col1, col2, col3 = st.columns(3)
        col1.metric("P/E", f"{pe:.1f}x" if is_valid(pe) else "N/A")
        col2.metric("P/B", f"{pb:.2f}x" if is_valid(pb) else "N/A",
                    help="Primary valuation metric for financial intermediaries")
        col3.metric("FCF Yield", f"{fy.value:.1f}%" if is_valid(fy.value) else "N/A")
        st.caption("EV/EBITDA is excluded for financial sector (not meaningful for banks/NBFC/insurance).")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("P/E", f"{pe:.1f}x" if is_valid(pe) else "N/A")
        col2.metric("P/B", f"{pb:.2f}x" if is_valid(pb) else "N/A")
        col3.metric("EV/EBITDA", f"{ev_eb.value:.1f}x" if is_valid(ev_eb.value) else "N/A")
        col4.metric("FCF Yield", f"{fy.value:.1f}%" if is_valid(fy.value) else "N/A")

    # ------------------------------------------------------------------ synthetic multiples
    st.divider()
    _render_synthetic_multiples(income_df, balance_df, mc, is_financial)

    # ------------------------------------------------------------------ market data snapshots
    if not market_history_df.empty and len(market_history_df) >= 2:
        st.divider()
        _render_snapshot_history(market_history_df)

    # ------------------------------------------------------------------ EV note
    st.divider()
    if not is_financial:
        st.markdown("#### Enterprise Value Definition")
        st.markdown(
            """
**EV = Market Cap + Interest-Bearing Debt − Cash**

The theoretical acquisition cost of the business — you pay the market cap to buy equity,
inherit the debt, and receive the cash. Different providers may include minority interest,
preference shares, or lease liabilities differently.
            """
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _render_synthetic_multiples(
    income_df: pd.DataFrame,
    balance_df: pd.DataFrame,
    market_cap,
    is_financial: bool,
) -> None:
    """Show current market cap as a multiple of historical PAT and equity."""
    from src.analysis.valuation_analysis import compute_synthetic_multiples
    from src.ui.charts import format_inr

    st.markdown("#### Price-to-Historical Earnings")
    st.caption(
        f"Computed as: **Current Market Cap** ({"₹" + format_inr(market_cap) if is_valid(market_cap) else "N/A"}) "
        "÷ historical PAT or equity for each fiscal year. "
        "**Not the same as historical P/E** — this uses today's market cap against past earnings, "
        "showing how current price relates to the company's earnings history."
    )

    syn = compute_synthetic_multiples(income_df, balance_df, market_cap)

    if not syn.mc_over_pat:
        st.info("Income data required to compute price-to-historical-earnings.")
        return

    years_pat = [f"FY{fy}" for fy, _ in syn.mc_over_pat]
    vals_pat = [v for _, v in syn.mc_over_pat]

    col1, col2, col3 = st.columns(3)
    current_mc_pat = vals_pat[-1] if vals_pat else None
    col1.metric(
        "Current MC/PAT",
        f"{current_mc_pat:.1f}x" if is_valid(current_mc_pat) else "N/A",
        help="Current market cap / latest year PAT",
    )
    col2.metric(
        "3Y Median MC/PAT",
        f"{syn.median_mc_over_pat_3y:.1f}x" if is_valid(syn.median_mc_over_pat_3y) else "N/A",
    )
    col3.metric(
        "5Y Median MC/PAT",
        f"{syn.median_mc_over_pat_5y:.1f}x" if is_valid(syn.median_mc_over_pat_5y) else "N/A",
    )

    st.plotly_chart(
        bar_chart(years_pat, vals_pat, "Market Cap / Historical PAT (x)", "x"),
        use_container_width=True,
    )

    # P/B based on historical equity (key for banking)
    if syn.mc_over_equity:
        label_pb = "Price-to-Historical Book"
        if is_financial:
            st.markdown(f"#### {label_pb}")
            st.caption(
                "Current market cap ÷ historical shareholders equity. "
                "P/B is the primary valuation multiple for financial intermediaries."
            )
        else:
            st.markdown(f"#### {label_pb}")
            st.caption("Current market cap ÷ historical shareholders equity.")

        years_eq = [f"FY{fy}" for fy, _ in syn.mc_over_equity]
        vals_eq = [v for _, v in syn.mc_over_equity]

        col1, col2, col3 = st.columns(3)
        current_mc_eq = vals_eq[-1] if vals_eq else None
        col1.metric(
            "Current MC/Equity",
            f"{current_mc_eq:.2f}x" if is_valid(current_mc_eq) else "N/A",
        )
        col2.metric(
            "3Y Median MC/Equity",
            f"{syn.median_mc_over_equity_3y:.2f}x" if is_valid(syn.median_mc_over_equity_3y) else "N/A",
        )
        col3.metric(
            "5Y Median MC/Equity",
            f"{syn.median_mc_over_equity_5y:.2f}x" if is_valid(syn.median_mc_over_equity_5y) else "N/A",
        )

        st.plotly_chart(
            bar_chart(years_eq, vals_eq, "Market Cap / Historical Equity (x)", "x", color="positive"),
            use_container_width=True,
        )


def _render_snapshot_history(market_history_df: pd.DataFrame) -> None:
    """Show accumulated market data snapshots when ≥2 imports exist."""
    from src.analysis.valuation_analysis import analyze_pe_history, analyze_pb_history

    st.markdown("#### Historical Market Data Snapshots")
    st.caption(
        f"{len(market_history_df)} data point(s) accumulated from Screener imports. "
        "Each row is one import's market data at that date."
    )

    pe_hist = analyze_pe_history(market_history_df)
    pb_hist = analyze_pb_history(market_history_df)

    # Summary stats row
    n = len(market_history_df)
    if n >= 3 and (pe_hist.series or pb_hist.series):
        pe_vals = [v for _, v in pe_hist.series]
        pb_vals = [v for _, v in pb_hist.series]

        col1, col2, col3, col4 = st.columns(4)
        pe_min = min((v for v in pe_vals if is_valid(v)), default=None)
        pe_max = max((v for v in pe_vals if is_valid(v)), default=None)
        pb_min = min((v for v in pb_vals if is_valid(v)), default=None)
        pb_max = max((v for v in pb_vals if is_valid(v)), default=None)

        col1.metric("P/E Median", f"{pe_hist.median_5y:.1f}x" if is_valid(pe_hist.median_5y) else "N/A")
        col2.metric("P/E Range", f"{pe_min:.1f}–{pe_max:.1f}x" if is_valid(pe_min) and is_valid(pe_max) else "N/A")
        col3.metric("P/B Median", f"{pb_hist.median_5y:.2f}x" if is_valid(pb_hist.median_5y) else "N/A")
        col4.metric("P/B Range", f"{pb_min:.2f}–{pb_max:.2f}x" if is_valid(pb_min) and is_valid(pb_max) else "N/A")

        # Premium/discount to median
        if is_valid(pe_hist.premium_to_5y_median_pct):
            sign = "+" if pe_hist.premium_to_5y_median_pct >= 0 else ""
            label = f"P/E is {sign}{pe_hist.premium_to_5y_median_pct:.1f}% vs its own 5Y median"
            if pe_hist.premium_to_5y_median_pct > 20:
                st.warning(f"⚠ {label}")
            elif pe_hist.premium_to_5y_median_pct < -20:
                st.info(f"ℹ {label}")
            else:
                st.caption(f"Context: {label}")

    # Charts side by side
    col_pe, col_pb = st.columns(2)
    if pe_hist.series and len(pe_hist.series) >= 2:
        dates_pe = [d for d, _ in pe_hist.series]
        vals_pe = [v for _, v in pe_hist.series]
        ref_line = pe_hist.median_5y
        with col_pe:
            st.plotly_chart(
                line_chart(
                    dates_pe, vals_pe, "P/E History (x)", "x",
                    reference_line=ref_line,
                    reference_label="5Y median" if is_valid(ref_line) else None,
                ),
                use_container_width=True,
            )
    if pb_hist.series and len(pb_hist.series) >= 2:
        dates_pb = [d for d, _ in pb_hist.series]
        vals_pb = [v for _, v in pb_hist.series]
        ref_line_pb = pb_hist.median_5y
        with col_pb:
            st.plotly_chart(
                line_chart(
                    dates_pb, vals_pb, "P/B History (x)", "x",
                    reference_line=ref_line_pb,
                    reference_label="5Y median" if is_valid(ref_line_pb) else None,
                ),
                use_container_width=True,
            )

    # Raw table — let user see every snapshot
    with st.expander("All snapshots"):
        display = market_history_df.copy()
        display["date"] = display["date"].astype(str)
        keep = ["date", "price", "market_cap", "pe", "pb", "ev_ebitda", "dividend_yield"]
        keep = [c for c in keep if c in display.columns]
        st.dataframe(display[keep].sort_values("date", ascending=False).reset_index(drop=True),
                     use_container_width=True)
