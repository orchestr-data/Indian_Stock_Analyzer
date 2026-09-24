"""Data validation — runs checks on parsed data before storage.

Validation is capability-aware: checks are only performed when the required
fields are present.  Missing a field is not itself a failure.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional

from src.ingestion.screener_excel import ParsedWorkbook, ParsedSheet

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    status: str = "PASS"   # "PASS", "WARNING", "FAILED"
    checks: list[dict] = field(default_factory=list)

    def add(self, name: str, passed: bool, message: str, severity: str = "warning") -> None:
        status = "PASS" if passed else severity.upper()
        self.checks.append({"name": name, "status": status, "message": message})
        if not passed:
            if severity == "failed" and self.status != "FAILED":
                self.status = "FAILED"
            elif severity == "warning" and self.status == "PASS":
                self.status = "WARNING"

    def has_failures(self) -> bool:
        return self.status == "FAILED"

    def summary(self) -> str:
        return f"{self.status} — {len(self.checks)} checks"


class Validator:
    """Validates a ParsedWorkbook before it's stored."""

    def validate(self, wb: ParsedWorkbook) -> ValidationResult:
        result = ValidationResult()
        self._check_company_identity(wb, result)
        if wb.income_annual:
            self._check_income(wb.income_annual, result)
        if wb.balance_sheet:
            self._check_balance_sheet(wb.balance_sheet, result)
        if wb.cash_flow:
            self._check_cash_flow(wb.cash_flow, result)
        if wb.shareholding:
            self._check_shareholding(wb.shareholding, result)
        return result

    def _check_company_identity(self, wb: ParsedWorkbook, r: ValidationResult) -> None:
        r.add(
            "company_name_present",
            wb.company_name is not None and len(wb.company_name) > 0,
            f"Company name: {wb.company_name or 'NOT FOUND'}",
            severity="warning",
        )
        r.add(
            "statement_type_known",
            wb.statement_type in ("Consolidated", "Standalone"),
            f"Statement type: {wb.statement_type}",
            severity="warning",
        )

    def _check_income(self, sheet: ParsedSheet, r: ValidationResult) -> None:
        periods = len(sheet.periods)
        r.add(
            "income_has_periods",
            periods >= 1,
            f"Income statement has {periods} period(s)",
            severity="warning",
        )
        r.add(
            "income_has_revenue",
            "revenue" in sheet.rows,
            "Revenue field found in income statement" if "revenue" in sheet.rows
            else "Revenue field NOT found — check label mapping",
            severity="warning",
        )

        # Check chronological order
        if periods >= 2:
            years = [p.fiscal_year for p in sheet.periods]
            is_ordered = years == sorted(years) or years == sorted(years, reverse=True)
            r.add(
                "income_periods_ordered",
                is_ordered,
                f"Period years appear {'ordered' if is_ordered else 'unordered'}: {years[:5]}",
                severity="warning",
            )

    def _check_balance_sheet(self, sheet: ParsedSheet, r: ValidationResult) -> None:
        has_assets = "total_assets" in sheet.rows
        has_equity = "shareholders_equity" in sheet.rows
        has_borrowings = "borrowings" in sheet.rows

        r.add(
            "balance_sheet_has_assets",
            has_assets,
            "Total assets field found" if has_assets else "Total assets NOT found",
            severity="warning",
        )

        # Assets ≈ Liabilities + Equity
        if has_assets and has_equity and has_borrowings:
            for i, period in enumerate(sheet.periods):
                assets = sheet.rows.get("total_assets", [None])[i] if i < len(sheet.rows.get("total_assets", [])) else None
                equity = sheet.rows.get("shareholders_equity", [None])[i] if i < len(sheet.rows.get("shareholders_equity", [])) else None
                liabilities = sheet.rows.get("total_liabilities", [None])[i] if i < len(sheet.rows.get("total_liabilities", [])) else None

                if assets and equity and liabilities:
                    diff_pct = abs(assets - (equity + liabilities)) / assets * 100
                    r.add(
                        f"balance_sheet_reconciles_{period.label}",
                        diff_pct < 5.0,
                        f"{period.label}: Assets={assets:.0f}, Equity+Liabilities={equity + liabilities:.0f} "
                        f"({diff_pct:.1f}% diff)",
                        severity="warning",
                    )
                    break  # check only latest period

    def _check_cash_flow(self, sheet: ParsedSheet, r: ValidationResult) -> None:
        has_cfo = "operating_cash_flow" in sheet.rows
        r.add(
            "cash_flow_has_cfo",
            has_cfo,
            "Operating cash flow found" if has_cfo else "Operating cash flow NOT found",
            severity="warning",
        )

    def _check_shareholding(self, sheet: ParsedSheet, r: ValidationResult) -> None:
        if "promoter_pct" not in sheet.rows:
            return

        for i, period in enumerate(sheet.periods[:3]):
            promoter = _get_val(sheet.rows.get("promoter_pct"), i)
            pledge = _get_val(sheet.rows.get("promoter_pledge_pct"), i)
            fii = _get_val(sheet.rows.get("fii_pct"), i)
            dii = _get_val(sheet.rows.get("dii_pct"), i)
            public = _get_val(sheet.rows.get("public_pct"), i)

            components = [v for v in [promoter, fii, dii, public] if v is not None]
            if len(components) >= 2:
                total = sum(components)
                r.add(
                    f"shareholding_sums_to_100_{period.label}",
                    abs(total - 100.0) < 5.0,
                    f"{period.label}: Shareholding total = {total:.1f}% "
                    f"(expected ~100%)",
                    severity="warning",
                )

            if promoter is not None and pledge is not None:
                r.add(
                    f"pledge_not_exceed_promoter_{period.label}",
                    pledge <= promoter + 0.1,
                    f"{period.label}: Pledge {pledge:.1f}% vs Promoter {promoter:.1f}%",
                    severity="warning",
                )
            break  # check only latest period


def _get_val(lst: Optional[list], idx: int) -> Optional[float]:
    if lst is None or idx >= len(lst):
        return None
    return lst[idx]
