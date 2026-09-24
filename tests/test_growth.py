"""Tests for growth calculation module."""

import pytest
from src.calculations.growth import cagr, revenue_cagr, pat_cagr, eps_cagr, yoy_growth


class TestCagr:
    def test_basic_cagr(self):
        r = cagr(100, 161.05, 5)
        assert r.value is not None
        assert abs(r.value - 10.0) < 0.01

    def test_zero_growth(self):
        r = cagr(100, 100, 5)
        assert r.value == pytest.approx(0.0, abs=0.01)

    def test_negative_cagr(self):
        # Values must stay positive for CAGR to work
        r = cagr(100, 50, 3)
        assert r.value is not None
        assert r.value < 0  # declining

    def test_initial_zero_returns_none(self):
        r = cagr(0, 100, 3)
        assert r.value is None
        assert "zero" in r.note.lower()

    def test_initial_negative_returns_none(self):
        r = cagr(-50, 100, 3)
        assert r.value is None
        assert "negative" in r.note.lower()

    def test_final_negative_returns_none(self):
        r = cagr(100, -50, 3)
        assert r.value is None

    def test_none_initial_returns_none(self):
        r = cagr(None, 100, 5)
        assert r.value is None

    def test_none_final_returns_none(self):
        r = cagr(100, None, 5)
        assert r.value is None

    def test_years_zero_returns_none(self):
        r = cagr(100, 200, 0)
        assert r.value is None

    def test_one_year(self):
        r = cagr(100, 115, 1)
        assert r.value == pytest.approx(15.0, abs=0.01)

    def test_cagr_unit_is_pct(self):
        r = cagr(100, 200, 5)
        assert r.unit == "%"

    def test_cagr_large_values(self):
        r = cagr(10000, 20000, 5)
        assert r.value is not None
        assert r.value > 0


class TestRevenueCagr:
    def test_sufficient_history(self):
        series = [100, 110, 121, 133.1, 146.41]
        r = revenue_cagr(series, 3)
        assert r.value is not None
        assert abs(r.value - 10.0) < 0.01

    def test_insufficient_history(self):
        series = [100, 110]
        r = revenue_cagr(series, 5)
        assert r.value is None

    def test_with_none_values_sufficient(self):
        series = [None, 100, 110, 121, 133.1, 146.41]
        r = revenue_cagr(series, 3)
        assert r.value is not None

    def test_all_none(self):
        series = [None, None, None, None]
        r = revenue_cagr(series, 3)
        assert r.value is None


class TestPatCagr:
    def test_negative_start(self):
        series = [-50, 10, 20, 30]
        r = pat_cagr(series, 3)
        assert r.value is None

    def test_positive_series(self):
        series = [100, 120, 144, 172.8, 207.36]
        r = pat_cagr(series, 4)
        assert r.value is not None


class TestYoyGrowth:
    def test_positive_growth(self):
        r = yoy_growth(100, 120)
        assert r.value == pytest.approx(20.0)

    def test_negative_growth(self):
        r = yoy_growth(100, 80)
        assert r.value == pytest.approx(-20.0)

    def test_zero_previous(self):
        r = yoy_growth(0, 100)
        assert r.value is None

    def test_none_previous(self):
        r = yoy_growth(None, 100)
        assert r.value is None

    def test_none_current(self):
        r = yoy_growth(100, None)
        assert r.value is None
