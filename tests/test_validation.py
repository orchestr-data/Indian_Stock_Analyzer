"""Tests for data validation."""

import pytest
from src.ingestion.screener_excel import ParsedWorkbook, ParsedSheet, ParsedPeriod
from src.ingestion.validator import Validator
from datetime import date


def _make_sheet(rows: dict, periods: list = None) -> ParsedSheet:
    if periods is None:
        periods = [
            ParsedPeriod("Mar 2025", 2025, period_end_date=date(2025, 3, 31)),
            ParsedPeriod("Mar 2024", 2024, period_end_date=date(2024, 3, 31)),
        ]
    return ParsedSheet(
        sheet_name="Test",
        statement_type="Consolidated",
        periods=periods,
        rows=rows,
    )


def _make_workbook(**kwargs) -> ParsedWorkbook:
    defaults = dict(
        file_path="test.xlsx",
        file_hash="abc123",
        company_name="Test Company",
        company_ticker="TEST",
        statement_type="Consolidated",
    )
    defaults.update(kwargs)
    return ParsedWorkbook(**defaults)


class TestValidator:
    def test_valid_workbook_passes(self):
        wb = _make_workbook()
        wb.income_annual = _make_sheet({
            "revenue": [1000.0, 900.0],
            "pat": [100.0, 80.0],
        })
        v = Validator()
        result = v.validate(wb)
        assert not result.has_failures()

    def test_missing_company_name_warns(self):
        wb = _make_workbook(company_name=None)
        v = Validator()
        result = v.validate(wb)
        assert result.status in ("WARNING", "FAILED")

    def test_unknown_statement_type_warns(self):
        wb = _make_workbook(statement_type="Unknown")
        v = Validator()
        result = v.validate(wb)
        assert result.status in ("WARNING", "FAILED")

    def test_shareholding_sums_checked(self):
        sh = _make_sheet({
            "promoter_pct": [50.0],
            "fii_pct": [20.0],
            "dii_pct": [10.0],
            "public_pct": [20.0],
        }, periods=[ParsedPeriod("Dec 2024", 2025, 3, period_end_date=date(2024, 12, 31))])
        wb = _make_workbook()
        wb.shareholding = sh
        v = Validator()
        result = v.validate(wb)
        # 100% sum should pass
        sum_checks = [c for c in result.checks if "shareholding_sums" in c["name"]]
        assert all(c["status"] == "PASS" for c in sum_checks)

    def test_pledge_exceeds_promoter_warns(self):
        sh = _make_sheet({
            "promoter_pct": [50.0],
            "promoter_pledge_pct": [60.0],  # pledge > holding — impossible
        }, periods=[ParsedPeriod("Dec 2024", 2025, 3, period_end_date=date(2024, 12, 31))])
        wb = _make_workbook()
        wb.shareholding = sh
        v = Validator()
        result = v.validate(wb)
        pledge_checks = [c for c in result.checks if "pledge_not_exceed" in c["name"]]
        assert any(c["status"] != "PASS" for c in pledge_checks)
