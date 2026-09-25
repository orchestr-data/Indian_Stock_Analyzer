"""Import orchestrator — coordinates parsing, validation, and storage."""

from __future__ import annotations

import logging
import re
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from src.config import get_companies_path
from src.database.connection import DatabaseConnection
from src.database.repository import Repository
from src.ingestion.screener_excel import (
    STATEMENT_TYPES,
    ParsedSheet,
    ParsedWorkbook,
    ScreenerExcelParser,
)
from src.ingestion.validator import Validator, ValidationResult

logger = logging.getLogger(__name__)

# Fields without which the analysis pages are meaningless. If any of these has
# no values at all, the import fails instead of reporting success.
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "income_annual": ("revenue", "pat"),
    "balance_sheet": ("shareholders_equity", "borrowings", "cash_and_equivalents"),
}


class ImportError_(Exception):
    """Raised for import problems that should be shown to the user as-is."""


class ImportResult:
    """Result of a single file import."""

    def __init__(self) -> None:
        self.success = False
        self.company_id: Optional[int] = None
        self.company_name: Optional[str] = None
        self.ticker: Optional[str] = None
        self.statement_type: Optional[str] = None
        self.validation: Optional[ValidationResult] = None
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.fiscal_years_imported: list[int] = []
        self.balance_years_imported: int = 0
        self.cashflow_years_imported: int = 0
        self.quarters_imported: int = 0
        self.shareholding_periods: int = 0
        self.market_snapshots: int = 0
        self.raw_file_stored_at: Optional[str] = None

    @property
    def status_label(self) -> str:
        if self.errors:
            return "Failed"
        if self.warnings:
            return "Imported with warnings"
        return "Imported successfully"


def ticker_from_filename(filename: str) -> str:
    """'TCS__1_.xlsx' / 'TCS (1).xlsx' / 'tcs.xlsx' → 'TCS'."""
    stem = Path(filename).stem
    stem = re.sub(r"[_\s]*\(?\d+\)?_*$", "", stem)
    return stem.strip(" _-").upper() or "UNKNOWN"


class ImportOrchestrator:
    """Orchestrates the full import pipeline for a Screener Excel file."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self._repo = Repository(db.conn)
        self._parser = ScreenerExcelParser()
        self._validator = Validator()

    def import_screener_excel(
        self,
        file_path: str | Path,
        ticker_override: Optional[str] = None,
        sector_override: Optional[str] = None,
        *,
        statement_type: str,
        original_filename: Optional[str] = None,
    ) -> ImportResult:
        """Full import pipeline: parse → validate → store (one transaction) → copy raw file.

        statement_type must be "Consolidated" or "Standalone". Screener's export
        does not say which view it came from, so the user has to tell us.
        """
        result = ImportResult()
        path = Path(file_path)
        display_name = original_filename or path.name

        if statement_type not in STATEMENT_TYPES:
            result.errors.append(
                f"Choose Consolidated or Standalone before importing (got {statement_type!r})."
            )
            return result

        try:
            parsed = self._parser.parse(path)
            parsed.statement_type = statement_type
            for sheet in (parsed.income_annual, parsed.balance_sheet, parsed.cash_flow,
                          parsed.income_quarterly, parsed.shareholding):
                if sheet is not None:
                    sheet.statement_type = statement_type
            result.warnings.extend(parsed.warnings)

            ticker = (ticker_override or parsed.company_ticker
                      or ticker_from_filename(display_name)).strip().upper()
            company_name = parsed.company_name or ticker
            result.ticker = ticker
            result.company_name = company_name
            result.statement_type = statement_type

            self._check_required_fields(parsed)

            if self._repo.file_already_imported(parsed.file_hash):
                result.warnings.append(
                    f"This file was imported before (hash {parsed.file_hash[:8]}); "
                    "existing rows are updated in place."
                )

            val_result = self._validator.validate(parsed)
            result.validation = val_result
            if val_result.has_failures():
                raise ImportError_(f"Validation failed: {val_result.summary()}")

            conn = self._db.conn
            conn.execute("BEGIN TRANSACTION")
            try:
                company_id = self._repo.upsert_company(
                    ticker=ticker,
                    company_name=company_name,
                    sector=sector_override or "DEFAULT",
                )
                result.company_id = company_id

                if parsed.income_annual:
                    result.fiscal_years_imported = self._store_annual_income(
                        company_id, statement_type, parsed.income_annual)
                if parsed.balance_sheet:
                    result.balance_years_imported = self._store_balance_sheet(
                        company_id, statement_type, parsed.balance_sheet)
                if parsed.cash_flow:
                    result.cashflow_years_imported = self._store_cash_flow(
                        company_id, statement_type, parsed.cash_flow)
                if parsed.income_quarterly:
                    result.quarters_imported = self._store_quarterly_income(
                        company_id, statement_type, parsed.income_quarterly)
                if parsed.shareholding:
                    result.shareholding_periods = self._store_shareholding(
                        company_id, parsed.shareholding)
                result.market_snapshots = self._store_market_data(company_id, parsed)

                if not result.fiscal_years_imported:
                    raise ImportError_(
                        "No annual periods were stored. The file may not be a Screener "
                        "export, or its layout has changed."
                    )

                self._repo.log_import(
                    company_id=company_id,
                    source_type="screener_excel",
                    source_name="Screener.in Excel Export",
                    source_file=display_name,
                    file_hash=parsed.file_hash,
                    statement_type=statement_type,
                    status="success" if not result.warnings else "warning",
                    warnings=result.warnings or None,
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

            raw_path = self._store_raw_file(path, ticker, display_name)
            result.raw_file_stored_at = str(raw_path)
            result.success = True
            logger.info("Import complete: %s | %s | %d years | %d quarters",
                        company_name, statement_type,
                        len(result.fiscal_years_imported), result.quarters_imported)

        except ImportError_ as exc:
            result.errors.append(str(exc))
        except Exception as exc:
            logger.exception("Import failed: %s", exc)
            result.errors.append(f"Import failed: {exc}")

        return result

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_required_fields(parsed: ParsedWorkbook) -> None:
        missing: list[str] = []
        for attr, fields in REQUIRED_FIELDS.items():
            sheet: Optional[ParsedSheet] = getattr(parsed, attr)
            if sheet is None or not sheet.periods:
                missing.append(f"{attr} (section not found)")
                continue
            for f in fields:
                if not any(v is not None for v in sheet.rows.get(f, [])):
                    missing.append(f"{attr}.{f}")
        if missing:
            raise ImportError_(
                "Required data missing: " + ", ".join(missing)
                + ". Nothing was imported. Check the Data Quality page for unrecognized labels."
            )

    # ------------------------------------------------------------------
    # Storage helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _column(sheet: ParsedSheet, i: int) -> dict:
        return {k: (v[i] if i < len(v) else None) for k, v in sheet.rows.items()}

    def _store_annual_income(self, company_id: int, stmt_type: str, sheet: ParsedSheet) -> list[int]:
        years = []
        for i, period in enumerate(sheet.periods):
            if period.is_ttm:
                continue
            data = self._column(sheet, i)
            if data.get("ebit") is None and data.get("pbt") is not None and data.get("interest") is not None:
                data["ebit"] = data["pbt"] + data["interest"]
            if data.get("ebitda") is None and data.get("operating_profit") is not None:
                data["ebitda"] = data["operating_profit"]
            self._repo.upsert_annual_income(company_id, stmt_type, period.fiscal_year, data)
            years.append(period.fiscal_year)
        return years

    def _store_balance_sheet(self, company_id: int, stmt_type: str, sheet: ParsedSheet) -> int:
        count = 0
        for i, period in enumerate(sheet.periods):
            if period.is_ttm:
                continue
            data = self._column(sheet, i)
            if data.get("shareholders_equity") is None:
                cap, res = data.get("equity_capital"), data.get("reserves")
                if cap is not None and res is not None:
                    data["shareholders_equity"] = cap + res
            if data.get("other_current_liabilities") is None:
                data["other_current_liabilities"] = data.get("other_liabilities")
            self._repo.upsert_balance_sheet(company_id, stmt_type, period.fiscal_year, data)
            count += 1
        return count

    def _store_cash_flow(self, company_id: int, stmt_type: str, sheet: ParsedSheet) -> int:
        count = 0
        for i, period in enumerate(sheet.periods):
            if period.is_ttm:
                continue
            data = self._column(sheet, i)
            cfo, capex = data.get("operating_cash_flow"), data.get("capital_expenditure")
            if cfo is not None and capex is not None:
                data["free_cash_flow"] = cfo - abs(capex)
            self._repo.upsert_cash_flow(company_id, stmt_type, period.fiscal_year, data)
            count += 1
        return count

    def _store_quarterly_income(self, company_id: int, stmt_type: str, sheet: ParsedSheet) -> int:
        count = 0
        for i, period in enumerate(sheet.periods):
            if period.is_ttm or period.fiscal_quarter is None:
                continue
            data = self._column(sheet, i)
            data["period_end_date"] = period.period_end_date
            self._repo.upsert_quarterly_income(
                company_id, stmt_type, period.fiscal_year, period.fiscal_quarter, data)
            count += 1
        return count

    def _store_shareholding(self, company_id: int, sheet: ParsedSheet) -> int:
        count = 0
        for i, period in enumerate(sheet.periods):
            if period.period_end_date is None:
                continue
            data = self._column(sheet, i)
            data["fiscal_year"] = period.fiscal_year
            data["fiscal_quarter"] = period.fiscal_quarter
            self._repo.upsert_shareholding(company_id, str(period.period_end_date), data)
            count += 1
        return count

    def _store_market_data(self, company_id: int, parsed: ParsedWorkbook) -> int:
        """Store the current price snapshot plus one snapshot per fiscal year-end."""
        inc, bs, qtr = parsed.income_annual, parsed.balance_sheet, parsed.income_quarterly
        if inc is None:
            return 0

        equity_by_fy: dict[int, Optional[float]] = {}
        debt_by_fy: dict[int, Optional[float]] = {}
        cash_by_fy: dict[int, Optional[float]] = {}
        if bs is not None:
            for i, p in enumerate(bs.periods):
                row = self._column(bs, i)
                equity_by_fy[p.fiscal_year] = row.get("shareholders_equity")
                debt_by_fy[p.fiscal_year] = row.get("borrowings")
                cash_by_fy[p.fiscal_year] = row.get("cash_and_equivalents")

        stored = 0
        shares_series = inc.rows.get("weighted_avg_shares", [])
        eps_series = inc.rows.get("basic_eps", [])
        for i, p in enumerate(inc.periods):
            price = parsed.year_end_prices[i] if i < len(parsed.year_end_prices) else None
            shares = shares_series[i] if i < len(shares_series) else None
            if price is None or p.period_end_date is None:
                continue
            eps = eps_series[i] if i < len(eps_series) else None
            mcap = price * shares if shares else None
            eq = equity_by_fy.get(p.fiscal_year)
            self._repo.upsert_market_data(company_id, str(p.period_end_date), {
                "price": price,
                "market_cap": round(mcap, 2) if mcap else None,
                "shares_outstanding": shares,
                "pe": round(price / eps, 2) if eps and eps > 0 else None,
                "pb": round(mcap / eq, 2) if mcap and eq and eq > 0 else None,
            })
            stored += 1

        if parsed.current_price is None and parsed.market_cap is None:
            return stored

        latest_i = len(inc.periods) - 1
        latest = self._column(inc, latest_i)
        latest_fy = inc.periods[latest_i].fiscal_year
        ttm_pat, ttm_ebitda = self._ttm(qtr, latest.get("pat"), latest.get("ebitda"))
        mcap = parsed.market_cap
        if mcap is None and parsed.current_price is not None and shares_series:
            mcap = parsed.current_price * (shares_series[-1] or 0) or None
        eq = equity_by_fy.get(latest_fy)
        debt, cash = debt_by_fy.get(latest_fy), cash_by_fy.get(latest_fy)
        ev = mcap + (debt or 0.0) - (cash or 0.0) if mcap is not None and debt is not None else None
        div = latest.get("dividend_amount")

        self._repo.upsert_market_data(company_id, str(date.today()), {
            "price": parsed.current_price,
            "market_cap": mcap,
            "shares_outstanding": shares_series[-1] if shares_series else None,
            "pe": round(mcap / ttm_pat, 2) if mcap and ttm_pat and ttm_pat > 0 else None,
            "pb": round(mcap / eq, 2) if mcap and eq and eq > 0 else None,
            "enterprise_value": round(ev, 2) if ev is not None else None,
            "ev_ebitda": round(ev / ttm_ebitda, 2) if ev is not None and ttm_ebitda and ttm_ebitda > 0 else None,
            "dividend_yield": round(div / mcap * 100, 2) if div and mcap else None,
        })
        return stored + 1

    @staticmethod
    def _ttm(qtr: Optional[ParsedSheet], fallback_pat, fallback_ebitda):
        """Sum the last four quarters; fall back to the latest fiscal year."""
        if qtr is None or len(qtr.periods) < 4:
            return fallback_pat, fallback_ebitda

        def last4(key: str):
            vals = qtr.rows.get(key, [])[-4:]
            return sum(vals) if len(vals) == 4 and all(v is not None for v in vals) else None

        pat = last4("pat")
        ebitda = last4("operating_profit")
        return (pat if pat is not None else fallback_pat,
                ebitda if ebitda is not None else fallback_ebitda)

    def _store_raw_file(self, source_path: Path, ticker: str, display_name: str) -> Path:
        """Copy the original file to data/raw/companies/TICKER/screener/<date>_<name>."""
        dest_dir = get_companies_path() / ticker.upper() / "screener"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{datetime.now():%Y-%m-%d}_{Path(display_name).name}"
        if not dest.exists():
            shutil.copy2(source_path, dest)
        return dest
