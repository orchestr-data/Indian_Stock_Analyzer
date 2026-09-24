"""Tests for cash flow calculations."""

import pytest
from src.calculations.cashflow import (
    free_cash_flow, cfo_pat_ratio, fcf_pat_ratio, fcf_margin, fcf_yield, capex_revenue_pct,
)


class TestFreeCashFlow:
    def test_basic(self):
        r = free_cash_flow(500, 100)
        assert r.value == pytest.approx(400)

    def test_capex_as_negative(self):
        # CapEx often comes as negative from investing section
        r = free_cash_flow(500, -100)
        assert r.value == pytest.approx(400)  # should normalize to 500 - 100

    def test_negative_fcf(self):
        r = free_cash_flow(100, 300)
        assert r.value == pytest.approx(-200)

    def test_zero_capex(self):
        r = free_cash_flow(500, 0)
        assert r.value == pytest.approx(500)

    def test_none_cfo(self):
        r = free_cash_flow(None, 100)
        assert r.value is None

    def test_none_capex(self):
        r = free_cash_flow(500, None)
        assert r.value is None


class TestCfoPat:
    def test_strong_conversion(self):
        r = cfo_pat_ratio(1200, 1000)
        assert r.value == pytest.approx(1.2)

    def test_weak_conversion(self):
        r = cfo_pat_ratio(500, 1000)
        assert r.value == pytest.approx(0.5)
        assert r.note is not None  # should flag < 0.7

    def test_negative_cfo(self):
        r = cfo_pat_ratio(-100, 1000)
        assert r.value is not None
        assert r.value < 0
        assert r.note is not None

    def test_zero_pat(self):
        r = cfo_pat_ratio(500, 0)
        assert r.value is None

    def test_negative_pat(self):
        r = cfo_pat_ratio(500, -200)
        assert r.value is None

    def test_none_cfo(self):
        r = cfo_pat_ratio(None, 1000)
        assert r.value is None

    def test_exactly_one(self):
        r = cfo_pat_ratio(1000, 1000)
        assert r.value == pytest.approx(1.0)


class TestFcfPat:
    def test_positive(self):
        r = fcf_pat_ratio(800, 1000)
        assert r.value == pytest.approx(0.8)

    def test_negative_fcf(self):
        r = fcf_pat_ratio(-200, 1000)
        assert r.value is not None
        assert r.value < 0

    def test_zero_pat(self):
        r = fcf_pat_ratio(800, 0)
        assert r.value is None


class TestFcfMargin:
    def test_basic(self):
        r = fcf_margin(400, 2000)
        assert r.value == pytest.approx(20.0)

    def test_negative_fcf(self):
        r = fcf_margin(-200, 2000)
        assert r.value == pytest.approx(-10.0)

    def test_none_revenue(self):
        r = fcf_margin(400, None)
        assert r.value is None


class TestFcfYield:
    def test_basic(self):
        r = fcf_yield(1000, 20000)
        assert r.value == pytest.approx(5.0)

    def test_none_market_cap(self):
        r = fcf_yield(1000, None)
        assert r.value is None

    def test_negative_fcf(self):
        r = fcf_yield(-500, 20000)
        assert r.value is not None
        assert r.value < 0
