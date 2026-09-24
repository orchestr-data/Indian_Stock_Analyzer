"""Tests for database layer."""

import pytest
import duckdb
from src.database.schema import create_all_tables, drop_all_tables
from src.database.repository import Repository


@pytest.fixture
def in_memory_conn():
    """Fresh in-memory DuckDB connection for each test."""
    conn = duckdb.connect(":memory:")
    create_all_tables(conn)
    yield conn
    conn.close()


@pytest.fixture
def repo(in_memory_conn):
    return Repository(in_memory_conn)


class TestCompanyRepository:
    def test_upsert_and_get(self, repo):
        cid = repo.upsert_company("TCS", "Tata Consultancy Services", "TCS", None, None, "IT_SERVICES")
        assert cid > 0
        company = repo.get_company_by_ticker("TCS")
        assert company is not None
        assert company["company_name"] == "Tata Consultancy Services"

    def test_upsert_updates_existing(self, repo):
        cid1 = repo.upsert_company("TCS", "Old Name")
        cid2 = repo.upsert_company("TCS", "New Name")
        assert cid1 == cid2
        company = repo.get_company_by_ticker("TCS")
        assert company["company_name"] == "New Name"

    def test_list_companies(self, repo):
        repo.upsert_company("TCS", "TCS Ltd")
        repo.upsert_company("INFY", "Infosys Ltd")
        df = repo.list_companies()
        assert len(df) == 2

    def test_search_companies(self, repo):
        repo.upsert_company("TCS", "Tata Consultancy Services")
        repo.upsert_company("INFY", "Infosys Ltd")
        df = repo.search_companies("tata")
        assert len(df) == 1
        assert df.iloc[0]["ticker"] == "TCS"


class TestAnnualIncomeRepository:
    def test_upsert_and_get(self, repo):
        cid = repo.upsert_company("TCS", "TCS")
        repo.upsert_annual_income(cid, "Consolidated", 2025, {
            "revenue": 2500.0, "pat": 300.0, "operating_profit": 600.0,
        })
        df = repo.get_annual_income(cid, "Consolidated")
        assert len(df) == 1
        assert df.iloc[0]["revenue"] == pytest.approx(2500.0)

    def test_upsert_updates_existing(self, repo):
        cid = repo.upsert_company("TCS", "TCS")
        repo.upsert_annual_income(cid, "Consolidated", 2025, {"revenue": 2500.0})
        repo.upsert_annual_income(cid, "Consolidated", 2025, {"revenue": 2600.0})
        df = repo.get_annual_income(cid, "Consolidated")
        assert len(df) == 1
        assert df.iloc[0]["revenue"] == pytest.approx(2600.0)

    def test_multiple_years(self, repo):
        cid = repo.upsert_company("TCS", "TCS")
        for fy in [2021, 2022, 2023, 2024, 2025]:
            repo.upsert_annual_income(cid, "Consolidated", fy, {"revenue": fy * 100.0})
        df = repo.get_annual_income(cid, "Consolidated")
        assert len(df) == 5
        assert list(df["fiscal_year"]) == [2021, 2022, 2023, 2024, 2025]

    def test_consolidated_standalone_separate(self, repo):
        cid = repo.upsert_company("TCS", "TCS")
        repo.upsert_annual_income(cid, "Consolidated", 2025, {"revenue": 2500.0})
        repo.upsert_annual_income(cid, "Standalone", 2025, {"revenue": 2000.0})
        df_c = repo.get_annual_income(cid, "Consolidated")
        df_s = repo.get_annual_income(cid, "Standalone")
        assert df_c.iloc[0]["revenue"] == pytest.approx(2500.0)
        assert df_s.iloc[0]["revenue"] == pytest.approx(2000.0)


class TestImportLogging:
    def test_log_and_check_duplicate(self, repo):
        cid = repo.upsert_company("TCS", "TCS")
        repo.log_import(cid, "screener_excel", "Screener", "tcs.xlsx",
                        "abc123", "Consolidated", "success")
        assert repo.file_already_imported("abc123") is True
        assert repo.file_already_imported("xyz999") is False

    def test_import_history(self, repo):
        cid = repo.upsert_company("TCS", "TCS")
        repo.log_import(cid, "screener_excel", "Screener", "tcs.xlsx",
                        "abc123", "Consolidated", "success")
        df = repo.get_import_history(cid)
        assert len(df) == 1
        assert df.iloc[0]["source_file"] == "tcs.xlsx"
