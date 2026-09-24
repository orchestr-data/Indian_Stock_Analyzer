"""Tests for observation engine."""

import pytest
import pandas as pd
from src.analysis.observations import ObservationEngine
from src.models.observations import ObservationCategory, ObservationSeverity


def _make_income(data: dict) -> pd.DataFrame:
    return pd.DataFrame(data)


def _make_cashflow(data: dict) -> pd.DataFrame:
    return pd.DataFrame(data)


class TestRevenueObservations:
    def test_consecutive_growth_observed(self):
        income = _make_income({
            "fiscal_year": [2019, 2020, 2021, 2022, 2023],
            "revenue": [100, 110, 120, 130, 140],
            "pat": [10, 11, 12, 13, 14],
        })
        engine = ObservationEngine()
        obs = engine._revenue_trend(income)
        assert any("grown" in o.message.lower() for o in obs)

    def test_revenue_decline_flagged(self):
        income = _make_income({
            "fiscal_year": [2022, 2023, 2024],
            "revenue": [100, 110, 90],
            "pat": [10, 11, 9],
        })
        engine = ObservationEngine()
        obs = engine._revenue_trend(income)
        assert any("declined" in o.message.lower() for o in obs)
        assert any(o.category == ObservationCategory.WARNING for o in obs)

    def test_insufficient_data_no_obs(self):
        income = _make_income({
            "fiscal_year": [2023, 2024],
            "revenue": [100, 110],
        })
        engine = ObservationEngine()
        obs = engine._revenue_trend(income)
        assert len(obs) == 0


class TestCashConversionObservations:
    def test_consecutive_low_cfo_pat_flagged(self):
        income = _make_income({
            "fiscal_year": [2020, 2021, 2022, 2023],
            "pat": [100, 110, 120, 130],
        })
        cashflow = _make_cashflow({
            "fiscal_year": [2020, 2021, 2022, 2023],
            "operating_cash_flow": [50, 55, 60, 65],  # all below 0.7 of PAT
        })
        engine = ObservationEngine()
        obs = engine._cash_conversion(income, cashflow)
        assert len(obs) > 0

    def test_strong_conversion_noted(self):
        income = _make_income({
            "fiscal_year": [2023],
            "pat": [100],
        })
        cashflow = _make_cashflow({
            "fiscal_year": [2023],
            "operating_cash_flow": [120],
        })
        engine = ObservationEngine()
        obs = engine._cash_conversion(income, cashflow)
        assert any(o.category == ObservationCategory.POSITIVE for o in obs)

    def test_no_pat_data_no_obs(self):
        income = pd.DataFrame()
        cashflow = pd.DataFrame()
        engine = ObservationEngine()
        obs = engine._cash_conversion(income, cashflow)
        assert len(obs) == 0


class TestPromoterObservations:
    def test_pledge_flagged(self):
        sh = pd.DataFrame({
            "period_end_date": ["2024-03-31"],
            "promoter_pct": [51.0],
            "promoter_pledge_pct": [8.5],
            "fii_pct": [20.0],
            "dii_pct": [10.0],
        })
        engine = ObservationEngine()
        obs = engine._promoter_observations(sh)
        assert any("pledged" in o.message.lower() for o in obs)
        assert any(o.category == ObservationCategory.INVESTIGATE for o in obs)

    def test_no_pledge_no_warning(self):
        sh = pd.DataFrame({
            "period_end_date": ["2024-03-31"],
            "promoter_pct": [55.0],
            "promoter_pledge_pct": [0.0],
        })
        engine = ObservationEngine()
        obs = engine._promoter_observations(sh)
        pledge_obs = [o for o in obs if "pledge" in o.message.lower()]
        assert len(pledge_obs) == 0


class TestShareDilution:
    def test_dilution_flagged(self):
        income = _make_income({
            "fiscal_year": [2019, 2020, 2021, 2022, 2023, 2024],
            "weighted_avg_shares": [100, 100, 105, 110, 115, 122],
        })
        engine = ObservationEngine()
        obs = engine._share_dilution(income)
        # 22% increase → should flag
        assert len(obs) > 0
        assert any("increased" in o.message.lower() for o in obs)

    def test_no_dilution_no_obs(self):
        income = _make_income({
            "fiscal_year": [2019, 2020, 2021],
            "weighted_avg_shares": [100, 100, 101],  # less than 10% threshold
        })
        engine = ObservationEngine()
        obs = engine._share_dilution(income)
        assert len(obs) == 0
