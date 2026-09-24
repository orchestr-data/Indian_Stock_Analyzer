"""Tests for profitability calculations."""

import pytest
from src.calculations.profitability import (
    operating_margin, ebitda_margin, net_margin, roe, roce, roa,
)


class TestMargins:
    def test_operating_margin_basic(self):
        r = operating_margin(250, 1000)
        assert r.value == pytest.approx(25.0)

    def test_zero_revenue(self):
        r = operating_margin(250, 0)
        assert r.value is None

    def test_none_revenue(self):
        r = operating_margin(250, None)
        assert r.value is None

    def test_none_profit(self):
        r = operating_margin(None, 1000)
        assert r.value is None

    def test_negative_margin(self):
        r = operating_margin(-100, 1000)
        assert r.value == pytest.approx(-10.0)

    def test_ebitda_margin(self):
        r = ebitda_margin(300, 1000)
        assert r.value == pytest.approx(30.0)

    def test_net_margin(self):
        r = net_margin(150, 1000)
        assert r.value == pytest.approx(15.0)


class TestROE:
    def test_basic_roe_with_avg_equity(self):
        r = roe(200, 1000, 900)
        # avg equity = 950
        assert r.value == pytest.approx(200 / 950 * 100, rel=0.01)

    def test_roe_fallback_current_only(self):
        r = roe(200, 1000, None)
        assert r.value == pytest.approx(20.0)
        assert r.note is not None  # warning about using current only

    def test_zero_equity_returns_none(self):
        r = roe(200, 0, None)
        assert r.value is None

    def test_negative_equity_returns_none(self):
        r = roe(200, -500, -400)
        assert r.value is None

    def test_none_pat(self):
        r = roe(None, 1000, None)
        assert r.value is None

    def test_negative_pat(self):
        r = roe(-100, 1000, 900)
        assert r.value is not None
        assert r.value < 0

    def test_large_values(self):
        r = roe(2480, 10000, 9000)
        assert r.value is not None
        assert r.value > 0


class TestROCE:
    def test_basic_roce(self):
        # EBIT=2480, equity=8000, debt=2000, cash=500
        r = roce(2480, 8000, 2000, 500)
        ce = 8000 + 2000 - 500
        expected = 2480 / ce * 100
        assert r.value == pytest.approx(expected, rel=0.01)

    def test_roce_with_avg_ce(self):
        r = roce(2480, 8000, 2000, 500, 7000, 1800, 400)
        ce_curr = 8000 + 2000 - 500
        ce_prev = 7000 + 1800 - 400
        avg_ce = (ce_curr + ce_prev) / 2
        expected = 2480 / avg_ce * 100
        assert r.value == pytest.approx(expected, rel=0.01)

    def test_zero_ce_returns_none(self):
        # Cash > Equity + Debt → negative CE → should return None
        r = roce(2480, 100, 0, 10000)
        assert r.value is None

    def test_none_ebit(self):
        r = roce(None, 8000, 2000, 500)
        assert r.value is None

    def test_no_debt(self):
        r = roce(2480, 8000, 0, 500)
        ce = 8000 - 500
        expected = 2480 / ce * 100
        assert r.value == pytest.approx(expected, rel=0.01)


class TestROA:
    def test_basic_roa(self):
        r = roa(200, 5000, 4800)
        avg = (5000 + 4800) / 2
        assert r.value == pytest.approx(200 / avg * 100, rel=0.01)

    def test_roa_no_prev(self):
        r = roa(200, 5000)
        assert r.value == pytest.approx(200 / 5000 * 100, rel=0.01)

    def test_roa_zero_assets(self):
        r = roa(200, 0)
        assert r.value is None
