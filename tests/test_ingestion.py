"""Tests for normalizer and ingestion helpers."""

import pytest
from src.ingestion.normalizer import (
    normalize_income_label, normalize_balance_label, normalize_cashflow_label,
    normalize_shareholding_label, clean_numeric,
)


class TestNormalizeIncomeLabel:
    def test_sales_maps_to_revenue(self):
        assert normalize_income_label("Sales") == "revenue"

    def test_revenue_maps_to_revenue(self):
        assert normalize_income_label("Revenue") == "revenue"

    def test_net_profit_maps_to_pat(self):
        assert normalize_income_label("Net Profit") == "pat"

    def test_pat_maps_to_pat(self):
        assert normalize_income_label("PAT") == "pat"

    def test_interest_maps(self):
        assert normalize_income_label("Finance Costs") == "interest"
        assert normalize_income_label("Interest") == "interest"

    def test_eps_maps(self):
        assert normalize_income_label("EPS in Rs") == "basic_eps"

    def test_unknown_returns_none(self):
        assert normalize_income_label("Some Random Field XYZ") is None

    def test_case_insensitive(self):
        assert normalize_income_label("SALES") == "revenue"
        assert normalize_income_label("sales") == "revenue"

    def test_leading_trailing_spaces(self):
        assert normalize_income_label("  Sales  ") == "revenue"


class TestNormalizeBalanceLabel:
    def test_share_capital(self):
        assert normalize_balance_label("Share Capital") == "equity_capital"

    def test_reserves(self):
        assert normalize_balance_label("Reserves & Surplus") == "reserves"

    def test_borrowings(self):
        assert normalize_balance_label("Borrowings") == "borrowings"

    def test_cash(self):
        assert normalize_balance_label("Cash & Equivalents") == "cash_and_equivalents"

    def test_debtors(self):
        assert normalize_balance_label("Debtors") == "receivables"


class TestNormalizeCashflow:
    def test_cfo(self):
        assert normalize_cashflow_label("Cash from Operating Activity") == "operating_cash_flow"

    def test_capex(self):
        assert normalize_cashflow_label("Capital Expenditure") == "capital_expenditure"


class TestNormalizeShareholding:
    def test_promoters(self):
        assert normalize_shareholding_label("Promoters") == "promoter_pct"

    def test_fii(self):
        assert normalize_shareholding_label("FIIs") == "fii_pct"


class TestCleanNumeric:
    def test_plain_number(self):
        assert clean_numeric("1234.56") == pytest.approx(1234.56)

    def test_comma_separated(self):
        assert clean_numeric("1,234.56") == pytest.approx(1234.56)

    def test_blank_returns_none(self):
        assert clean_numeric("") is None
        assert clean_numeric("--") is None
        assert clean_numeric("N/A") is None

    def test_none_returns_none(self):
        assert clean_numeric(None) is None

    def test_parentheses_negative(self):
        assert clean_numeric("(500)") == pytest.approx(-500)

    def test_percentage_stripped(self):
        assert clean_numeric("25.4%") == pytest.approx(25.4)

    def test_rupee_stripped(self):
        assert clean_numeric("₹1,234") == pytest.approx(1234)

    def test_cr_suffix_stripped(self):
        assert clean_numeric("1234 Cr") == pytest.approx(1234)

    def test_integer(self):
        assert clean_numeric(1234) == pytest.approx(1234)

    def test_float(self):
        assert clean_numeric(12.5) == pytest.approx(12.5)

    def test_footnote_marker(self):
        assert clean_numeric("1234.5*") == pytest.approx(1234.5)
