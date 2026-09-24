"""Tests for corporate actions analysis — share count, dividends, buybacks."""

import pytest
import pandas as pd

from src.analysis.corporate_actions import (
    analyze_share_count,
    analyze_dividend_history,
    analyze_buyback_history,
    ShareCountAnalysis,
    DividendHistory,
    BuybackHistory,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _income_df(fys, pats, shares=None):
    data = {"fiscal_year": fys, "pat": pats}
    if shares is not None:
        data["weighted_avg_shares"] = shares
    return pd.DataFrame(data)


def _cashflow_df(fys, dividends=None, buybacks=None):
    data = {"fiscal_year": fys}
    if dividends is not None:
        data["dividends_paid"] = dividends
    if buybacks is not None:
        data["buybacks"] = buybacks
    return pd.DataFrame(data)


# ===========================================================================
# analyze_share_count
# ===========================================================================

class TestAnalyzeShareCount:
    def test_empty_df_returns_empty(self):
        r = analyze_share_count(pd.DataFrame())
        assert r.series == []
        assert r.total_change_pct is None
        assert r.notes == []

    def test_no_shares_column(self):
        df = _income_df([2022, 2023], [100.0, 120.0])
        r = analyze_share_count(df)
        assert r.series == []

    def test_single_year_no_change(self):
        df = _income_df([2024], [100.0], shares=[50.0])
        r = analyze_share_count(df)
        assert len(r.series) == 1
        assert r.series[0] == (2024, 50.0)
        assert r.total_change_pct is None  # need ≥ 2

    def test_stable_shares_no_note(self):
        df = _income_df([2022, 2023, 2024], [100.0, 110.0, 120.0], shares=[50.0, 51.0, 50.5])
        r = analyze_share_count(df)
        assert r.total_change_pct is not None
        assert abs(r.total_change_pct) <= 10
        assert r.notes == []

    def test_dilution_note_above_10pct(self):
        # 50 → 65: +30% dilution
        df = _income_df([2022, 2024], [100.0, 120.0], shares=[50.0, 65.0])
        r = analyze_share_count(df)
        assert r.total_change_pct == pytest.approx(30.0)
        assert len(r.notes) == 1
        assert "dilutive" in r.notes[0].lower() or "increased" in r.notes[0].lower()

    def test_buyback_note_below_minus_5pct(self):
        # 50 → 44: -12% buyback
        df = _income_df([2022, 2024], [100.0, 120.0], shares=[50.0, 44.0])
        r = analyze_share_count(df)
        assert r.total_change_pct == pytest.approx(-12.0)
        assert len(r.notes) == 1
        assert "buyback" in r.notes[0].lower()

    def test_none_shares_handled(self):
        df = _income_df([2022, 2023, 2024], [100.0, 110.0, 120.0], shares=[None, 50.0, 55.0])
        r = analyze_share_count(df)
        assert r.series[0] == (2022, None)
        assert r.series[1] == (2023, 50.0)
        assert r.series[2] == (2024, 55.0)

    def test_series_sorted_by_fy(self):
        # Pass in reverse order
        df = pd.DataFrame({
            "fiscal_year": [2024, 2022, 2023],
            "pat": [120.0, 100.0, 110.0],
            "weighted_avg_shares": [55.0, 50.0, 52.0],
        })
        r = analyze_share_count(df)
        years = [yr for yr, _ in r.series]
        assert years == sorted(years)

    def test_exactly_10pct_no_note(self):
        # exactly 10% increase should NOT trigger dilution note (threshold is >10)
        df = _income_df([2022, 2023], [100.0, 110.0], shares=[50.0, 55.0])
        r = analyze_share_count(df)
        assert r.total_change_pct == pytest.approx(10.0)
        assert r.notes == []

    def test_exactly_minus_5pct_no_note(self):
        # exactly -5% should NOT trigger buyback note (threshold is <-5)
        df = _income_df([2022, 2023], [100.0, 110.0], shares=[50.0, 47.5])
        r = analyze_share_count(df)
        assert r.total_change_pct == pytest.approx(-5.0)
        assert r.notes == []


# ===========================================================================
# analyze_dividend_history
# ===========================================================================

class TestAnalyzeDividendHistory:
    def test_empty_cashflow_returns_no_data(self):
        r = analyze_dividend_history(pd.DataFrame(), pd.DataFrame())
        assert not r.has_data
        assert r.series == []

    def test_no_dividends_column(self):
        cf = _cashflow_df([2022, 2023])
        r = analyze_dividend_history(cf, pd.DataFrame())
        assert not r.has_data

    def test_basic_series(self):
        cf = _cashflow_df([2022, 2023, 2024], dividends=[-50.0, -60.0, -70.0])
        r = analyze_dividend_history(cf, pd.DataFrame())
        assert r.has_data
        assert len(r.series) == 3
        # Stored as absolute value
        assert r.series[0] == (2022, pytest.approx(50.0))
        assert r.series[1] == (2023, pytest.approx(60.0))
        assert r.series[2] == (2024, pytest.approx(70.0))

    def test_positive_dividend_values_also_abs(self):
        # Some importers store as positive
        cf = _cashflow_df([2022, 2023], dividends=[50.0, 60.0])
        r = analyze_dividend_history(cf, pd.DataFrame())
        assert r.series[0][1] == pytest.approx(50.0)
        assert r.series[1][1] == pytest.approx(60.0)

    def test_payout_ratio_computed(self):
        cf = _cashflow_df([2022, 2023], dividends=[-30.0, -40.0])
        inc = _income_df([2022, 2023], pats=[100.0, 200.0])
        r = analyze_dividend_history(cf, inc)
        # payout: 30/100=30%, 40/200=20%
        assert r.payout_series[0] == (2022, pytest.approx(30.0))
        assert r.payout_series[1] == (2023, pytest.approx(20.0))

    def test_payout_none_when_no_income_match(self):
        cf = _cashflow_df([2022, 2023], dividends=[-30.0, -40.0])
        # income only has 2022
        inc = _income_df([2022], pats=[100.0])
        r = analyze_dividend_history(cf, inc)
        assert r.payout_series[0][1] == pytest.approx(30.0)
        assert r.payout_series[1][1] is None  # 2023 not in income

    def test_payout_none_when_pat_zero(self):
        cf = _cashflow_df([2022], dividends=[-30.0])
        inc = _income_df([2022], pats=[0.0])
        r = analyze_dividend_history(cf, inc)
        assert r.payout_series[0][1] is None

    def test_payout_none_when_pat_negative(self):
        cf = _cashflow_df([2022], dividends=[-30.0])
        inc = _income_df([2022], pats=[-50.0])
        r = analyze_dividend_history(cf, inc)
        assert r.payout_series[0][1] is None

    def test_none_dividend_values(self):
        cf = _cashflow_df([2022, 2023, 2024], dividends=[None, -40.0, None])
        r = analyze_dividend_history(cf, pd.DataFrame())
        assert r.has_data  # 2023 has data
        assert r.series[0] == (2022, None)
        assert r.series[1] == (2023, pytest.approx(40.0))
        assert r.series[2] == (2024, None)

    def test_all_none_dividends_no_data(self):
        cf = _cashflow_df([2022, 2023], dividends=[None, None])
        r = analyze_dividend_history(cf, pd.DataFrame())
        assert not r.has_data


# ===========================================================================
# analyze_buyback_history
# ===========================================================================

class TestAnalyzeBuybackHistory:
    def test_empty_cashflow_returns_no_data(self):
        r = analyze_buyback_history(pd.DataFrame())
        assert not r.has_data
        assert r.series == []
        assert r.total_cr is None

    def test_no_buybacks_column(self):
        cf = _cashflow_df([2022, 2023])
        r = analyze_buyback_history(cf)
        assert not r.has_data

    def test_basic_series(self):
        cf = _cashflow_df([2022, 2023, 2024], buybacks=[-100.0, -150.0, -200.0])
        r = analyze_buyback_history(cf)
        assert r.has_data
        assert len(r.series) == 3
        assert r.series[0] == (2022, pytest.approx(100.0))
        assert r.series[1] == (2023, pytest.approx(150.0))
        assert r.series[2] == (2024, pytest.approx(200.0))

    def test_total_cr_sum(self):
        cf = _cashflow_df([2022, 2023, 2024], buybacks=[-100.0, -150.0, -200.0])
        r = analyze_buyback_history(cf)
        assert r.total_cr == pytest.approx(450.0)

    def test_positive_values_abs(self):
        cf = _cashflow_df([2022, 2023], buybacks=[100.0, 200.0])
        r = analyze_buyback_history(cf)
        assert r.series[0][1] == pytest.approx(100.0)
        assert r.total_cr == pytest.approx(300.0)

    def test_none_values_excluded_from_total(self):
        cf = _cashflow_df([2022, 2023, 2024], buybacks=[None, -200.0, None])
        r = analyze_buyback_history(cf)
        assert r.has_data
        assert r.total_cr == pytest.approx(200.0)

    def test_all_none_no_data(self):
        cf = _cashflow_df([2022, 2023], buybacks=[None, None])
        r = analyze_buyback_history(cf)
        assert not r.has_data
        assert r.total_cr is None

    def test_series_sorted_by_fy(self):
        df = pd.DataFrame({
            "fiscal_year": [2024, 2022, 2023],
            "buybacks": [-200.0, -100.0, -150.0],
        })
        r = analyze_buyback_history(df)
        years = [yr for yr, _ in r.series]
        assert years == sorted(years)

    def test_total_none_when_all_zero(self):
        cf = _cashflow_df([2022, 2023], buybacks=[0.0, 0.0])
        r = analyze_buyback_history(cf)
        # zero buybacks: abs(0) = 0, total = 0, result.total_cr should be None
        assert r.total_cr is None
