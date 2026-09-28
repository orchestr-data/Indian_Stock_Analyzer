"""Sector-specific analysis page — Banking, NBFC, and Insurance KPIs."""

from __future__ import annotations
from collections import OrderedDict
from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

from src.calculations import roa
from src.ui.charts import line_chart
from src.ui.components import section_header
from src.ui.constants import FINANCIAL_SECTORS as _FINANCIAL_SECTORS
_BANKING_LIKE = frozenset({"BANKING", "NBFC"})

# metric_key -> (display_label, unit, help_text)
_BANKING_METRICS: OrderedDict = OrderedDict([
    ("nim_pct",               ("NIM (%)",              "%", "Net Interest Margin — NII / Avg Interest-Earning Assets × 100")),
    ("gnpa_pct",              ("GNPA (%)",             "%", "Gross NPA ratio — Gross NPA / Gross Advances × 100")),
    ("nnpa_pct",              ("NNPA (%)",             "%", "Net NPA ratio — Net NPA / Net Advances × 100")),
    ("pcr_pct",               ("PCR (%)",              "%", "Provision Coverage Ratio — Provisions / Gross NPA × 100")),
    ("casa_ratio_pct",        ("CASA Ratio (%)",       "%", "CASA deposits / Total deposits × 100")),
    ("capital_adequacy_pct",  ("CAR / CRAR (%)",       "%", "Capital Adequacy Ratio — (Tier 1 + Tier 2) / Risk-Weighted Assets × 100")),
    ("credit_cost_pct",       ("Credit Cost (%)",      "%", "Provisions for the year / Average advances × 100")),
    ("loan_growth_pct",       ("Loan Book Growth (%)", "%", "YoY growth in gross advances / loan book")),
    ("deposit_growth_pct",    ("Deposit Growth (%)",   "%", "YoY growth in total deposits")),
    ("yield_on_advances_pct", ("Yield on Advances (%)","%", "Interest income on loans / Avg advances × 100")),
    ("cost_of_deposits_pct",  ("Cost of Deposits (%)", "%", "Interest expense on deposits / Avg deposits × 100")),
    ("slippage_ratio_pct",    ("Slippage Ratio (%)",   "%", "Fresh NPAs in period / Opening standard assets × 100")),
])

_NBFC_METRICS: OrderedDict = OrderedDict([
    ("nim_pct",                ("NIM / Spread (%)",      "%", "Net Interest Margin or Spread (Yield on Advances − Cost of Borrowings)")),
    ("gnpa_pct",               ("GNPA (%)",              "%", "Gross NPA ratio")),
    ("nnpa_pct",               ("NNPA (%)",              "%", "Net NPA ratio")),
    ("pcr_pct",                ("PCR (%)",               "%", "Provision Coverage Ratio")),
    ("capital_adequacy_pct",   ("CAR (%)",               "%", "Capital Adequacy Ratio")),
    ("aum_growth_pct",         ("AUM Growth (%)",        "%", "Assets Under Management YoY growth")),
    ("yield_on_advances_pct",  ("Yield on Advances (%)", "%", "Yield on the loan portfolio")),
    ("cost_of_borrowings_pct", ("Cost of Borrowings (%)","%", "Weighted average cost of borrowings")),
    ("credit_cost_pct",        ("Credit Cost (%)",       "%", "Provisions / Average AUM × 100")),
    ("slippage_ratio_pct",     ("Slippage Ratio (%)",    "%", "Fresh NPAs / Opening standard assets × 100")),
])

_INSURANCE_METRICS: OrderedDict = OrderedDict([
    ("vnb_margin_pct",      ("VNB Margin (%)",     "%", "Value of New Business / APE × 100")),
    ("ev_growth_pct",       ("EV Growth (%)",      "%", "Embedded Value YoY growth")),
    ("ape_growth_pct",      ("APE Growth (%)",     "%", "Annualized Premium Equivalent YoY growth")),
    ("persistency_13m_pct", ("Persistency 13M (%)","%", "13-month policy persistency rate")),
    ("persistency_61m_pct", ("Persistency 61M (%)","%", "61-month policy persistency rate")),
    ("solvency_ratio_pct",  ("Solvency Ratio (%)", "%", "Available Solvency Margin / Required Solvency Margin × 100 (IRDAI min: 150%)")),
    ("combined_ratio_pct",  ("Combined Ratio (%)", "%", "Claims Ratio + Expense Ratio (general insurance; below 100% = underwriting profit)")),
    ("claims_ratio_pct",    ("Claims Ratio (%)",   "%", "Net claims incurred / Net premiums earned × 100")),
    ("expense_ratio_pct",   ("Expense Ratio (%)",  "%", "Operating expenses / Net premiums earned × 100")),
])

_SECTOR_DISPLAY = {"BANKING": "Banking", "NBFC": "NBFC", "INSURANCE": "Insurance"}


def render(
    company: dict,
    income_df: pd.DataFrame,
    balance_df: pd.DataFrame,
    sector: str,
    repo,
) -> None:
    """Render the sector-specific analysis page."""
    if sector not in _FINANCIAL_SECTORS:
        section_header("Sector Analysis", f"Sector: {sector}")
        st.info(
            "This page shows sector-specific KPIs for Banking, NBFC, and Insurance companies. "
            f"The selected company's sector is **{sector}** — standard metrics apply. "
            "Use Profitability, Balance Sheet, and Efficiency pages for analysis."
        )
        return

    company_id: Optional[int] = company.get("company_id") if company else None
    sector_label = _SECTOR_DISPLAY.get(sector, sector)

    section_header(
        "Sector Analysis",
        f"{sector_label} — sector-specific KPIs (not available in standard Screener export)",
    )

    if income_df is None or income_df.empty:
        st.info("No financial data imported yet. Import a Screener Excel file first.")
        return

    income_df = income_df.sort_values("fiscal_year").reset_index(drop=True)

    # ------------------------------------------------------------------ computed metrics
    st.markdown("#### Derived from Standard Financial Data")
    st.caption("Computed automatically from the imported income statement and balance sheet.")
    _render_computable_metrics(income_df, balance_df, sector)

    st.divider()

    # ------------------------------------------------------------------ manual entry
    st.markdown("#### Sector-Specific KPIs — Manual Entry")
    st.caption(
        "These metrics require data from annual reports, investor presentations, or "
        "exchange filings (BSE / NSE). Enter them here to track trends over time."
    )

    if company_id is None:
        st.warning("Company ID not found — cannot save sector metrics.")
        return

    _render_manual_entry(company_id, income_df, sector, repo)

    # ------------------------------------------------------------------ historical trends
    st.divider()
    sector_df = repo.get_sector_metrics(company_id)
    if not sector_df.empty:
        st.markdown("#### Historical Trends")
        _render_sector_trends(sector_df, sector)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _render_computable_metrics(
    income_df: pd.DataFrame, balance_df: Optional[pd.DataFrame], sector: str
) -> None:
    """Show ROA and approximate cost-to-income derived from standard Screener data."""
    if balance_df is not None and not balance_df.empty:
        balance_df = balance_df.sort_values("fiscal_year").reset_index(drop=True)
    else:
        balance_df = None

    years_label = [f"FY{y}" for y in income_df["fiscal_year"]]
    roa_vals: list = []
    ci_vals: list = []

    for i, row in income_df.iterrows():
        pat = row.get("pat")
        assets = prev_assets = None
        if balance_df is not None:
            bl = balance_df[balance_df["fiscal_year"] == row["fiscal_year"]]
            if not bl.empty:
                assets = bl.iloc[0].get("total_assets")
            if i > 0:
                prev_bl = balance_df[balance_df["fiscal_year"] == income_df.iloc[i - 1]["fiscal_year"]]
                if not prev_bl.empty:
                    prev_assets = prev_bl.iloc[0].get("total_assets")

        roa_vals.append(roa(pat, assets, prev_assets).value)

        rev = row.get("revenue")
        exp = row.get("expenses")
        if rev and exp and rev > 0:
            ci_vals.append(round(exp / rev * 100, 1))
        else:
            ci_vals.append(None)

    latest_roa = roa_vals[-1] if roa_vals else None
    latest_ci = ci_vals[-1] if ci_vals else None
    valid_roa = [v for v in roa_vals[-3:] if v is not None]
    avg3_roa = round(sum(valid_roa) / len(valid_roa), 2) if valid_roa else None

    col1, col2, col3 = st.columns(3)
    col1.metric("ROA (Latest)", f"{latest_roa:.2f}%" if latest_roa is not None else "N/A")
    col3.metric("ROA 3Y Avg", f"{avg3_roa:.2f}%" if avg3_roa is not None else "N/A")
    col2.metric(
        "Cost-to-Income (approx)",
        f"{latest_ci:.1f}%" if latest_ci is not None else "N/A",
        help="Expenses / Revenue — this is an approximation; may differ from the reported C/I ratio",
    )

    if any(v is not None for v in roa_vals):
        st.plotly_chart(
            line_chart(years_label, roa_vals, "ROA (%)", "%"),
            use_container_width=True,
        )
    else:
        st.caption("Balance sheet data not available — ROA cannot be computed.")


def _get_metrics_def(sector: str) -> OrderedDict:
    if sector == "BANKING":
        return _BANKING_METRICS
    elif sector == "NBFC":
        return _NBFC_METRICS
    return _INSURANCE_METRICS


def _render_manual_entry(
    company_id: int, income_df: pd.DataFrame, sector: str, repo
) -> None:
    """Render manual KPI entry form with existing values pre-filled."""
    metrics_def = _get_metrics_def(sector)

    # Build FY list: income years + current/next FY
    available_fys = sorted(income_df["fiscal_year"].tolist(), reverse=True)
    today = date.today()
    fy_current = today.year if today.month >= 4 else today.year - 1
    for fy in [fy_current + 1, fy_current]:
        if fy not in available_fys:
            available_fys.insert(0, fy)

    selected_fy = st.selectbox(
        "Select Fiscal Year",
        available_fys,
        help="Indian fiscal year ending March 31 — FY2026 covers April 2025 to March 2026",
        key="sector_fy_select",
    )

    period_date = f"{selected_fy}-03-31"

    # Fetch existing values for this FY
    existing_df = repo.get_sector_metrics(company_id)
    existing: dict = {}
    if not existing_df.empty:
        existing_df["period_end_date"] = existing_df["period_end_date"].astype(str)
        fy_rows = existing_df[existing_df["period_end_date"] == period_date]
        for _, row in fy_rows.iterrows():
            existing[row["metric_name"]] = row["metric_value"]

    st.markdown(f"**Entering / updating metrics for FY{selected_fy}** (period: {period_date})")
    st.caption("Leave at 0.00 to skip saving that metric. Non-zero values will be saved.")

    with st.form(f"sector_metrics_form_{company_id}_{selected_fy}"):
        cols = st.columns(2)
        values: dict = {}
        for idx, (key, (label, unit, help_text)) in enumerate(metrics_def.items()):
            with cols[idx % 2]:
                default = float(existing.get(key) or 0.0)
                val = st.number_input(
                    label,
                    min_value=0.0,
                    max_value=100000.0,
                    value=default,
                    step=0.01,
                    format="%.2f",
                    help=help_text,
                    key=f"sector_input_{key}_{selected_fy}",
                )
                values[key] = val

        col_save, col_delete = st.columns([3, 1])
        with col_save:
            submitted = st.form_submit_button("Save Metrics", type="primary")
        with col_delete:
            delete_btn = st.form_submit_button(
                "Clear FY Data", help=f"Delete all saved metrics for FY{selected_fy}"
            )

        if submitted:
            saved = 0
            for key, val in values.items():
                if val > 0:
                    label_str, unit_str, _ = metrics_def[key]
                    repo.upsert_sector_metric(
                        company_id, period_date, key, val, unit_str, "manual"
                    )
                    saved += 1
            st.success(f"Saved {saved} metrics for FY{selected_fy}.")
            st.rerun()

        if delete_btn:
            deleted = repo.delete_sector_metrics_for_period(company_id, period_date)
            st.warning(f"Cleared {deleted} metric(s) for FY{selected_fy}.")
            st.rerun()

    # Show historical table
    all_metrics = repo.get_sector_metrics(company_id)
    if not all_metrics.empty:
        all_metrics["period_end_date"] = all_metrics["period_end_date"].astype(str)
        label_map = {k: v[0] for k, v in metrics_def.items()}
        all_metrics["Metric"] = all_metrics["metric_name"].map(label_map).fillna(all_metrics["metric_name"])

        pivot = all_metrics.pivot_table(
            index="Metric",
            columns="period_end_date",
            values="metric_value",
            aggfunc="first",
        )
        if not pivot.empty:
            pivot.columns = [f"FY{c[:4]}" for c in sorted(pivot.columns, reverse=True)]
            st.markdown("**All Entered Data**")
            st.dataframe(pivot.round(2), use_container_width=True)


def _render_sector_trends(sector_df: pd.DataFrame, sector: str) -> None:
    """Render trend charts for all entered sector metrics that have ≥2 data points."""
    metrics_def = _get_metrics_def(sector)

    sector_df = sector_df.copy()
    sector_df["period_end_date"] = sector_df["period_end_date"].astype(str)
    sector_df = sector_df.sort_values("period_end_date")

    dates = sorted(sector_df["period_end_date"].unique())
    if len(dates) < 2:
        st.caption("Enter data for at least 2 fiscal years to see trend charts.")
        return

    labels = [f"FY{d[:4]}" for d in dates]

    # Collect metrics that have data
    chart_items = []
    for key, (label, unit, _) in metrics_def.items():
        metric_rows = sector_df[sector_df["metric_name"] == key]
        if metric_rows.empty:
            continue
        vals = []
        for d in dates:
            row = metric_rows[metric_rows["period_end_date"] == d]
            vals.append(float(row.iloc[0]["metric_value"]) if not row.empty else None)
        if sum(1 for v in vals if v is not None) >= 2:
            chart_items.append((label, unit, vals))

    if not chart_items:
        st.caption("Not enough data points for trend charts — enter metrics for 2+ fiscal years.")
        return

    # Render 2 charts per row
    for i in range(0, len(chart_items), 2):
        pair = chart_items[i : i + 2]
        cols = st.columns(len(pair))
        for col, (label, unit, vals) in zip(cols, pair):
            with col:
                col.plotly_chart(
                    line_chart(labels, vals, f"{label}", unit),
                    use_container_width=True,
                )
