"""Tests for valuation analysis — historical context and synthetic multiples."""

import pytest
import pandas as pd
from src.analysis.valuation_analysis import (
    analyze_pe_history,
    analyze_pb_history,
    compute_synthetic_multiples,
    ValuationHistory,
    SyntheticMultiples,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _market_df(dates, pe_vals, pb_vals=None):
    """Build a minimal market_data DataFrame."""
    data = {"date": dates, "pe": pe_vals}
    if pb_vals is not None:
        data["pb"] = pb_vals
    return pd.DataFrame(data)


def _income_df(fys, pats):
    return pd.DataFrame({"fiscal_year": fys, "pat": pats})


def _balance_df(fys, equities):
    return pd.DataFrame({"fiscal_year": fys, "shareholders_equity": equities})


# ===========================================================================
# analyze_pe_history
# ===========================================================================

class TestAnalyzePeHistory:
    def test_empty_df(self):
        r = analyze_pe_history(pd.DataFrame())
        assert r.current is None
        assert r.series == []

    def test_no_pe_column(self):
        r = analyze_pe_history(pd.DataFrame({"date": ["2024-01-01"], "pb": [2.0]}))
        assert r.current is None

    def test_single_point(self):
        df = _market_df(["2024-03-31"], [20.0])
        r = analyze_pe_history(df)
        assert r.current == pytest.approx(20.0)
        assert r.median_3y is None  # need ≥ 3
        assert len(r.series) == 1

    def test_three_points_gives_median_3y(self):
        df = _market_df(["2022-03-31", "2023-03-31", "2024-03-31"], [15.0, 20.0, 25.0])
        r = analyze_pe_history(df)
        assert r.current == pytest.approx(25.0)
        assert r.median_3y == pytest.approx(20.0)  # median of [15, 20, 25]

    def test_five_points_gives_median_5y(self):
        df = _market_df(
            ["2020-03-31", "2021-03-31", "2022-03-31", "2023-03-31", "2024-03-31"],
            [10.0, 15.0, 20.0, 25.0, 30.0],
        )
        r = analyze_pe_history(df)
        assert r.median_5y == pytest.approx(20.0)
        assert r.current == pytest.approx(30.0)

    def test_premium_to_5y_median(self):
        df = _market_df(
            ["2020-03-31", "2021-03-31", "2022-03-31", "2023-03-31", "2024-03-31"],
            [10.0, 10.0, 10.0, 10.0, 15.0],
        )
        r = analyze_pe_history(df)
        # current=15, med5=10 → premium = (15-10)/10 * 100 = 50%
        assert r.premium_to_5y_median_pct == pytest.approx(50.0)

    def test_discount_to_5y_median(self):
        df = _market_df(
            ["2020-03-31", "2021-03-31", "2022-03-31", "2023-03-31", "2024-03-31"],
            [20.0, 20.0, 20.0, 20.0, 10.0],
        )
        r = analyze_pe_history(df)
        assert r.premium_to_5y_median_pct == pytest.approx(-50.0)

    def test_none_values_skipped(self):
        df = _market_df(["2022-03-31", "2023-03-31", "2024-03-31"], [None, 20.0, 25.0])
        r = analyze_pe_history(df)
        # Only 2 valid points after dropping None
        assert r.current == pytest.approx(25.0)

    def test_label(self):
        df = _market_df(["2024-03-31"], [18.0])
        r = analyze_pe_history(df)
        assert r.metric_name == "P/E"


# ===========================================================================
# analyze_pb_history
# ===========================================================================

class TestAnalyzePbHistory:
    def test_empty_df(self):
        r = analyze_pb_history(pd.DataFrame())
        assert r.current is None

    def test_no_pb_column(self):
        r = analyze_pb_history(pd.DataFrame({"date": ["2024-01-01"], "pe": [20.0]}))
        assert r.current is None

    def test_single_point(self):
        df = _market_df(["2024-03-31"], [20.0], pb_vals=[3.0])
        r = analyze_pb_history(df)
        assert r.current == pytest.approx(3.0)

    def test_three_points_median(self):
        df = _market_df(
            ["2022-03-31", "2023-03-31", "2024-03-31"],
            [15.0, 18.0, 22.0],
            pb_vals=[2.0, 3.0, 4.0],
        )
        r = analyze_pb_history(df)
        assert r.median_3y == pytest.approx(3.0)
        assert r.current == pytest.approx(4.0)

    def test_premium_computed(self):
        df = _market_df(
            ["2020-03-31", "2021-03-31", "2022-03-31", "2023-03-31", "2024-03-31"],
            [15.0] * 5,
            pb_vals=[2.0, 2.0, 2.0, 2.0, 3.0],
        )
        r = analyze_pb_history(df)
        assert r.premium_to_5y_median_pct == pytest.approx(50.0)

    def test_label(self):
        df = _market_df(["2024-03-31"], [20.0], pb_vals=[2.5])
        r = analyze_pb_history(df)
        assert r.metric_name == "P/B"


# ===========================================================================
# compute_synthetic_multiples
# ===========================================================================

class TestComputeSyntheticMultiples:
    def test_no_market_cap(self):
        inc = _income_df([2022, 2023, 2024], [100.0, 120.0, 140.0])
        r = compute_synthetic_multiples(inc, None, None)
        assert r.mc_over_pat == []
        assert r.market_cap is None

    def test_empty_income(self):
        r = compute_synthetic_multiples(pd.DataFrame(), None, 10000.0)
        assert r.mc_over_pat == []

    def test_basic_mc_over_pat(self):
        inc = _income_df([2022, 2023, 2024], [100.0, 200.0, 500.0])
        r = compute_synthetic_multiples(inc, None, 10000.0)
        assert len(r.mc_over_pat) == 3
        assert r.mc_over_pat[0] == (2022, pytest.approx(100.0))  # 10000 / 100
        assert r.mc_over_pat[1] == (2023, pytest.approx(50.0))   # 10000 / 200
        assert r.mc_over_pat[2] == (2024, pytest.approx(20.0))   # 10000 / 500

    def test_zero_pat_returns_none(self):
        inc = _income_df([2022, 2023], [0.0, 100.0])
        r = compute_synthetic_multiples(inc, None, 10000.0)
        assert r.mc_over_pat[0] == (2022, None)
        assert r.mc_over_pat[1] == (2023, pytest.approx(100.0))

    def test_negative_pat_returns_none(self):
        inc = _income_df([2022, 2023], [-50.0, 100.0])
        r = compute_synthetic_multiples(inc, None, 10000.0)
        assert r.mc_over_pat[0] == (2022, None)

    def test_mc_over_equity(self):
        inc = _income_df([2022, 2023], [100.0, 120.0])
        bal = _balance_df([2022, 2023], [2000.0, 2500.0])
        r = compute_synthetic_multiples(inc, bal, 10000.0)
        assert len(r.mc_over_equity) == 2
        assert r.mc_over_equity[0] == (2022, pytest.approx(5.0))   # 10000 / 2000
        assert r.mc_over_equity[1] == (2023, pytest.approx(4.0))   # 10000 / 2500

    def test_median_3y_pat(self):
        # MC/PAT values: 100, 50, 25 for last 3 years
        inc = _income_df([2022, 2023, 2024], [100.0, 200.0, 400.0])
        r = compute_synthetic_multiples(inc, None, 10000.0)
        # mc_over_pat = [(2022, 100), (2023, 50), (2024, 25)]
        # median of last 3 = median(100, 50, 25) = 50
        assert r.median_mc_over_pat_3y == pytest.approx(50.0)

    def test_median_5y_pat(self):
        inc = _income_df(
            [2020, 2021, 2022, 2023, 2024],
            [100.0, 200.0, 250.0, 500.0, 1000.0],
        )
        r = compute_synthetic_multiples(inc, None, 10000.0)
        # mc_over_pat = [100, 50, 40, 20, 10]
        # median of 5 = 40
        assert r.median_mc_over_pat_5y == pytest.approx(40.0)

    def test_no_median_if_fewer_than_3(self):
        inc = _income_df([2022, 2023], [100.0, 200.0])
        r = compute_synthetic_multiples(inc, None, 10000.0)
        assert r.median_mc_over_pat_3y is None
        assert r.median_mc_over_pat_5y is None

    def test_market_cap_stored(self):
        inc = _income_df([2024], [100.0])
        r = compute_synthetic_multiples(inc, None, 50000.0)
        assert r.market_cap == pytest.approx(50000.0)

    def test_no_balance_df_mc_over_equity_empty(self):
        inc = _income_df([2022, 2023], [100.0, 120.0])
        r = compute_synthetic_multiples(inc, None, 10000.0)
        assert r.mc_over_equity == []
        assert r.median_mc_over_equity_3y is None
        assert r.median_mc_over_equity_5y is None
