"""Shared fixtures. `screener_xlsx` builds a workbook with the same layout as a
real Screener export (workbook v2.1): values live only in "Data Sheet", and the
presentation sheets hold formulas with no cached results."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import openpyxl
import pytest

from src.database.connection import DatabaseConnection
from src.database.schema import create_all_tables

YEARS = [datetime(y, 3, 31) for y in range(2017, 2027)]
QUARTERS = [datetime(2024, 3, 31), datetime(2024, 6, 30), datetime(2024, 9, 30),
            datetime(2024, 12, 31), datetime(2025, 3, 31), datetime(2025, 6, 30),
            datetime(2025, 9, 30), datetime(2025, 12, 31), datetime(2026, 3, 31),
            datetime(2026, 6, 30)]


def _series(start: float, step: float, n: int = 10) -> list[float]:
    return [start + step * i for i in range(n)]


def build_screener_workbook(path: Path, *, drop_labels: tuple[str, ...] = ()) -> Path:
    wb = openpyxl.Workbook()
    pl = wb.active
    pl.title = "Profit & Loss"
    pl.append(["='Data Sheet'!B1"])
    pl.append([])
    pl.append(["Narration"] + [f"='Data Sheet'!{c}16" for c in "BCDEFGHIJK"])
    pl.append(["Sales"] + [f"='Data Sheet'!{c}17" for c in "BCDEFGHIJK"])
    for name in ("Quarters", "Balance Sheet", "Cash Flow", "Customization"):
        wb.create_sheet(name).append(["='Profit & Loss'!A1"])

    ds = wb.create_sheet("Data Sheet")
    rows: list[list] = [
        ["COMPANY NAME", "TEST INDUSTRIES LTD"],
        ["LATEST VERSION", 2.1],
        ["CURRENT VERSION", 2.1],
        [],
        ["META"],
        ["Number of shares", None],
        ["Face Value", 1],
        ["Current Price", 1500.0],
        ["Market Capitalization", 150000.0],
        [], [], [], [], [],
        ["PROFIT & LOSS"],
        ["Report Date"] + YEARS,
        ["Sales"] + _series(1000, 100),
        ["Raw Material Cost"] + _series(300, 30),
        ["Change in Inventory"] + [10.0] * 10,
        ["Power and Fuel"] + [None] * 10,
        ["Other Mfr. Exp"] + [50.0] * 10,
        ["Employee Cost"] + _series(200, 20),
        ["Selling and admin"] + [60.0] * 10,
        ["Other Expenses"] + [40.0] * 10,
        ["Other Income"] + [20.0] * 10,
        ["Depreciation"] + [50.0] * 10,
        ["Interest"] + [10.0] * 10,
        ["Profit before tax"] + _series(320, 50),
        ["Tax"] + _series(80, 12.5),
        ["Net profit"] + _series(240, 37.5),
        ["Dividend Amount"] + [60.0] * 10,
        [], [], [], [], [], [], [], [],
        ["Quarters"],
        ["Report Date"] + QUARTERS,
        ["Sales"] + _series(450, 10),
        ["Expenses"] + _series(330, 7),
        ["Other Income"] + [5.0] * 10,
        ["Depreciation"] + [13.0] * 10,
        ["Interest"] + [2.5] * 10,
        ["Profit before tax"] + _series(110, 3),
        ["Tax"] + _series(27, 1),
        ["Net profit"] + _series(83, 2),
        ["Operating Profit"] + _series(120, 3),
        [], [], [], [],
        ["BALANCE SHEET"],
        ["Report Date"] + YEARS,
        ["Equity Share Capital"] + [100.0] * 10,
        ["Reserves"] + _series(900, 150),
        ["Borrowings"] + _series(300, -20),
        ["Other Liabilities"] + [200.0] * 10,
        ["Total"] + [100 + 900 + 150 * i + 300 - 20 * i + 200 for i in range(10)],
        ["Net Block"] + [600.0] * 10,
        ["Capital Work in Progress"] + [50.0] * 10,
        ["Investments"] + [150.0] * 10,
        ["Other Assets"] + [700 + 130 * i for i in range(10)],
        ["Total"] + [100 + 900 + 150 * i + 300 - 20 * i + 200 for i in range(10)],
        ["Receivables"] + _series(200, 15),
        ["Inventory"] + [120.0] * 10,
        ["Cash & Bank"] + _series(80, 10),
        ["No. of Equity Shares"] + [1_000_000_000.0] * 10,
        ["New Bonus Shares"] + [None] * 10,
        ["Face value"] + [1.0] * 10,
        [], [], [], [], [], [], [],
        ["CASH FLOW:"],
        ["Report Date"] + YEARS,
        ["Cash from Operating Activity"] + _series(260, 35),
        ["Cash from Investing Activity"] + [-90.0] * 10,
        ["Cash from Financing Activity"] + [-150.0] * 10,
        ["Net Cash Flow"] + _series(20, 35),
        [], [], [], [],
        ["PRICE:"] + _series(800, 70),
        [],
        ["DERIVED:"],
        ["Adjusted Equity Shares in Cr"] + [100.0] * 10,
    ]
    for r in rows:
        if r and r[0] in drop_labels:
            continue
        ds.append(r)
    wb.save(path)
    return path


@pytest.fixture
def screener_xlsx(tmp_path) -> Path:
    return build_screener_workbook(tmp_path / "TESTCO__1_.xlsx")


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ingestion.importer.get_companies_path",
                        lambda: tmp_path / "raw" / "companies")
    conn = DatabaseConnection(str(tmp_path / "test.duckdb"))
    create_all_tables(conn.conn)
    yield conn
    conn.close()


REAL_FIXTURES = sorted((Path(__file__).parent / "fixtures" / "real").glob("*.xlsx"))
