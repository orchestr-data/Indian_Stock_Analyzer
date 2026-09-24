"""Import orchestrator — coordinates parsing, validation, and storage."""

from __future__ import annotations
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import get_companies_path
from src.database.connection import DatabaseConnection
from src.database.repository import Repository
from src.ingestion.screener_excel import ScreenerExcelParser, ParsedWorkbook, ParsedSheet
from src.ingestion.validator import Validator, ValidationResult
from src.models.company import SectorEnum

logger = logging.getLogger(__name__)


class ImportResult:
    """Result of a single file import."""

    def __init__(self) -> None:
        self.success = False
        self.company_id: Optional[int] = None
        self.company_name: Optional[str] = None
        self.statement_type: Optional[str] = None
        self.validation: Optional[ValidationResult] = None
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.fiscal_years_imported: list[int] = []
        self.quarters_imported: int = 0
        self.shareholding_periods: int = 0
        self.raw_file_stored_at: Optional[str] = None

    @property
    def status_label(self) -> str:
        if self.errors:
            return "Failed"
        if self.warnings:
            return "Imported with warnings"
        return "Imported successfully"


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
    ) -> ImportResult:
        """Full import pipeline: parse → validate → store → copy raw file."""
        result = ImportResult()
        path = Path(file_path)

        try:
            # 1. Parse
            logger.info("Importing: %s", path.name)
            parsed = self._parser.parse(path)
            result.warnings.extend(parsed.warnings)

            # 2. Determine ticker/name
            ticker = ticker_override or parsed.company_ticker or path.stem
            company_name = parsed.company_name or ticker
            result.company_name = company_name
            result.statement_type = parsed.statement_type

            # 3. Check for duplicate
            if self._repo.file_already_imported(parsed.file_hash):
                result.warnings.append(
                    f"File already imported (hash match: {parsed.file_hash[:8]}). "
                    "Proceeding with re-import."
                )

            # 4. Validate
            val_result = self._validator.validate(parsed)
            result.validation = val_result
            if val_result.has_failures():
                result.errors.append(f"Validation failed: {val_result.summary()}")
                return result

            # 5. Upsert company
            sector = sector_override or "DEFAULT"
            company_id = self._repo.upsert_company(
                ticker=ticker,
                company_name=company_name,
                sector=sector,
            )
            result.company_id = company_id

            # 6. Store financial data
            stmt_type = parsed.statement_type
            if parsed.income_annual:
                fiscal_years = self._store_annual_income(
                    company_id, stmt_type, parsed.income_annual
                )
                result.fiscal_years_imported = fiscal_years

            if parsed.balance_sheet:
                self._store_balance_sheet(company_id, stmt_type, parsed.balance_sheet)

            if parsed.cash_flow:
                self._store_cash_flow(company_id, stmt_type, parsed.cash_flow)

            if parsed.income_quarterly:
                result.quarters_imported = self._store_quarterly_income(
                    company_id, stmt_type, parsed.income_quarterly
                )

            if parsed.shareholding:
                result.shareholding_periods = self._store_shareholding(
                    company_id, parsed.shareholding
                )

            # 7. Copy raw file to company storage
            raw_path = self._store_raw_file(path, ticker, parsed)
            result.raw_file_stored_at = str(raw_path)

            # 8. Log import
            self._repo.log_import(
                company_id=company_id,
                source_type="screener_excel",
                source_name="Screener.in Excel Export",
                source_file=path.name,
                file_hash=parsed.file_hash,
                statement_type=stmt_type,
                status="success" if not result.warnings else "warning",
                warnings=result.warnings or None,
            )

            result.success = True
            logger.info(
                "Import complete: %s | %s | %d years | %d quarters",
                company_name, stmt_type,
                len(result.fiscal_years_imported), result.quarters_imported,
            )

        except Exception as exc:
            logger.exception("Import failed: %s", exc)
            result.errors.append(str(exc))

        return result

    # ------------------------------------------------------------------
    # Storage helpers
    # ------------------------------------------------------------------

    def _store_annual_income(
        self, company_id: int, stmt_type: str, sheet: ParsedSheet
    ) -> list[int]:
        years = []
        for i, period in enumerate(sheet.periods):
            if period.is_ttm or period.fiscal_quarter is not None:
                continue
            data = {k: (v[i] if i < len(v) else None) for k, v in sheet.rows.items()}

            # Derive EBIT if not present (EBIT = operating_profit + other_income - interest?)
            # Screener sometimes provides EBIT directly, sometimes not
            # Try: EBIT ≈ PBT + Interest  or  Operating Profit + Other Income
            if "ebit" not in data or data.get("ebit") is None:
                pbt = data.get("pbt")
                interest = data.get("interest")
                if pbt is not None and interest is not None:
                    data["ebit"] = pbt + interest

            # EBITDA: EBIT + Depreciation
            if "ebitda" not in data or data.get("ebitda") is None:
                ebit = data.get("ebit")
                dep = data.get("depreciation")
                if ebit is not None and dep is not None:
                    data["ebitda"] = ebit + dep

            self._repo.upsert_annual_income(company_id, stmt_type, period.fiscal_year, data)
            years.append(period.fiscal_year)
        return years

    def _store_balance_sheet(self, company_id: int, stmt_type: str, sheet: ParsedSheet) -> None:
        for i, period in enumerate(sheet.periods):
            if period.is_ttm or period.fiscal_quarter is not None:
                continue
            data = {k: (v[i] if i < len(v) else None) for k, v in sheet.rows.items()}
            # Derive shareholders_equity if not direct
            if data.get("shareholders_equity") is None:
                equity_cap = data.get("equity_capital")
                reserves = data.get("reserves")
                if equity_cap is not None and reserves is not None:
                    data["shareholders_equity"] = equity_cap + reserves
            self._repo.upsert_balance_sheet(company_id, stmt_type, period.fiscal_year, data)

    def _store_cash_flow(self, company_id: int, stmt_type: str, sheet: ParsedSheet) -> None:
        for i, period in enumerate(sheet.periods):
            if period.is_ttm or period.fiscal_quarter is not None:
                continue
            data = {k: (v[i] if i < len(v) else None) for k, v in sheet.rows.items()}
            # Derive FCF = CFO - CapEx
            cfo = data.get("operating_cash_flow")
            capex = data.get("capital_expenditure")
            if cfo is not None and capex is not None:
                data["free_cash_flow"] = cfo - abs(capex)
            self._repo.upsert_cash_flow(company_id, stmt_type, period.fiscal_year, data)

    def _store_quarterly_income(
        self, company_id: int, stmt_type: str, sheet: ParsedSheet
    ) -> int:
        count = 0
        for i, period in enumerate(sheet.periods):
            if period.is_ttm or period.fiscal_quarter is None:
                continue
            data = {k: (v[i] if i < len(v) else None) for k, v in sheet.rows.items()}
            data["period_end_date"] = period.period_end_date
            self._repo.upsert_quarterly_income(
                company_id, stmt_type,
                period.fiscal_year, period.fiscal_quarter, data,
            )
            count += 1
        return count

    def _store_shareholding(self, company_id: int, sheet: ParsedSheet) -> int:
        count = 0
        for i, period in enumerate(sheet.periods):
            if period.period_end_date is None:
                continue
            data = {k: (v[i] if i < len(v) else None) for k, v in sheet.rows.items()}
            data["fiscal_year"] = period.fiscal_year
            data["fiscal_quarter"] = period.fiscal_quarter
            self._repo.upsert_shareholding(
                company_id, str(period.period_end_date), data
            )
            count += 1
        return count

    def _store_raw_file(
        self, source_path: Path, ticker: str, parsed: ParsedWorkbook
    ) -> Path:
        """Copy the original file to data/raw/companies/TICKER/screener/date.xlsx."""
        companies_root = get_companies_path()
        today = datetime.now().strftime("%Y-%m-%d")
        dest_dir = companies_root / ticker.upper() / "screener"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{today}_{source_path.name}"
        if not dest.exists():
            shutil.copy2(source_path, dest)
            logger.info("Raw file stored: %s", dest)
        else:
            logger.info("Raw file already exists at: %s", dest)
        return dest
