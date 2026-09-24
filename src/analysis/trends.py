"""Trend analysis engine — historical metrics over time.

Computes CAGR, averages, medians, trend direction, and volatility.
All calculations use pure helper functions and return TrendResult objects.
"""

from __future__ import annotations
import logging
from typing import Optional

import numpy as np
import pandas as pd

from src.calculations.growth import cagr
from src.calculations.helpers import average, median, slope_sign, is_valid
from src.models.metrics import TrendResult, TrendPoint

logger = logging.getLogger(__name__)


def _direction(values: list[Optional[float]]) -> str:
    """Classify trend direction from a time-ordered list of values."""
    valid = [v for v in values if is_valid(v)]
    if len(valid) < 3:
        return "insufficient_history"

    slope = slope_sign(values)
    if slope is None:
        return "insufficient_history"

    # Count consecutive direction
    changes = [valid[i + 1] - valid[i] for i in range(len(valid) - 1)]
    positives = sum(1 for c in changes if c > 0)
    negatives = sum(1 for c in changes if c < 0)
    total = len(changes)

    pos_ratio = positives / total
    neg_ratio = negatives / total

    if pos_ratio >= 0.75 and slope > 0:
        return "improving"
    if neg_ratio >= 0.75 and slope < 0:
        return "declining"
    if pos_ratio >= 0.6:
        return "improving"
    if neg_ratio >= 0.6:
        return "declining"
    if abs(slope) < 0.001 * (abs(sum(v for v in valid if v)) / len(valid) + 1e-9):
        return "stable"
    return "mixed"


def _consecutive(values: list[Optional[float]]) -> tuple[int, int]:
    """Return (consecutive_increases, consecutive_decreases) from the most recent end."""
    valid_indexed = [(i, v) for i, v in enumerate(values) if is_valid(v)]
    if len(valid_indexed) < 2:
        return 0, 0

    # Work from the end
    inc = 0
    dec = 0
    for j in range(len(valid_indexed) - 1, 0, -1):
        prev_v = valid_indexed[j - 1][1]
        curr_v = valid_indexed[j][1]
        if curr_v > prev_v:  # type: ignore[operator]
            if dec == 0:
                inc += 1
            else:
                break
        elif curr_v < prev_v:  # type: ignore[operator]
            if inc == 0:
                dec += 1
            else:
                break
        else:
            break
    return inc, dec


def _volatility(values: list[Optional[float]]) -> Optional[float]:
    """Coefficient of variation of valid values (std/mean × 100)."""
    valid = [v for v in values if is_valid(v)]
    if len(valid) < 3:
        return None
    arr = np.array(valid, dtype=float)
    mean = float(arr.mean())
    if abs(mean) < 1e-9:
        return None
    return float(arr.std() / abs(mean) * 100.0)


class TrendAnalyzer:
    """Analyzes time-series financial data for a single metric."""

    def analyze(
        self,
        metric_name: str,
        values: list[Optional[float]],
        labels: list[str],
        fiscal_years: list[int],
    ) -> TrendResult:
        """Compute full trend analysis for a named metric series.

        Args:
            metric_name: Human label for the metric.
            values:      Time-ordered list of values (oldest first).
            labels:      Period labels matching values (e.g., "FY2021").
            fiscal_years: Numeric fiscal years matching values.
        """
        n = len(values)
        data_points = [
            TrendPoint(
                period_label=labels[i] if i < len(labels) else str(i),
                fiscal_year=fiscal_years[i] if i < len(fiscal_years) else 0,
                value=values[i],
            )
            for i in range(n)
        ]

        valid_vals = [v for v in values if is_valid(v)]
        latest = valid_vals[-1] if valid_vals else None
        previous = valid_vals[-2] if len(valid_vals) >= 2 else None

        # CAGRs
        c3 = cagr(*self._cagr_args(valid_vals, 3))
        c5 = cagr(*self._cagr_args(valid_vals, 5))
        c10 = cagr(*self._cagr_args(valid_vals, 10))

        # Averages
        avg3 = average(valid_vals[-3:]) if len(valid_vals) >= 3 else None
        avg5 = average(valid_vals[-5:]) if len(valid_vals) >= 5 else None
        avg10 = average(valid_vals[-10:]) if len(valid_vals) >= 10 else None

        # Medians
        med3 = median(valid_vals[-3:]) if len(valid_vals) >= 3 else None
        med5 = median(valid_vals[-5:]) if len(valid_vals) >= 5 else None
        med10 = median(valid_vals[-10:]) if len(valid_vals) >= 10 else None

        # Changes
        abs_change = (latest - previous) if (latest is not None and previous is not None) else None
        pct_change: Optional[float] = None
        if abs_change is not None and previous != 0 and previous is not None:
            pct_change = (abs_change / abs(previous)) * 100.0

        inc, dec = _consecutive(values)
        vol = _volatility(values)
        direction = _direction(values)

        return TrendResult(
            metric_name=metric_name,
            data_points=data_points,
            direction=direction,
            cagr_3y=c3.value,
            cagr_5y=c5.value,
            cagr_10y=c10.value,
            avg_3y=avg3,
            avg_5y=avg5,
            avg_10y=avg10,
            median_3y=med3,
            median_5y=med5,
            median_10y=med10,
            latest=latest,
            previous=previous,
            abs_change=abs_change,
            pct_change=pct_change,
            consecutive_increases=inc,
            consecutive_decreases=dec,
            volatility=vol,
        )

    @staticmethod
    def _cagr_args(
        valid_vals: list[float],
        years: int,
    ) -> tuple[Optional[float], Optional[float], int]:
        if len(valid_vals) >= years + 1:
            return valid_vals[-(years + 1)], valid_vals[-1], years
        return None, None, years

    def from_dataframe(
        self,
        df: pd.DataFrame,
        metric_col: str,
        year_col: str = "fiscal_year",
        metric_name: Optional[str] = None,
    ) -> TrendResult:
        """Build TrendResult from a DataFrame column."""
        df = df.sort_values(year_col).reset_index(drop=True)
        values = [float(v) if pd.notna(v) else None for v in df[metric_col]]
        years = [int(y) for y in df[year_col]]
        labels = [f"FY{y}" for y in years]
        return self.analyze(metric_name or metric_col, values, labels, years)
