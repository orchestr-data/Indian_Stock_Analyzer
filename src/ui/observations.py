"""Observations page — structured factual findings."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.analysis.observations import ObservationEngine
from src.models.observations import Observation, ObservationCategory, ObservationSeverity
from src.ui.components import section_header

_SEVERITY_EMOJI = {
    ObservationSeverity.INFO: "ℹ️",
    ObservationSeverity.LOW: "🔵",
    ObservationSeverity.MEDIUM: "🟡",
    ObservationSeverity.HIGH: "🔴",
}

_CATEGORY_COLOR = {
    ObservationCategory.POSITIVE: "success",
    ObservationCategory.NEUTRAL: "info",
    ObservationCategory.WARNING: "warning",
    ObservationCategory.INVESTIGATE: "warning",
    ObservationCategory.DATA_QUALITY: "error",
}


def render(
    income_df: pd.DataFrame,
    balance_df: pd.DataFrame,
    cashflow_df: pd.DataFrame,
    shareholding_df: pd.DataFrame,
    market_data: dict | None,
    sector: str,
) -> None:
    section_header(
        "Observations",
        "Factual observations only — no buy/sell verdicts, no scores.",
    )

    st.info(
        "These observations are generated from the imported financial data. "
        "They highlight trends and changes that warrant investigation. "
        "They are NOT investment recommendations."
    )

    engine = ObservationEngine(sector=sector)

    safe_inc = income_df if income_df is not None else pd.DataFrame()
    safe_bal = balance_df if balance_df is not None else pd.DataFrame()
    safe_cf = cashflow_df if cashflow_df is not None else pd.DataFrame()
    safe_sh = shareholding_df if shareholding_df is not None else pd.DataFrame()

    if safe_inc.empty:
        st.info("No financial data available to generate observations.")
        return

    observations = engine.generate_all(safe_inc, safe_bal, safe_cf, safe_sh, market_data)

    if not observations:
        st.success("No observations generated — insufficient data or no material changes detected.")
        return

    # Group by category
    positives = [o for o in observations if o.category == ObservationCategory.POSITIVE]
    neutral = [o for o in observations if o.category == ObservationCategory.NEUTRAL]
    warnings = [o for o in observations if o.category == ObservationCategory.WARNING]
    investigate = [o for o in observations if o.category == ObservationCategory.INVESTIGATE]
    data_quality = [o for o in observations if o.category == ObservationCategory.DATA_QUALITY]

    if positives:
        st.markdown("### Positive Observations")
        for obs in positives:
            _render_observation(obs)

    if neutral:
        st.markdown("### Context / Neutral")
        for obs in neutral:
            _render_observation(obs)

    if warnings:
        st.markdown("### Warnings / Material Changes")
        for obs in warnings:
            _render_observation(obs)

    if investigate:
        st.markdown("### Questions to Investigate")
        for obs in investigate:
            _render_observation(obs)

    if data_quality:
        st.markdown("### Data Quality Notes")
        for obs in data_quality:
            _render_observation(obs)

    st.divider()
    st.caption(
        f"Generated {len(observations)} observation(s) from imported data. "
        "Run fresh analysis after importing updated data."
    )


def _render_observation(obs: Observation) -> None:
    emoji = _SEVERITY_EMOJI.get(obs.severity, "•")
    label = f"{obs.metric.replace('_', ' ').title()}"
    period_str = f" | {obs.period}" if obs.period else ""

    short_msg = obs.message[:80] + "..." if len(obs.message) > 80 else obs.message
    with st.expander(f"{emoji} {label}{period_str}  —  {short_msg}"):
        st.markdown(f"**{obs.message}**")

        if obs.starting_value is not None or obs.ending_value is not None:
            change_str = obs.value_change_display
            if change_str:
                st.markdown(f"**Change:** {change_str}")

        if obs.reason:
            st.markdown(f"**Why flagged:** {obs.reason}")

        if obs.suggested_investigation:
            st.markdown(f"**Investigate:** {obs.suggested_investigation}")
