"""Financial statement data models — all values in ₹ Crore."""

from __future__ import annotations
from typing import Optional
from datetime import date
from pydantic import BaseModel


class AnnualIncome(BaseModel):
    """Annual Profit & Loss statement data."""

    company_id: int
    statement_type: str  # "Consolidated" | "Standalone"
    fiscal_year: int

    revenue: Optional[float] = None
    expenses: Optional[float] = None
    operating_profit: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    other_income: Optional[float] = None
    interest: Optional[float] = None
    depreciation: Optional[float] = None
    amortization: Optional[float] = None
    pbt: Optional[float] = None
    tax: Optional[float] = None
    pat: Optional[float] = None
    minority_interest: Optional[float] = None
    pat_attributable: Optional[float] = None
    basic_eps: Optional[float] = None
    diluted_eps: Optional[float] = None
    weighted_avg_shares: Optional[float] = None  # in crores


class QuarterlyIncome(BaseModel):
    """Quarterly Profit & Loss statement data."""

    company_id: int
    statement_type: str
    fiscal_year: int
    fiscal_quarter: int  # 1-4
    period_end_date: Optional[date] = None

    revenue: Optional[float] = None
    expenses: Optional[float] = None
    operating_profit: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    other_income: Optional[float] = None
    interest: Optional[float] = None
    depreciation: Optional[float] = None
    pbt: Optional[float] = None
    tax: Optional[float] = None
    pat: Optional[float] = None
    eps: Optional[float] = None
    operating_margin: Optional[float] = None  # %


class BalanceSheet(BaseModel):
    """Balance Sheet data — all values ₹ Crore."""

    company_id: int
    statement_type: str
    fiscal_year: int

    # Equity & Liabilities
    equity_capital: Optional[float] = None
    reserves: Optional[float] = None
    shareholders_equity: Optional[float] = None
    borrowings: Optional[float] = None
    short_term_debt: Optional[float] = None
    long_term_debt: Optional[float] = None
    other_current_liabilities: Optional[float] = None
    total_liabilities: Optional[float] = None

    # Assets
    cash_and_equivalents: Optional[float] = None
    receivables: Optional[float] = None
    inventory: Optional[float] = None
    payables: Optional[float] = None
    other_current_assets: Optional[float] = None
    fixed_assets: Optional[float] = None
    cwip: Optional[float] = None
    investments: Optional[float] = None
    other_assets: Optional[float] = None
    total_assets: Optional[float] = None


class CashFlow(BaseModel):
    """Cash Flow statement data — all values ₹ Crore."""

    company_id: int
    statement_type: str
    fiscal_year: int

    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    capital_expenditure: Optional[float] = None
    free_cash_flow: Optional[float] = None  # calculated or reported
    dividends_paid: Optional[float] = None
    debt_raised: Optional[float] = None
    debt_repaid: Optional[float] = None
    share_issuance: Optional[float] = None
    buybacks: Optional[float] = None


class Shareholding(BaseModel):
    """Shareholding pattern data — all values in %."""

    company_id: int
    period_end_date: date
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None

    promoter_pct: Optional[float] = None
    promoter_pledge_pct: Optional[float] = None
    fii_pct: Optional[float] = None
    dii_pct: Optional[float] = None
    government_pct: Optional[float] = None
    public_pct: Optional[float] = None
    other_pct: Optional[float] = None


class MarketData(BaseModel):
    """Market / valuation data at a point in time."""

    company_id: int
    date: date

    price: Optional[float] = None
    market_cap: Optional[float] = None  # ₹ Crore
    shares_outstanding: Optional[float] = None  # Crore shares
    pe: Optional[float] = None
    pb: Optional[float] = None
    enterprise_value: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ev_ebit: Optional[float] = None
    dividend_yield: Optional[float] = None


class CorporateAction(BaseModel):
    """Corporate action event."""

    company_id: int
    action_date: date
    action_type: str  # stock_split, bonus, rights_issue, buyback, dividend, etc.
    description: str
    ratio_or_amount: Optional[str] = None
