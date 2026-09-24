"""Tests for efficiency / working capital calculations."""

import pytest
from src.calculations.efficiency import (
    receivable_days, inventory_days, payable_days,
    cash_conversion_cycle, asset_turnover, working_capital_days,
)


class TestReceivableDays:
    def test_basic(self):
        r = receivable_days(100, 1000)
        # 100/1000 * 365 = 36.5
        assert r.value == pytest.approx(36.5)

    def test_zero_revenue(self):
        r = receivable_days(100, 0)
        assert r.value is None

    def test_none_receivables(self):
        r = receivable_days(None, 1000)
        assert r.value is None

    def test_large_receivables(self):
        r = receivable_days(500, 1000)
        assert r.value == pytest.approx(182.5)


class TestInventoryDays:
    def test_with_cogs(self):
        r = inventory_days(200, cogs=1000)
        assert r.value == pytest.approx(73.0)

    def test_fallback_to_revenue(self):
        r = inventory_days(200, revenue=1000)
        assert r.value is not None
        assert r.note is not None  # proxy warning

    def test_zero_inventory(self):
        r = inventory_days(0, revenue=1000)
        assert r.value == pytest.approx(0.0)

    def test_none_inventory(self):
        r = inventory_days(None, revenue=1000)
        assert r.value is None

    def test_no_cogs_no_revenue(self):
        r = inventory_days(200)
        assert r.value is None


class TestPayableDays:
    def test_basic(self):
        r = payable_days(150, 1500)
        assert r.value == pytest.approx(36.5)

    def test_zero_expenses(self):
        r = payable_days(150, 0)
        assert r.value is None


class TestCashConversionCycle:
    def test_basic(self):
        r = cash_conversion_cycle(45.0, 30.0, 25.0)
        assert r.value == pytest.approx(50.0)

    def test_negative_ccc(self):
        # Very fast cash cycle (FMCG type)
        r = cash_conversion_cycle(10.0, 15.0, 60.0)
        assert r.value == pytest.approx(-35.0)

    def test_missing_component(self):
        r = cash_conversion_cycle(45.0, None, 25.0)
        assert r.value is None

    def test_all_zero(self):
        r = cash_conversion_cycle(0.0, 0.0, 0.0)
        assert r.value == pytest.approx(0.0)


class TestAssetTurnover:
    def test_basic(self):
        r = asset_turnover(2000, 1000, 900)
        # avg assets = 950
        assert r.value == pytest.approx(2000 / 950, rel=0.01)

    def test_no_prev(self):
        r = asset_turnover(2000, 1000)
        assert r.value == pytest.approx(2.0)

    def test_zero_assets(self):
        r = asset_turnover(2000, 0, 0)
        assert r.value is None

    def test_none_revenue(self):
        r = asset_turnover(None, 1000)
        assert r.value is None
