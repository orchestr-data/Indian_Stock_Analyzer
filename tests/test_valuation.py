"""Tests for valuation calculations."""

import pytest
from src.calculations.valuation import (
    pe_ratio, pb_ratio, peg_ratio, enterprise_value, ev_ebitda, ev_ebit,
    earnings_yield, book_value_per_share, eps_calc,
)


class TestPeRatio:
    def test_basic(self):
        r = pe_ratio(100, 5)
        assert r.value == pytest.approx(20.0)

    def test_negative_eps(self):
        r = pe_ratio(100, -5)
        assert r.value is None
        assert r.note is not None

    def test_zero_eps(self):
        r = pe_ratio(100, 0)
        assert r.value is None

    def test_none_price(self):
        r = pe_ratio(None, 5)
        assert r.value is None

    def test_high_pe(self):
        r = pe_ratio(100, 0.5)
        assert r.value == pytest.approx(200.0)


class TestPbRatio:
    def test_basic(self):
        r = pb_ratio(50000, 25000)
        assert r.value == pytest.approx(2.0)

    def test_negative_equity(self):
        r = pb_ratio(50000, -10000)
        assert r.value is None

    def test_zero_equity(self):
        r = pb_ratio(50000, 0)
        assert r.value is None


class TestPegRatio:
    def test_basic(self):
        r = peg_ratio(20, 20)
        assert r.value == pytest.approx(1.0)

    def test_zero_growth(self):
        r = peg_ratio(20, 0)
        assert r.value is None

    def test_negative_growth(self):
        r = peg_ratio(20, -10)
        assert r.value is None

    def test_negative_pe(self):
        r = peg_ratio(-5, 20)
        assert r.value is None

    def test_high_growth(self):
        r = peg_ratio(40, 40)
        assert r.value == pytest.approx(1.0)


class TestEnterpriseValue:
    def test_basic(self):
        r = enterprise_value(50000, 5000, 2000)
        assert r.value == pytest.approx(53000)

    def test_net_cash_company(self):
        r = enterprise_value(50000, 0, 5000)
        assert r.value == pytest.approx(45000)

    def test_no_cash(self):
        r = enterprise_value(50000, 5000, None)
        # cash treated as 0
        assert r.value == pytest.approx(55000)

    def test_none_market_cap(self):
        r = enterprise_value(None, 5000, 2000)
        assert r.value is None


class TestEvEbitda:
    def test_basic(self):
        r = ev_ebitda(50000, 5000)
        assert r.value == pytest.approx(10.0)

    def test_negative_ebitda(self):
        r = ev_ebitda(50000, -1000)
        assert r.value is None

    def test_zero_ebitda(self):
        r = ev_ebitda(50000, 0)
        assert r.value is None


class TestEps:
    def test_basic(self):
        r = eps_calc(1000, 500)
        assert r.value == pytest.approx(2.0)

    def test_negative_pat(self):
        r = eps_calc(-500, 500)
        assert r.value is not None
        assert r.value < 0

    def test_zero_shares(self):
        r = eps_calc(1000, 0)
        assert r.value is None

    def test_none_pat(self):
        r = eps_calc(None, 500)
        assert r.value is None


class TestBookValuePerShare:
    def test_basic(self):
        r = book_value_per_share(10000, 500)
        assert r.value == pytest.approx(20.0)

    def test_zero_shares(self):
        r = book_value_per_share(10000, 0)
        assert r.value is None
