"""Shared helpers for financial calculations — safe arithmetic primitives."""

from __future__ import annotations
from typing import Optional
import math


def is_valid(value: Optional[float]) -> bool:
    """Return True if value is a non-None, non-NaN, finite number."""
    if value is None:
        return False
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return False
    return True


def safe_div(
    numerator: Optional[float],
    denominator: Optional[float],
    *,
    note_on_none: str = "",
) -> tuple[Optional[float], str]:
    """Divide two values, returning (result, note).

    Returns (None, reason) when division cannot be performed:
    - either input is None/NaN/inf
    - denominator is zero
    """
    if not is_valid(numerator):
        return None, "numerator unavailable"
    if not is_valid(denominator):
        return None, "denominator unavailable"
    if denominator == 0:
        return None, "denominator is zero"
    return numerator / denominator, note_on_none  # type: ignore[operator]


def safe_pct(
    numerator: Optional[float],
    denominator: Optional[float],
) -> Optional[float]:
    """Return numerator/denominator * 100, or None."""
    result, _ = safe_div(numerator, denominator)
    if result is None:
        return None
    return result * 100.0


def average(values: list[Optional[float]]) -> Optional[float]:
    """Arithmetic mean of valid values. Returns None if fewer than 2 valid."""
    valid = [v for v in values if is_valid(v)]
    if len(valid) < 2:
        return None
    return sum(valid) / len(valid)  # type: ignore[arg-type]


def median(values: list[Optional[float]]) -> Optional[float]:
    """Median of valid values. Returns None if no valid values."""
    valid = sorted(v for v in values if is_valid(v))  # type: ignore[type-var]
    n = len(valid)
    if n == 0:
        return None
    mid = n // 2
    if n % 2 == 1:
        return valid[mid]
    return (valid[mid - 1] + valid[mid]) / 2.0


def slope_sign(values: list[Optional[float]]) -> Optional[float]:
    """Return the OLS slope of valid (index, value) pairs, or None."""
    pts = [(i, v) for i, v in enumerate(values) if is_valid(v)]
    if len(pts) < 3:
        return None
    n = len(pts)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    den = sum((x - x_mean) ** 2 for x in xs)
    if den == 0:
        return 0.0
    return num / den


def pct_change(old: Optional[float], new: Optional[float]) -> Optional[float]:
    """Return percentage change from old to new."""
    if not is_valid(old) or not is_valid(new):
        return None
    if old == 0:
        return None  # undefined
    return ((new - old) / abs(old)) * 100.0  # type: ignore[operator]


def pp_change(old: Optional[float], new: Optional[float]) -> Optional[float]:
    """Percentage-point change (for margins, ratios already in %)."""
    if not is_valid(old) or not is_valid(new):
        return None
    return new - old  # type: ignore[operator]
