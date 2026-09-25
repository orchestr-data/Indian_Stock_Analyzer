"""End-to-end tests for the Screener import: parser → importer → DuckDB."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from src.analysis.valuation_analysis import analyze_pe_history
from src.ingestion.importer import ImportOrchestrator, ticker_from_filename
from src.ingestion.normalizer import clean_numeric
from src.ingestion.screener_excel import ScreenerExcelParser, _parse_period_label
from tests.conftest import REAL_FIXTURES, build_screener_workbook


# ---------------------------------------------------------------------------
# Period parsing
# ---------------------------------------------------------------------------

class TestPeriodParsing:
    @pytest.mark.parametrize("value", [
        datetime(2024, 3, 31), date(2024, 3, 31), "Mar 2024", "Mar-24",
        "Mar-2024", "March 2024", "2024-03-31", "2024-03-31 00:00:00", "2024",
    ])
    def test_formats_resolve_to_fy2024(self, value):
        p = _parse_period_label(value)
        assert p is not None and p.fiscal_year == 2024
        assert p.period_end_date == date(2024, 3, 31)

    def test_annual_period_has_no_quarter(self):
        # Regression: annual March columns used to get quarter=4 and were then
        # skipped by the importer, so no annual data was ever stored.
        assert _parse_period_label(datetime(2024, 3, 31), is_quarterly=False).fiscal_quarter is None

    @pytest.mark.parametrize("month,q,fy", [(6, 1, 2025), (9, 2, 2025), (12, 3, 2025), (3, 4, 2025)])
    def test_quarterly_mapping(self, month, q, fy):
        year = 2025 if month == 3 else 2024
        p = _parse_period_label(datetime(year, month, 28), is_quarterly=True)
        assert (p.fiscal_quarter, p.fiscal_year) == (q, fy)

    def test_ttm(self):
        assert _parse_period_label("TTM").is_ttm


class TestCleanNumeric:
    def test_lakh_crore_scaled(self):
        assert clean_numeric("1.5 Lakh Cr") == pytest.approx(150000.0)

    def test_unicode_minus(self):
        assert clean_numeric("−120") == -120.0

    def test_crore_unchanged(self):
        assert clean_numeric("1,234 Cr") == 1234.0


def test_ticker_from_filename():
    assert ticker_from_filename("TCS__1_.xlsx") == "TCS"
    assert ticker_from_filename("Infosys (2).xlsx") == "INFOSYS"
    assert ticker_from_filename("hdfcbank.xlsx") == "HDFCBANK"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class TestDataSheetParser:
    def test_reads_data_sheet_not_formula_sheets(self, screener_xlsx):
        wb = ScreenerExcelParser().parse(screener_xlsx)
        assert wb.source_layout == "data_sheet"
        assert wb.company_name == "TEST INDUSTRIES LTD"
        assert wb.current_price == 1500.0 and wb.market_cap == 150000.0

    def test_all_sections_and_labels(self, screener_xlsx):
        wb = ScreenerExcelParser().parse(screener_xlsx)
        for sheet in (wb.income_annual, wb.balance_sheet, wb.cash_flow, wb.income_quarterly):
            assert sheet is not None and len(sheet.periods) == 10
            assert sheet.unknown_labels == []

    def test_statement_type_not_guessed(self, screener_xlsx):
        assert ScreenerExcelParser().parse(screener_xlsx).statement_type == "Unknown"

    def test_derived_pl_matches_screener_formulas(self, screener_xlsx):
        rows = ScreenerExcelParser().parse(screener_xlsx).income_annual.rows
        # FY2017: RM 300 + mfr 50 + emp 200 + selling 60 + other 40 − Δinv 10 = 640
        assert rows["expenses"][0] == pytest.approx(640.0)
        assert rows["operating_profit"][0] == pytest.approx(360.0)
        assert rows["ebitda"][0] == rows["operating_profit"][0]
        assert rows["ebit"][0] == pytest.approx(330.0)
        assert rows["basic_eps"][0] == pytest.approx(2.40)

    def test_balance_sheet_ties(self, screener_xlsx):
        rows = ScreenerExcelParser().parse(screener_xlsx).balance_sheet.rows
        for eq, liab, assets in zip(rows["shareholders_equity"], rows["total_liabilities"],
                                    rows["total_assets"]):
            assert eq + liab == pytest.approx(assets)
        assert rows["cash_and_equivalents"][0] == 80.0

    def test_year_end_prices_aligned(self, screener_xlsx):
        wb = ScreenerExcelParser().parse(screener_xlsx)
        assert len(wb.year_end_prices) == len(wb.income_annual.periods)
        assert wb.year_end_prices[0] == 800.0

    def test_capex_absence_is_reported(self, screener_xlsx):
        wb = ScreenerExcelParser().parse(screener_xlsx)
        assert any("capital expenditure" in w for w in wb.warnings)


# ---------------------------------------------------------------------------
# Importer (end to end into DuckDB)
# ---------------------------------------------------------------------------

def _count(db, table):
    return db.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


class TestImporter:
    def test_full_import_stores_every_section(self, db, screener_xlsx):
        r = ImportOrchestrator(db).import_screener_excel(
            screener_xlsx, statement_type="Consolidated", original_filename="TESTCO__1_.xlsx")
        assert r.success, r.errors
        assert r.ticker == "TESTCO"
        assert r.fiscal_years_imported == list(range(2017, 2027))
        assert _count(db, "annual_income") == 10
        assert _count(db, "balance_sheet") == 10
        assert _count(db, "cash_flow") == 10
        assert _count(db, "quarterly_income") == 10
        assert _count(db, "market_data") == 11   # 10 year-ends + current snapshot

    def test_statement_type_required(self, db, screener_xlsx):
        r = ImportOrchestrator(db).import_screener_excel(screener_xlsx, statement_type="")
        assert not r.success and r.errors
        assert _count(db, "annual_income") == 0

    def test_missing_cash_fails_and_writes_nothing(self, db, tmp_path):
        path = build_screener_workbook(tmp_path / "nocash.xlsx", drop_labels=("Cash & Bank",))
        r = ImportOrchestrator(db).import_screener_excel(path, statement_type="Standalone")
        assert not r.success
        assert "cash_and_equivalents" in r.errors[0]
        assert _count(db, "companies") == 0 and _count(db, "annual_income") == 0

    def test_reimport_is_idempotent(self, db, screener_xlsx):
        imp = ImportOrchestrator(db)
        imp.import_screener_excel(screener_xlsx, statement_type="Consolidated")
        imp.import_screener_excel(screener_xlsx, statement_type="Consolidated")
        assert _count(db, "annual_income") == 10
        assert _count(db, "companies") == 1

    def test_consolidated_and_standalone_kept_separate(self, db, screener_xlsx):
        imp = ImportOrchestrator(db)
        imp.import_screener_excel(screener_xlsx, statement_type="Consolidated")
        imp.import_screener_excel(screener_xlsx, statement_type="Standalone")
        assert _count(db, "annual_income") == 20

    def test_stored_values(self, db, screener_xlsx):
        ImportOrchestrator(db).import_screener_excel(screener_xlsx, statement_type="Consolidated")
        row = db.conn.execute(
            "SELECT revenue, operating_profit, pat, basic_eps FROM annual_income "
            "WHERE fiscal_year = 2017").fetchone()
        assert row == (1000.0, 360.0, 240.0, 2.4)

    def test_market_snapshots(self, db, screener_xlsx):
        ImportOrchestrator(db).import_screener_excel(screener_xlsx, statement_type="Consolidated")
        fy17 = db.conn.execute(
            "SELECT price, market_cap, pe FROM market_data WHERE date = '2017-03-31'").fetchone()
        assert fy17 == (800.0, 80000.0, pytest.approx(800 / 2.4, rel=1e-3))
        today = db.conn.execute(
            "SELECT pe FROM market_data WHERE date = ?", [str(date.today())]).fetchone()
        ttm_pat = sum(83 + 2 * i for i in range(6, 10))   # last four quarters
        assert today[0] == pytest.approx(150000.0 / ttm_pat, rel=1e-3)


# ---------------------------------------------------------------------------
# Valuation history with year-end snapshots
# ---------------------------------------------------------------------------

def test_pe_median_windows_use_dates_not_row_counts():
    dates = [f"{y}-03-31" for y in range(2017, 2027)]
    pe = [10, 10, 10, 10, 10, 10, 10, 30, 30, 30]
    r = analyze_pe_history(pd.DataFrame({"date": dates, "pe": pe}))
    assert r.median_3y == 30
    assert r.median_10y == 10


# ---------------------------------------------------------------------------
# Golden tests against real exports (drop files into tests/fixtures/real/)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not REAL_FIXTURES, reason="no real Screener exports in tests/fixtures/real/")
@pytest.mark.parametrize("path", REAL_FIXTURES, ids=lambda p: p.stem)
def test_real_export_imports_cleanly(db, path):
    r = ImportOrchestrator(db).import_screener_excel(path, statement_type="Consolidated")
    assert r.success, r.errors
    assert len(r.fiscal_years_imported) >= 5
    assert r.quarters_imported >= 4
    assert not any("Unrecognized labels" in w for w in r.warnings), r.warnings
    bad = db.conn.execute("""
        SELECT fiscal_year FROM balance_sheet
        WHERE ABS(total_assets - shareholders_equity - total_liabilities) > 1
    """).fetchall()
    assert bad == []
