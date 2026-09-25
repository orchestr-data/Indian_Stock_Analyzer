"""Normalizer — maps Screener.in labels to canonical internal field names.

Only this module and the parser understand Screener-specific labels.
The rest of the application uses canonical names only.
"""

from __future__ import annotations
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Canonical field name mappings — Screener label → canonical name
# ---------------------------------------------------------------------------

# Income statement labels
_INCOME_MAP: dict[str, str] = {
    # Revenue
    "sales": "revenue",
    "revenue": "revenue",
    "net sales": "revenue",
    "net revenue": "revenue",
    "turnover": "revenue",
    "income from operations": "revenue",
    "total income from operations": "revenue",
    "sales +": "revenue",
    "revenue from operations": "revenue",

    # Expenses
    "expenses": "expenses",
    "total expenses": "expenses",
    "expenditure": "expenses",
    "total expenditure": "expenses",

    # Operating profit
    "operating profit": "operating_profit",
    "ebitda": "ebitda",
    "pbdit": "ebitda",
    "profit before depreciation interest and tax": "ebitda",
    "operating income": "operating_profit",

    # Margins
    "opm %": "operating_margin_pct",
    "opm": "operating_margin_pct",
    "operating profit margin": "operating_margin_pct",

    # Other income
    "other income": "other_income",
    "non-operating income": "other_income",
    "other non-operating income": "other_income",

    # Interest
    "interest": "interest",
    "finance costs": "interest",
    "finance cost": "interest",
    "interest expense": "interest",
    "borrowing costs": "interest",

    # Depreciation
    "depreciation": "depreciation",
    "depreciation & amortisation": "depreciation",
    "depreciation and amortisation": "depreciation",
    "d&a": "depreciation",
    "dep": "depreciation",

    # PBT
    "profit before tax": "pbt",
    "pbt": "pbt",
    "profit/(loss) before tax": "pbt",
    "profit before exceptional items and tax": "pbt",

    # Tax
    "tax %": "tax_pct",
    "tax": "tax",
    "income tax": "tax",

    # PAT
    "net profit": "pat",
    "profit after tax": "pat",
    "pat": "pat",
    "net income": "pat",
    "profit for the year": "pat",
    "net profit / loss": "pat",
    "profit/(loss) after tax": "pat",

    # EPS
    "eps in rs": "basic_eps",
    "eps": "basic_eps",
    "basic eps": "basic_eps",
    "diluted eps": "diluted_eps",
    "earnings per share": "basic_eps",
    "diluted earnings per share": "diluted_eps",

    # Shares
    "shares outstanding": "weighted_avg_shares",
    "no. of shares": "weighted_avg_shares",
    "equity shares": "equity_capital",

    # Dividend
    "dividend payout %": "dividend_payout_pct",
    "dividend payout": "dividend_payout_pct",
}

# Balance sheet labels
_BALANCE_MAP: dict[str, str] = {
    # Equity
    "share capital": "equity_capital",
    "equity capital": "equity_capital",
    "paid-up capital": "equity_capital",
    "paid up share capital": "equity_capital",

    "reserves": "reserves",
    "reserves & surplus": "reserves",
    "reserves and surplus": "reserves",
    "other equity": "reserves",

    "shareholders equity": "shareholders_equity",
    "shareholders' equity": "shareholders_equity",
    "total equity": "shareholders_equity",
    "net worth": "shareholders_equity",
    "equity": "shareholders_equity",

    # Borrowings
    "borrowings": "borrowings",
    "total borrowings": "borrowings",
    "debt": "borrowings",
    "total debt": "borrowings",
    "long term borrowings": "long_term_debt",
    "short term borrowings": "short_term_debt",
    "current portion of long-term debt": "short_term_debt",

    # Liabilities
    "other liabilities": "other_current_liabilities",
    "total liabilities": "total_liabilities",
    "current liabilities": "other_current_liabilities",
    "trade payables": "payables",
    "payables": "payables",
    "creditors": "payables",
    "accounts payable": "payables",

    # Assets
    "fixed assets": "fixed_assets",
    "net fixed assets": "fixed_assets",
    "property, plant and equipment": "fixed_assets",
    "tangible assets": "fixed_assets",

    "cwip": "cwip",
    "capital work in progress": "cwip",
    "capital work-in-progress": "cwip",

    "investments": "investments",
    "long term investments": "investments",
    "other investments": "investments",

    "total assets": "total_assets",
    "net assets": "total_assets",

    "cash": "cash_and_equivalents",
    "cash & equivalents": "cash_and_equivalents",
    "cash and cash equivalents": "cash_and_equivalents",
    "cash and bank balances": "cash_and_equivalents",

    "receivables": "receivables",
    "debtors": "receivables",
    "trade receivables": "receivables",
    "sundry debtors": "receivables",
    "accounts receivable": "receivables",

    "inventory": "inventory",
    "inventories": "inventory",
    "stock in trade": "inventory",

    "other assets": "other_assets",
    "other current assets": "other_current_assets",
    "loans and advances": "other_current_assets",
}

# Cash flow labels
_CASHFLOW_MAP: dict[str, str] = {
    "cash from operating activity": "operating_cash_flow",
    "cash from operations": "operating_cash_flow",
    "operating activities": "operating_cash_flow",
    "net cash from operating activities": "operating_cash_flow",
    "cash flow from operations": "operating_cash_flow",
    "cfo": "operating_cash_flow",

    "cash from investing activity": "investing_cash_flow",
    "investing activities": "investing_cash_flow",
    "net cash from investing activities": "investing_cash_flow",
    "cash flow from investing": "investing_cash_flow",

    "cash from financing activity": "financing_cash_flow",
    "financing activities": "financing_cash_flow",
    "net cash from financing activities": "financing_cash_flow",
    "cash flow from financing": "financing_cash_flow",

    "capex": "capital_expenditure",
    "capital expenditure": "capital_expenditure",
    "purchase of fixed assets": "capital_expenditure",
    "additions to fixed assets": "capital_expenditure",
    "purchase of property, plant and equipment": "capital_expenditure",

    "dividends paid": "dividends_paid",
    "dividend paid": "dividends_paid",
    "dividend payout": "dividends_paid",
}

# Shareholding labels
_SHAREHOLDING_MAP: dict[str, str] = {
    "promoters": "promoter_pct",
    "promoter & promoter group": "promoter_pct",
    "promoter and promoter group": "promoter_pct",
    "promoter": "promoter_pct",

    "pledge": "promoter_pledge_pct",
    "pledged": "promoter_pledge_pct",
    "promoter pledged shares %": "promoter_pledge_pct",
    "% of promoter shares pledged": "promoter_pledge_pct",

    "fiis": "fii_pct",
    "fii": "fii_pct",
    "foreign institutional investors": "fii_pct",
    "foreign portfolio investors": "fii_pct",
    "fpi": "fii_pct",

    "diis": "dii_pct",
    "dii": "dii_pct",
    "domestic institutional investors": "dii_pct",

    "government": "government_pct",
    "central government": "government_pct",

    "public": "public_pct",
    "public & others": "public_pct",
    "others": "public_pct",
}


def _clean_label(label: str) -> str:
    """Normalise a raw label for lookup."""
    label = str(label).strip().lower()
    label = re.sub(r"\s+", " ", label)
    label = label.rstrip(":")
    return label


def normalize_income_label(raw_label: str) -> Optional[str]:
    """Map a raw income statement label to the canonical field name."""
    cleaned = _clean_label(raw_label)
    return _INCOME_MAP.get(cleaned)


def normalize_balance_label(raw_label: str) -> Optional[str]:
    cleaned = _clean_label(raw_label)
    return _BALANCE_MAP.get(cleaned)


def normalize_cashflow_label(raw_label: str) -> Optional[str]:
    cleaned = _clean_label(raw_label)
    return _CASHFLOW_MAP.get(cleaned)


def normalize_shareholding_label(raw_label: str) -> Optional[str]:
    cleaned = _clean_label(raw_label)
    return _SHAREHOLDING_MAP.get(cleaned)


def clean_numeric(raw: object) -> Optional[float]:
    """Convert a raw cell value to float, or None.

    Handles:
    - commas: "1,234.56" → 1234.56
    - blanks / "--" / "N/A" → None
    - parentheses for negatives: "(100)" → -100
    - % suffix (stripped — caller decides whether to divide by 100)
    - ₹ prefix
    - "Cr", "crore" suffix (stripped — values assumed already in crore)
    - trailing footnote markers like "*"
    """
    if raw is None:
        return None

    s = str(raw).strip()

    # Explicit missing markers
    if s in ("", "--", "-", "N/A", "NA", "n/a", "—", "Nil", "nil"):
        return None

    # Strip ₹, commas, footnote chars; normalise unicode minus / dashes
    s = s.replace("₹", "").replace(",", "").replace("*", "").strip()
    s = s.replace("−", "-").replace("–", "-")

    # Units. Values are stored in crore, so lakh crore must be scaled.
    multiplier = 1.0
    lower = s.lower()
    for unit, mult in (("lakh crore", 1e5), ("lakh cr", 1e5), ("crore", 1.0), ("cr", 1.0)):
        if lower.endswith(unit):
            s = s[: -len(unit)].strip()
            multiplier = mult
            break

    # Percentage: strip %, don't convert to fraction here
    s = s.rstrip("%").strip()

    # Parentheses = negative
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]

    try:
        return float(s) * multiplier
    except (ValueError, TypeError):
        logger.debug("Cannot parse numeric value: %r", raw)
        return None
