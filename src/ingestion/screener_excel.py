"""Screener.in Excel export parser.

Screener.in exports a multi-sheet workbook.  The exact sheet names and layout
vary by export version, but the general structure is:

  Sheet names observed in practice:
    "Profit & Loss"  /  "P&L"
    "Balance Sheet"  /  "Balance sheet"
    "Cash Flow"      /  "Cash flow"
    "Quarterly"      /  "Quarterly Results"
    "Shareholding"   /  "Shareholding Pattern"
    "Annual"         /  "Annual"   (sometimes a combined annual sheet)

  Row layout (typical):
    Row 1 or 2:  Column headers — first cell is a label, subsequent cells are
                 fiscal periods (e.g. "Mar 2026", "Mar 2025", ...) or quarters.
    Rows 3+:     One financial metric per row.
                 Column A = metric label
                 Columns B..N = values for each period

  Number format: Indian Crore (₹ Cr).  Values already in crore.
  Negative values may appear as plain negatives or in parentheses.

IMPORTANT:
  Do NOT guess the exact Screener format — if your export looks different,
  submit a sample and the parser will be updated.

  This parser is designed defensively:
  - Unknown labels are logged and skipped, not silently dropped.
  - Missing values are stored as None.
  - Duplicate rows for the same label are flagged.
  - Statement type (Consolidated / Standalone) is detected from the file.
"""

from __future__ import annotations
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import openpyxl

from src.ingestion.normalizer import (
    normalize_income_label,
    normalize_balance_label,
    normalize_cashflow_label,
    normalize_shareholding_label,
    clean_numeric,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures returned by the parser
# ---------------------------------------------------------------------------


@dataclass
class ParsedPeriod:
    """Represents one period column from the Screener export."""
    label: str          # raw label e.g. "Mar 2026"
    fiscal_year: int    # e.g. 2026
    fiscal_quarter: Optional[int] = None
    period_end_date: Optional[date] = None
    is_ttm: bool = False


@dataclass
class ParsedSheet:
    """One parsed sheet with its periods and data rows."""
    sheet_name: str
    statement_type: str  # "Consolidated" or "Standalone"
    periods: list[ParsedPeriod]
    rows: dict[str, list[Optional[float]]]   # canonical_field → [val_for_period_0, ...]
    unknown_labels: list[str] = field(default_factory=list)


@dataclass
class ParsedWorkbook:
    """Complete parsed output from one Screener Excel file."""
    file_path: str
    file_hash: str
    company_name: Optional[str]
    company_ticker: Optional[str]
    statement_type: str
    income_annual: Optional[ParsedSheet] = None
    balance_sheet: Optional[ParsedSheet] = None
    cash_flow: Optional[ParsedSheet] = None
    income_quarterly: Optional[ParsedSheet] = None
    shareholding: Optional[ParsedSheet] = None
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Period parsing
# ---------------------------------------------------------------------------

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_QUARTER_END_MONTHS = {3: 4, 6: 1, 9: 2, 12: 3}  # month → quarter number


def _parse_period_label(label: str) -> Optional[ParsedPeriod]:
    """Parse period header cells like 'Mar 2026', 'Jun 2025', 'TTM'."""
    if not label or str(label).strip() == "":
        return None

    s = str(label).strip()

    if "ttm" in s.lower():
        return ParsedPeriod(label=s, fiscal_year=0, is_ttm=True)

    # Match "Mon YYYY" or "YYYY"
    m = re.match(r"([A-Za-z]+)\s+(\d{4})", s)
    if m:
        month_str = m.group(1).lower()[:3]
        year = int(m.group(2))
        month = _MONTH_MAP.get(month_str)
        if month is None:
            return None

        # Indian fiscal year ends March 31
        # "Mar 2026" → FY2026 (April 2025 – March 2026)
        # "Jun 2025" → FY2026 (quarterly — Q1 FY2026)
        fiscal_year = year if month <= 3 else year + 1
        quarter = _QUARTER_END_MONTHS.get(month)

        # Determine last day of month
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        return ParsedPeriod(
            label=s,
            fiscal_year=fiscal_year,
            fiscal_quarter=quarter,
            period_end_date=end_date,
        )

    # Plain year like "2026"
    m2 = re.match(r"^(\d{4})$", s)
    if m2:
        year = int(m2.group(1))
        return ParsedPeriod(
            label=s, fiscal_year=year,
            period_end_date=date(year, 3, 31),
        )

    return None


# ---------------------------------------------------------------------------
# Main parser class
# ---------------------------------------------------------------------------

class ScreenerExcelParser:
    """Parse a Screener.in Excel export workbook."""

    def __init__(self) -> None:
        self._wb: Optional[openpyxl.Workbook] = None

    def parse(self, file_path: str | Path) -> ParsedWorkbook:
        """Parse the workbook and return structured data."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_hash = self._hash_file(path)
        logger.info("Parsing Screener export: %s (hash: %s)", path.name, file_hash[:8])

        self._wb = openpyxl.load_workbook(path, read_only=True, data_only=True)

        company_name, ticker = self._detect_company()
        statement_type = self._detect_statement_type()

        result = ParsedWorkbook(
            file_path=str(path),
            file_hash=file_hash,
            company_name=company_name,
            company_ticker=ticker,
            statement_type=statement_type,
        )

        # Try each known sheet name pattern
        result.income_annual = self._parse_sheet(
            ["Profit & Loss", "P&L", "Annual", "Annual Report", "Profit and Loss"],
            normalize_income_label,
            "income_annual",
            is_quarterly=False,
        )
        result.balance_sheet = self._parse_sheet(
            ["Balance Sheet", "Balance sheet", "BalanceSheet"],
            normalize_balance_label,
            "balance_sheet",
            is_quarterly=False,
        )
        result.cash_flow = self._parse_sheet(
            ["Cash Flow", "Cash flow", "Cashflow"],
            normalize_cashflow_label,
            "cash_flow",
            is_quarterly=False,
        )
        result.income_quarterly = self._parse_sheet(
            ["Quarterly", "Quarterly Results", "Quarterly P&L"],
            normalize_income_label,
            "quarterly",
            is_quarterly=True,
        )
        result.shareholding = self._parse_sheet(
            ["Shareholding", "Shareholding Pattern", "Share Holding"],
            normalize_shareholding_label,
            "shareholding",
            is_quarterly=True,
        )

        # Collect warnings
        for sheet in [result.income_annual, result.balance_sheet,
                      result.cash_flow, result.income_quarterly, result.shareholding]:
            if sheet and sheet.unknown_labels:
                result.warnings.append(
                    f"[{sheet.sheet_name}] Unrecognized labels: "
                    + ", ".join(sheet.unknown_labels[:10])
                )

        self._wb.close()
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _detect_company(self) -> tuple[Optional[str], Optional[str]]:
        """Try to read company name and ticker from common header positions."""
        if self._wb is None:
            return None, None
        for sheet_name in self._wb.sheetnames:
            ws = self._wb[sheet_name]
            # Screener often puts company name in A1
            val = ws.cell(1, 1).value
            if val and isinstance(val, str) and len(val) > 1:
                # Remove common suffixes
                name = val.strip()
                # Try to extract ticker if in parentheses: "TCS (TCS)"
                m = re.search(r"\(([A-Z0-9&-]{2,20})\)", name)
                ticker = m.group(1) if m else None
                clean_name = re.sub(r"\s*\(.*?\)", "", name).strip()
                return clean_name, ticker
        return None, None

    def _detect_statement_type(self) -> str:
        """Detect if export is Consolidated or Standalone."""
        if self._wb is None:
            return "Standalone"
        # Check sheet names and cell A1 content
        for sheet_name in self._wb.sheetnames:
            if "consolidated" in sheet_name.lower():
                return "Consolidated"
            if "standalone" in sheet_name.lower():
                return "Standalone"
            ws = self._wb[sheet_name]
            a1 = str(ws.cell(1, 1).value or "").lower()
            if "consolidated" in a1:
                return "Consolidated"
            if "standalone" in a1:
                return "Standalone"
        return "Consolidated"  # default assumption

    def _find_sheet(self, candidates: list[str]) -> Optional[openpyxl.worksheet.worksheet.Worksheet]:
        """Find the first matching sheet by candidate names (case-insensitive)."""
        if self._wb is None:
            return None
        sheet_map = {s.lower(): s for s in self._wb.sheetnames}
        for candidate in candidates:
            actual = sheet_map.get(candidate.lower())
            if actual:
                return self._wb[actual]
        # Partial match fallback
        for candidate in candidates:
            for actual_lower, actual in sheet_map.items():
                if candidate.lower() in actual_lower or actual_lower in candidate.lower():
                    return self._wb[actual]
        return None

    def _parse_sheet(
        self,
        sheet_candidates: list[str],
        normalize_fn: Any,
        kind: str,
        is_quarterly: bool,
    ) -> Optional[ParsedSheet]:
        """Parse a single sheet, returning ParsedSheet or None."""
        ws = self._find_sheet(sheet_candidates)
        if ws is None:
            logger.debug("Sheet not found for kind=%s (tried: %s)", kind, sheet_candidates)
            return None

        # Read all rows into a list for random access
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            return None

        # Find the header row — first row with multiple non-empty cells
        header_row_idx = 0
        for i, row in enumerate(all_rows[:5]):
            non_empty = sum(1 for c in row if c is not None and str(c).strip())
            if non_empty >= 3:
                header_row_idx = i
                break

        header_row = all_rows[header_row_idx]

        # Parse period columns from header
        periods: list[ParsedPeriod] = []
        col_indices: list[int] = []  # column indices that correspond to periods

        for col_idx, cell_val in enumerate(header_row):
            if col_idx == 0:
                continue  # label column
            if cell_val is None:
                continue
            period = _parse_period_label(str(cell_val))
            if period is not None:
                periods.append(period)
                col_indices.append(col_idx)

        if not periods:
            logger.warning("No period columns found in sheet %s", ws.title)
            return None

        # Parse data rows
        rows: dict[str, list[Optional[float]]] = {}
        unknown_labels: list[str] = []

        for row in all_rows[header_row_idx + 1:]:
            if not row or row[0] is None:
                continue
            raw_label = str(row[0]).strip()
            if not raw_label:
                continue

            canonical = normalize_fn(raw_label)
            if canonical is None:
                unknown_labels.append(raw_label)
                continue

            values: list[Optional[float]] = []
            for col_idx in col_indices:
                cell_val = row[col_idx] if col_idx < len(row) else None
                values.append(clean_numeric(cell_val))

            # Handle duplicate canonical labels (keep first, warn)
            if canonical in rows:
                logger.debug("Duplicate canonical label '%s' from '%s' — keeping first",
                             canonical, raw_label)
            else:
                rows[canonical] = values

        statement_type = self._detect_statement_type()
        return ParsedSheet(
            sheet_name=ws.title,
            statement_type=statement_type,
            periods=periods,
            rows=rows,
            unknown_labels=unknown_labels,
        )


def compute_file_hash(file_path: str | Path) -> str:
    """Standalone helper to compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
