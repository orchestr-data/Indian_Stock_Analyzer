"""Profitability analysis page."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.calculations import operating_margin, ebitda_margin, ebit_margin, net_margin, roe, roce, roa
from src.calculations.helpers import is_valid, average
from src.ui.charts import line_chart
from src.ui.components import section_header, not_available

_FINANCIAL_SECTORS = frozenset({"BANKING", "NBFC", "INSURANCE"})


def render(
    income_df: pd.DataFrame,
    balance_df: pd.DataFrame,
    statement_type: str,
    sector: str = "DEFAULT",
) -> None:
    is_financial = sector in _FINANCIAL_SECTORS
    subtitle = "Margins and returns over time"
    if is_financial:
        subtitle = "Margins and returns — ROCE excluded for financial sector (see Sector Analysis page for NIM/NPA)"

    section_header("Profitability", subtitle)

    if income_df is None or income_df.empty:
        st.info("No income data available.")
        return

    income_df = income_df.sort_values("fiscal_year")
    years_label = [f"FY{y}" for y in income_df["fiscal_year"]]

    # Margins
    st.markdown("#### Operating Margins")
    _render_margins(income_df, years_label)

    st.divider()
    if is_financial:
        st.markdown("#### Returns — ROE & ROA")
        st.caption("ROCE is excluded for banking/NBFC/insurance (not a meaningful measure for financial intermediaries).")
        _render_returns_financial(income_df, balance_df, years_label)
    else:
        st.markdown("#### Returns — ROE & ROCE")
        _render_returns(income_df, balance_df, years_label)


def _render_margins(df: pd.DataFrame, years_label: list) -> None:
    om_vals, em_vals, nm_vals = [], [], []
    for _, row in df.iterrows():
        rev = row.get("revenue")
        op = row.get("operating_profit")
        ebitda = row.get("ebitda")
        pat = row.get("pat")
        om_vals.append(operating_margin(op, rev).value)
        em_vals.append(ebitda_margin(ebitda, rev).value)
        nm_vals.append(net_margin(pat, rev).value)

    # Summary table
    latest_om = om_vals[-1] if om_vals else None
    avg3_om = average(om_vals[-3:]) if len(om_vals) >= 3 else None
    avg5_om = average(om_vals[-5:]) if len(om_vals) >= 5 else None

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Operating Margin (Latest)", f"{latest_om:.1f}%" if is_valid(latest_om) else "N/A")
    col2.metric("3Y Average", f"{avg3_om:.1f}%" if is_valid(avg3_om) else "N/A")
    col3.metric("5Y Average", f"{avg5_om:.1f}%" if is_valid(avg5_om) else "N/A")
    latest_nm = nm_vals[-1] if nm_vals else None
    col4.metric("Net Margin (Latest)", f"{latest_nm:.1f}%" if is_valid(latest_nm) else "N/A")

    from src.ui.charts import line_chart
    st.plotly_chart(
        _margin_chart(years_label, om_vals, em_vals, nm_vals),
        use_container_width=True,
    )


def _margin_chart(years, om, em, nm):
    import plotly.graph_objects as go
    fig = go.Figure()
    for vals, label, color in [(om, "Operating Margin", "#1f77b4"),
                                (em, "EBITDA Margin", "#2ca02c"),
                                (nm, "Net Margin", "#ff7f0e")]:
        safe_vals = [v if v is not None else None for v in vals]
        fig.add_trace(go.Scatter(x=years, y=safe_vals, name=label,
                                  mode="lines+markers",
                                  line=dict(color=color, width=2)))
    fig.update_layout(
        title="Margin Trends (%)",
        yaxis_title="%",
        template="plotly_white",
        height=350,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1),
    )
    return fig


def _render_returns_financial(
    income_df: pd.DataFrame, balance_df: pd.DataFrame, years_label: list
) -> None:
    """ROE + ROA for banking/NBFC/insurance — no ROCE."""
    roe_vals = []
    roa_vals = []

    income_df = income_df.sort_values("fiscal_year").reset_index(drop=True)
    if balance_df is not None:
        balance_df = balance_df.sort_values("fiscal_year").reset_index(drop=True)

    for i, row in income_df.iterrows():
        pat = row.get("pat")
        eq = prev_eq = assets = prev_assets = None

        if balance_df is not None and not balance_df.empty:
            bl = balance_df[balance_df["fiscal_year"] == row["fiscal_year"]]
            if not bl.empty:
                bl_row = bl.iloc[0]
                eq = bl_row.get("shareholders_equity")
                assets = bl_row.get("total_assets")
            if i > 0:
                prev_bl = balance_df[balance_df["fiscal_year"] == income_df.iloc[i - 1]["fiscal_year"]]
                if not prev_bl.empty:
                    prev_eq = prev_bl.iloc[0].get("shareholders_equity")
                    prev_assets = prev_bl.iloc[0].get("total_assets")

        mi = row.get("minority_interest")
        roe_vals.append(roe(pat, eq, prev_eq, minority_interest=mi).value)
        roa_vals.append(roa(pat, assets, prev_assets).value)

    col1, col2 = st.columns(2)
    with col1:
        latest_roe = roe_vals[-1] if roe_vals else None
        avg3 = average(roe_vals[-3:]) if len(roe_vals) >= 3 else None
        st.metric("ROE (Latest)", f"{latest_roe:.1f}%" if is_valid(latest_roe) else "N/A")
        st.metric("ROE 3Y Avg", f"{avg3:.1f}%" if is_valid(avg3) else "N/A")
        st.plotly_chart(
            line_chart(years_label, roe_vals, "ROE (%)", "%"),
            use_container_width=True,
        )
    with col2:
        latest_roa = roa_vals[-1] if roa_vals else None
        avg3r = average(roa_vals[-3:]) if len(roa_vals) >= 3 else None
        st.metric("ROA (Latest)", f"{latest_roa:.2f}%" if is_valid(latest_roa) else "N/A")
        st.metric("ROA 3Y Avg", f"{avg3r:.2f}%" if is_valid(avg3r) else "N/A")
        st.plotly_chart(
            line_chart(years_label, roa_vals, "ROA (%)", "%", color="positive"),
            use_container_width=True,
        )


def _render_returns(income_df: pd.DataFrame, balance_df: pd.DataFrame, years_label: list) -> None:
    roe_vals = []
    roce_vals = []

    income_df = income_df.sort_values("fiscal_year").reset_index(drop=True)
    if balance_df is not None:
        balance_df = balance_df.sort_values("fiscal_year").reset_index(drop=True)

    for i, row in income_df.iterrows():
        pat = row.get("pat")
        ebit = row.get("ebit")
        eq, prev_eq, borr, cash = None, None, None, None

        if balance_df is not None and not balance_df.empty:
            bl = balance_df[balance_df["fiscal_year"] == row["fiscal_year"]]
            if not bl.empty:
                bl_row = bl.iloc[0]
                eq = bl_row.get("shareholders_equity")
                borr = bl_row.get("borrowings")
                cash = bl_row.get("cash_and_equivalents")
            if i > 0:
                prev_bl = balance_df[balance_df["fiscal_year"] == income_df.iloc[i - 1]["fiscal_year"]]
                if not prev_bl.empty:
                    prev_eq = prev_bl.iloc[0].get("shareholders_equity")

        mi = row.get("minority_interest")
        roe_vals.append(roe(pat, eq, prev_eq, minority_interest=mi).value)
        roce_vals.append(roce(ebit, eq, borr, cash).value)

    col1, col2 = st.columns(2)
    with col1:
        latest_roe = roe_vals[-1] if roe_vals else None
        avg3 = average(roe_vals[-3:]) if len(roe_vals) >= 3 else None
        st.metric("ROE (Latest)", f"{latest_roe:.1f}%" if is_valid(latest_roe) else "N/A")
        st.metric("ROE 3Y Avg", f"{avg3:.1f}%" if is_valid(avg3) else "N/A")
        st.plotly_chart(
            line_chart(years_label, roe_vals, "ROE (%)", "%"),
            use_container_width=True,
        )
    with col2:
        latest_roce = roce_vals[-1] if roce_vals else None
        avg3r = average(roce_vals[-3:]) if len(roce_vals) >= 3 else None
        st.metric("ROCE (Latest)", f"{latest_roce:.1f}%" if is_valid(latest_roce) else "N/A")
        st.metric("ROCE 3Y Avg", f"{avg3r:.1f}%" if is_valid(avg3r) else "N/A")
        st.plotly_chart(
            line_chart(years_label, roce_vals, "ROCE (%)", "%", color="positive"),
            use_container_width=True,
        )
