"""Corporate Actions page — share count history, dividends, buybacks, and action register."""

from __future__ import annotations
from datetime import date

import pandas as pd
import streamlit as st

from src.analysis.corporate_actions import (
    analyze_share_count,
    analyze_dividend_history,
    analyze_buyback_history,
)
from src.calculations.helpers import is_valid
from src.ui.charts import bar_chart, line_chart
from src.ui.components import section_header

_ACTION_TYPES = [
    "Dividend",
    "Bonus Issue",
    "Stock Split",
    "Rights Issue",
    "Buyback",
    "Merger / Demerger",
    "ESOP / Share Allotment",
    "Other",
]


def render(
    company_id: int,
    company: dict,
    income_df: pd.DataFrame,
    cashflow_df: pd.DataFrame,
    repo,
) -> None:
    section_header(
        "Corporate Actions",
        "Share count history, capital returns, and structural events",
    )

    inc = income_df.sort_values("fiscal_year") if income_df is not None and not income_df.empty else pd.DataFrame()
    cf = cashflow_df.sort_values("fiscal_year") if cashflow_df is not None and not cashflow_df.empty else pd.DataFrame()

    # ------------------------------------------------------------------ share count
    st.markdown("#### Share Count History")
    st.caption(
        "Derived from weighted average shares in the income statement. "
        "Changes indicate bonus issues, splits, rights issues, ESOPs, or buybacks."
    )
    _render_share_count(inc)

    # ------------------------------------------------------------------ capital returns
    if not cf.empty:
        st.divider()
        _render_capital_returns(cf, inc)

    # ------------------------------------------------------------------ actions register
    st.divider()
    st.markdown("#### Corporate Actions Register")
    st.caption(
        "Screener's Excel export does not include corporate actions. "
        "Enter them manually here — bonus issues, splits, rights issues, major dividends, etc."
    )
    _render_actions_register(company_id, repo)


# ------------------------------------------------------------------
# Share count
# ------------------------------------------------------------------

def _render_share_count(inc: pd.DataFrame) -> None:
    if inc.empty:
        st.info("No income data available.")
        return

    analysis = analyze_share_count(inc)

    if not analysis.series or all(v is None for _, v in analysis.series):
        st.info("Share count (weighted average shares) not available in the imported data.")
        return

    for note in analysis.notes:
        st.warning(note)

    col1, col2 = st.columns(2)
    valid_shares = [(yr, s) for yr, s in analysis.series if s is not None]
    if valid_shares:
        latest_fy, latest_shares = valid_shares[-1]
        col1.metric(
            f"Latest Shares (FY{latest_fy})",
            f"{latest_shares:,.2f} Cr" if latest_shares >= 1 else f"{latest_shares * 100:.2f} L",
        )
    if is_valid(analysis.total_change_pct):
        col2.metric(
            "Total Share Count Change",
            f"{analysis.total_change_pct:+.1f}%",
            help="From first to latest fiscal year in the data",
        )

    years = [f"FY{yr}" for yr, _ in analysis.series]
    vals = [v for _, v in analysis.series]
    st.plotly_chart(
        bar_chart(years, vals, "Weighted Avg Shares (Cr)", "Cr", color="neutral"),
        use_container_width=True,
    )


# ------------------------------------------------------------------
# Capital returns: dividends + buybacks
# ------------------------------------------------------------------

def _render_capital_returns(cf: pd.DataFrame, inc: pd.DataFrame) -> None:
    div_hist = analyze_dividend_history(cf, inc)
    bb_hist = analyze_buyback_history(cf)

    has_div = div_hist.has_data
    has_bb = bb_hist.has_data

    if not has_div and not has_bb:
        st.markdown("#### Capital Returns to Shareholders")
        st.info("No dividend or buyback data found in the imported cash flow statement.")
        return

    st.markdown("#### Capital Returns to Shareholders")

    # Summary metrics
    cols = st.columns(4)
    idx = 0

    if has_div and div_hist.series:
        valid_divs = [v for _, v in div_hist.series if v is not None]
        latest_div_fy, latest_div = next(
            ((yr, v) for yr, v in reversed(div_hist.series) if v is not None), (None, None)
        )
        if is_valid(latest_div):
            cols[idx].metric(
                f"Dividends Paid (FY{latest_div_fy})",
                f"₹{latest_div:,.0f} Cr",
            )
            idx += 1
        total_divs = sum(v for v in valid_divs)
        if total_divs > 0:
            cols[min(idx, 3)].metric("Total Dividends (all years)", f"₹{total_divs:,.0f} Cr")
            idx += 1

    if has_bb and bb_hist.total_cr:
        cols[min(idx, 3)].metric("Total Buybacks", f"₹{bb_hist.total_cr:,.0f} Cr")

    # Dividend chart
    if has_div:
        div_years = [f"FY{yr}" for yr, _ in div_hist.series]
        div_vals = [v for _, v in div_hist.series]
        payout_vals = [v for _, v in div_hist.payout_series]

        if has_bb:
            bb_years = [f"FY{yr}" for yr, _ in bb_hist.series]
            bb_vals = [v for _, v in bb_hist.series]

            col_d, col_b = st.columns(2)
            with col_d:
                st.plotly_chart(
                    bar_chart(div_years, div_vals, "Dividends Paid (₹ Cr)", "₹ Cr"),
                    use_container_width=True,
                )
            with col_b:
                st.plotly_chart(
                    bar_chart(bb_years, bb_vals, "Buybacks (₹ Cr)", "₹ Cr", color="positive"),
                    use_container_width=True,
                )
        else:
            st.plotly_chart(
                bar_chart(div_years, div_vals, "Dividends Paid (₹ Cr)", "₹ Cr"),
                use_container_width=True,
            )

        # Payout ratio
        if any(v is not None for v in payout_vals):
            st.markdown("##### Dividend Payout Ratio")
            st.caption("Dividends Paid / PAT × 100")
            st.plotly_chart(
                line_chart(div_years, payout_vals, "Payout Ratio (%)", "%"),
                use_container_width=True,
            )
    elif has_bb:
        bb_years = [f"FY{yr}" for yr, _ in bb_hist.series]
        bb_vals = [v for _, v in bb_hist.series]
        st.plotly_chart(
            bar_chart(bb_years, bb_vals, "Buybacks (₹ Cr)", "₹ Cr", color="positive"),
            use_container_width=True,
        )


# ------------------------------------------------------------------
# Actions register (manual entry)
# ------------------------------------------------------------------

def _render_actions_register(company_id: int, repo) -> None:
    existing_df = repo.get_corporate_actions(company_id)

    # Show existing entries
    if not existing_df.empty:
        st.markdown("**Recorded Actions**")
        display_cols = ["id", "action_date", "action_type", "description", "ratio_or_amount"]
        display_cols = [c for c in display_cols if c in existing_df.columns]
        display = existing_df[display_cols].copy()
        display["action_date"] = display["action_date"].astype(str)
        st.dataframe(display, use_container_width=True, hide_index=True)

        # Delete section
        with st.expander("Delete an entry"):
            action_ids = existing_df["id"].tolist()
            labels = [
                f"ID {row['id']} — {row['action_date']} | {row['action_type']}"
                for _, row in existing_df.iterrows()
            ]
            id_map = dict(zip(labels, action_ids))
            to_delete = st.selectbox("Select entry to delete", labels, key="ca_delete_select")
            if st.button("Delete", key="ca_delete_btn", type="secondary"):
                repo.delete_corporate_action(id_map[to_delete])
                st.success("Entry deleted.")
                st.rerun()

    st.markdown("**Add a Corporate Action**")
    with st.form("corporate_actions_form"):
        col1, col2 = st.columns(2)
        with col1:
            action_date = st.date_input(
                "Date",
                value=date.today(),
                help="The record / ex-date of the corporate action",
            )
            action_type = st.selectbox("Action Type", _ACTION_TYPES)
        with col2:
            description = st.text_input(
                "Description",
                placeholder="e.g. Bonus issue 1:1, Dividend ₹5/share, Stock split 2:1",
            )
            ratio_or_amount = st.text_input(
                "Ratio / Amount (optional)",
                placeholder="e.g. 1:1  /  ₹5.00  /  2:1",
            )

        submitted = st.form_submit_button("Save Action", type="primary")
        if submitted:
            if not description.strip():
                st.error("Description is required.")
            else:
                repo.upsert_corporate_action(
                    company_id,
                    str(action_date),
                    action_type,
                    description.strip(),
                    ratio_or_amount.strip() or None,
                )
                st.success(f"Saved: {action_type} on {action_date}")
                st.rerun()

    st.caption(
        "**Where to find corporate action data:** "
        "BSE / NSE filings → Corporate Announcements | "
        "Screener.in → company page → 'Corporate Actions' tab | "
        "Annual report → Notes to Accounts"
    )
