"""Reusable Streamlit UI components."""

from __future__ import annotations
from typing import Optional

import streamlit as st

from src.ui.charts import format_inr


def metric_card(
    label: str,
    value: Optional[float],
    unit: str = "",
    formula: Optional[str] = None,
    definition: Optional[str] = None,
    inputs: Optional[dict] = None,
    note: Optional[str] = None,
    delta: Optional[float] = None,
    delta_label: str = "vs prev year",
) -> None:
    """Render a metric card with optional expandable definition."""
    display = _format_value(value, unit)
    st.metric(label=label, value=display,
              delta=f"{delta:+.1f}{unit}" if delta is not None else None,
              delta_color="normal")
    if note:
        st.caption(f"ℹ️ {note}")
    if formula or definition or inputs:
        with st.expander(f"About {label}"):
            if formula:
                st.markdown(f"**Formula:** `{formula}`")
            if inputs:
                st.markdown("**Input values:**")
                for k, v in inputs.items():
                    fmt_v = _format_value(v, "₹ Cr") if isinstance(v, (int, float)) else str(v)
                    st.markdown(f"- {k}: {fmt_v}")
            if definition:
                st.markdown(f"**Definition:** {definition}")


def _format_value(value: Optional[float], unit: str) -> str:
    if value is None:
        return "N/A"
    if unit == "%":
        return f"{value:.1f}%"
    if unit == "x":
        return f"{value:.1f}x"
    if unit in ("₹ Cr", "Cr"):
        return format_inr(value)
    if unit == "days":
        return f"{value:.0f} days"
    if unit == "₹":
        return f"₹{value:.2f}"
    return f"{value:.2f}"


def section_header(title: str, subtitle: str = "") -> None:
    """Render a section header."""
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)
    st.divider()


_VALID_STATEMENT_TYPES = {"Consolidated", "Standalone"}

def statement_type_badge(statement_type: str) -> None:
    """Render statement type indicator."""
    if statement_type not in _VALID_STATEMENT_TYPES:
        statement_type = "Unknown"
    color = "#1f77b4" if statement_type == "Consolidated" else "#ff7f0e"
    st.markdown(
        f'<span style="background:{color};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.85em;">{statement_type}</span>',
        unsafe_allow_html=True,
    )


def not_available(message: str = "Not available") -> None:
    st.caption(f"*{message}*")


def data_warning(message: str) -> None:
    st.warning(f"⚠️ {message}")


def cagr_table(label: str, c3: Optional[float], c5: Optional[float], c10: Optional[float]) -> None:
    """Render a 3/5/10Y CAGR summary."""
    def _fmt(v: Optional[float]) -> str:
        return f"{v:.1f}%" if v is not None else "N/A"

    cols = st.columns(3)
    cols[0].metric("3Y CAGR", _fmt(c3))
    cols[1].metric("5Y CAGR", _fmt(c5))
    cols[2].metric("10Y CAGR", _fmt(c10))
