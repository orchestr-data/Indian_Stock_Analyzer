"""Tests for leverage calculations."""

import pytest
from src.calculations.leverage import (
    debt_equity, net_debt, net_debt_ebitda, interest_coverage, debt_to_assets,
)


class TestDebtEquity:
    def test_basic(self):
        r = debt_equity(500, 1000)
        assert r.value == pytest.approx(0.5)

    def test_zero_debt(self):
        r = debt_equity(0, 1000)
        assert r.value == pytest.approx(0.0)

    def test_zero_equity(self):
        r = debt_equity(500, 0)
        assert r.value is None

    def test_negative_equity(self):
        r = debt_equity(500, -200)
        assert r.value is None
        assert r.note is not None

    def test_none_debt(self):
        r = debt_equity(None, 1000)
        assert r.value is None

    def test_high_de(self):
        r = debt_equity(5000, 1000)
        assert r.value == pytest.approx(5.0)


class TestNetDebt:
    def test_positive_net_debt(self):
        r = net_debt(1000, 200)
        assert r.value == pytest.approx(800)

    def test_net_cash_position(self):
        r = net_debt(200, 1000)
        assert r.value == pytest.approx(-800)
        assert "net cash" in r.note.lower()

    def test_none_cash_treated_as_zero(self):
        r = net_debt(1000, None)
        assert r.value == pytest.approx(1000)

    def test_zero_debt(self):
        r = net_debt(0, 500)
        assert r.value == pytest.approx(-500)

    def test_none_debt_returns_none(self):
        r = net_debt(None, 500)
        assert r.value is None


class TestNetDebtEbitda:
    def test_basic(self):
        r = net_debt_ebitda(1000, 200, 500)
        # net debt = 800, ebitda = 500
        assert r.value == pytest.approx(1.6)

    def test_negative_ebitda(self):
        r = net_debt_ebitda(1000, 200, -500)
        assert r.value is None

    def test_zero_ebitda(self):
        r = net_debt_ebitda(1000, 200, 0)
        assert r.value is None

    def test_net_cash_company(self):
        r = net_debt_ebitda(200, 1000, 500)
        # net debt = -800
        assert r.value is not None
        assert r.value < 0


class TestInterestCoverage:
    def test_basic(self):
        r = interest_coverage(500, 100)
        assert r.value == pytest.approx(5.0)

    def test_below_one(self):
        r = interest_coverage(80, 100)
        assert r.value == pytest.approx(0.8)
        assert "below 1" in r.note.lower()

    def test_zero_interest(self):
        r = interest_coverage(500, 0)
        assert r.value is None

    def test_negative_ebit(self):
        r = interest_coverage(-100, 50)
        assert r.value is not None
        assert r.value < 0
        assert "negative" in r.note.lower()

    def test_none_ebit(self):
        r = interest_coverage(None, 50)
        assert r.value is None

    def test_very_high_coverage(self):
        r = interest_coverage(10000, 10)
        assert r.value == pytest.approx(1000.0)
