"""Reusable Plotly chart components."""

from __future__ import annotations
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

_COLORS = {
    "primary": "#1f77b4",
    "positive": "#2ca02c",
    "warning": "#d62728",
    "neutral": "#ff7f0e",
    "secondary": "#9467bd",
    "grey": "#7f7f7f",
}

_CHART_LAYOUT = dict(
    template="plotly_white",
    height=350,
    margin=dict(l=40, r=20, t=40, b=40),
    font=dict(size=12),
    hovermode="x unified",
)


def bar_chart(
    x: list,
    y: list,
    title: str,
    y_label: str = "",
    color: str = "primary",
    show_values: bool = True,
) -> go.Figure:
    """Simple bar chart."""
    fig = go.Figure(go.Bar(
        x=x, y=y,
        marker_color=_COLORS.get(color, color),
        text=[_fmt(v) for v in y] if show_values else None,
        textposition="outside",
    ))
    fig.update_layout(title=title, yaxis_title=y_label, **_CHART_LAYOUT)
    return fig


def line_chart(
    x: list,
    y: list,
    title: str,
    y_label: str = "",
    color: str = "primary",
    reference_line: Optional[float] = None,
    reference_label: str = "",
) -> go.Figure:
    """Line chart with optional horizontal reference."""
    fig = go.Figure(go.Scatter(
        x=x, y=y,
        mode="lines+markers",
        line=dict(color=_COLORS.get(color, color), width=2),
        marker=dict(size=6),
    ))
    if reference_line is not None:
        fig.add_hline(
            y=reference_line,
            line_dash="dash",
            line_color=_COLORS["grey"],
            annotation_text=reference_label,
        )
    fig.update_layout(title=title, yaxis_title=y_label, **_CHART_LAYOUT)
    return fig


def dual_bar_chart(
    x: list,
    y1: list, y1_label: str,
    y2: list, y2_label: str,
    title: str,
) -> go.Figure:
    """Side-by-side bar chart for two series."""
    fig = go.Figure([
        go.Bar(name=y1_label, x=x, y=y1, marker_color=_COLORS["primary"]),
        go.Bar(name=y2_label, x=x, y=y2, marker_color=_COLORS["positive"]),
    ])
    fig.update_layout(
        title=title, barmode="group",
        legend=dict(orientation="h", y=1.1),
        **_CHART_LAYOUT,
    )
    return fig


def line_with_bar(
    x: list,
    bar_y: list, bar_label: str,
    line_y: list, line_label: str,
    title: str,
    bar_color: str = "primary",
    line_color: str = "warning",
) -> go.Figure:
    """Combined bar (primary axis) and line (secondary axis) chart."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x, y=bar_y, name=bar_label,
        marker_color=_COLORS.get(bar_color, bar_color),
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=line_y, name=line_label,
        mode="lines+markers",
        line=dict(color=_COLORS.get(line_color, line_color), width=2),
        yaxis="y2",
    ))
    fig.update_layout(
        title=title,
        yaxis=dict(title=bar_label),
        yaxis2=dict(title=line_label, overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.1),
        **_CHART_LAYOUT,
    )
    return fig


def area_chart(
    x: list, y: list, title: str, y_label: str = "", color: str = "primary"
) -> go.Figure:
    """Area chart."""
    fig = go.Figure(go.Scatter(
        x=x, y=y, fill="tozeroy",
        line=dict(color=_COLORS.get(color, color)),
        mode="lines",
    ))
    fig.update_layout(title=title, yaxis_title=y_label, **_CHART_LAYOUT)
    return fig


def stacked_area_chart(
    x: list,
    series: dict[str, list],
    title: str,
) -> go.Figure:
    """Stacked area chart for ownership composition."""
    colors = [_COLORS["primary"], _COLORS["positive"], _COLORS["neutral"],
               _COLORS["secondary"], _COLORS["grey"], _COLORS["warning"]]
    fig = go.Figure()
    for i, (name, values) in enumerate(series.items()):
        fig.add_trace(go.Scatter(
            x=x, y=values, name=name,
            mode="lines", stackgroup="one",
            line=dict(color=colors[i % len(colors)]),
        ))
    fig.update_layout(
        title=title, yaxis_title="%",
        legend=dict(orientation="h", y=1.1),
        **_CHART_LAYOUT,
    )
    return fig


def _fmt(v: object) -> str:
    if v is None:
        return ""
    try:
        f = float(v)  # type: ignore[arg-type]
        if abs(f) >= 10000:
            return f"{f/100:.0f}k"
        return f"{f:.1f}"
    except (TypeError, ValueError):
        return str(v)


def format_inr(value: Optional[float], unit: str = "Cr") -> str:
    """Format a value in Indian number system."""
    if value is None:
        return "N/A"
    if unit == "Cr":
        if abs(value) >= 100_000:
            return f"₹{value / 100_000:.2f} Lakh Cr"
        return f"₹{value:,.0f} Cr"
    return f"{value:.2f}"
