"""Growth rate calculations — CAGR and period-over-period changes.

CAGR = (Final / Initial) ^ (1 / Years) - 1

Important edge-cases handled:
- Initial value is zero: CAGR undefined, returns None with explanation
- Initial value is negative: CAGR undefined, returns None with explanation
- Final value is negative: returns the negative CAGR but flags it
- Insufficient history: returns None with explanation
- Periods are not annual: caller must ensure correct period type
"""

from __future__ import annotations
from typing import Optional
import math

from src.calculations.helpers import is_valid, pct_change
from src.models.metrics import MetricResult


def cagr(
    initial: Optional[float],
    final: Optional[float],
    years: int,
) -> MetricResult:
    """Compute Compound Annual Growth Rate.

    Args:
        initial: Value at the start of the period (must be positive).
        final:   Value at the end of the period.
        years:   Number of years between initial and final.

    Returns:
        MetricResult with value in % (e.g. 12.5 means 12.5%).
    """
    label = f"{years}Y CAGR"
    formula = "( Final / Initial ) ^ ( 1 / Years ) − 1"

    if years < 1:
        return MetricResult(
            value=None, label=label, unit="%", formula=formula,
            note="Years must be at least 1",
        )
    if not is_valid(initial):
        return MetricResult(
            value=None, label=label, unit="%", formula=formula,
            note="Initial value unavailable",
        )
    if not is_valid(final):
        return MetricResult(
            value=None, label=label, unit="%", formula=formula,
            note="Final value unavailable",
        )
    if initial == 0:
        return MetricResult(
            value=None, label=label, unit="%", formula=formula,
            note="CAGR undefined: initial value is zero",
            inputs={"initial": initial, "final": final, "years": years},
        )
    if initial < 0:
        return MetricResult(
            value=None, label=label, unit="%", formula=formula,
            note="CAGR undefined: initial value is negative — values crossed zero",
            inputs={"initial": initial, "final": final, "years": years},
        )

    ratio = final / initial  # type: ignore[operator]
    if ratio < 0:
        return MetricResult(
            value=None, label=label, unit="%", formula=formula,
            note="CAGR undefined: final value is negative while initial is positive",
            inputs={"initial": initial, "final": final, "years": years},
        )

    result_pct = (ratio ** (1.0 / years) - 1.0) * 100.0
    return MetricResult(
        value=round(result_pct, 2),
        label=label,
        unit="%",
        formula=formula,
        inputs={"initial": initial, "final": final, "years": years},
    )


def _cagr_from_series(
    series: list[Optional[float]],
    years: int,
    label: str,
    fiscal_years: Optional[list[int]] = None,
) -> MetricResult:
    """Compute CAGR using actual fiscal year span when available.

    When `fiscal_years` is supplied, the function finds the valid data point
    closest to `years` years before the latest point and uses the real year
    gap as the exponent.  This avoids overstating CAGR when years are missing
    from the series (e.g. FY2019 absent makes a nominal "3Y" span actually 4Y).
    """
    if fiscal_years is not None:
        pairs = [(fy, v) for fy, v in zip(fiscal_years, series) if is_valid(v)]
        if len(pairs) < 2:
            return MetricResult(value=None, label=label, unit="%",
                note=f"{label} unavailable: insufficient valid data")
        last_fy, final = pairs[-1]
        target_fy = last_fy - years
        earlier = [(fy, v) for fy, v in pairs[:-1] if fy <= target_fy]
        if not earlier:
            return MetricResult(value=None, label=label, unit="%",
                note=f"{label} unavailable: no data {years}+ years back (earliest: FY{pairs[0][0]})")
        first_fy, initial = max(earlier, key=lambda x: x[0])
        actual_years = last_fy - first_fy
        result = cagr(initial, final, actual_years)
        if result.value is not None and actual_years != years:
            result.note = f"Computed over {actual_years} years (FY{first_fy}–FY{last_fy}); FY{target_fy} data unavailable"
        return result

    # Legacy path — no fiscal year info, use count of valid values
    valid = [v for v in series if is_valid(v)]
    if len(valid) < years + 1:
        return MetricResult(
            value=None, label=label, unit="%",
            note=f"{label} unavailable: only {len(valid)} year(s) of valid data",
        )
    initial = valid[-(years + 1)]
    final = valid[-1]
    return cagr(initial, final, years)


def revenue_cagr(
    revenue_series: list[Optional[float]],
    years: int,
    fiscal_years: Optional[list[int]] = None,
) -> MetricResult:
    """Revenue CAGR over `years` using the most recent data points."""
    r = _cagr_from_series(revenue_series, years, f"Revenue {years}Y CAGR", fiscal_years)
    r.formula = "( Revenue_Final / Revenue_Initial ) ^ ( 1 / Years ) − 1"
    return r


def pat_cagr(
    pat_series: list[Optional[float]],
    years: int,
    fiscal_years: Optional[list[int]] = None,
) -> MetricResult:
    """PAT CAGR over `years`."""
    return _cagr_from_series(pat_series, years, f"PAT {years}Y CAGR", fiscal_years)


def eps_cagr(
    eps_series: list[Optional[float]],
    years: int,
    fiscal_years: Optional[list[int]] = None,
) -> MetricResult:
    """EPS CAGR over `years`."""
    return _cagr_from_series(eps_series, years, f"EPS {years}Y CAGR", fiscal_years)


def ebitda_cagr(
    ebitda_series: list[Optional[float]],
    years: int,
    fiscal_years: Optional[list[int]] = None,
) -> MetricResult:
    return _cagr_from_series(ebitda_series, years, f"EBITDA {years}Y CAGR", fiscal_years)


def fcf_cagr(
    fcf_series: list[Optional[float]],
    years: int,
    fiscal_years: Optional[list[int]] = None,
) -> MetricResult:
    return _cagr_from_series(fcf_series, years, f"FCF {years}Y CAGR", fiscal_years)


def book_value_cagr(
    bvps_series: list[Optional[float]],
    years: int,
    fiscal_years: Optional[list[int]] = None,
) -> MetricResult:
    return _cagr_from_series(bvps_series, years, f"Book Value {years}Y CAGR", fiscal_years)


def yoy_growth(previous: Optional[float], current: Optional[float], label: str = "YoY") -> MetricResult:
    """Year-over-year percentage change."""
    chg = pct_change(previous, current)
    return MetricResult(
        value=chg,
        label=label,
        unit="%",
        formula="( Current − Previous ) / |Previous| × 100",
        inputs={"previous": previous, "current": current},
        note=None if chg is not None else "Unavailable — previous value is zero or missing",
    )


def share_count_growth(
    shares_series: list[Optional[float]],
    years: int,
    fiscal_years: Optional[list[int]] = None,
) -> MetricResult:
    """Share count CAGR — used to identify dilution trends."""
    return _cagr_from_series(shares_series, years, f"Share Count {years}Y CAGR", fiscal_years)
