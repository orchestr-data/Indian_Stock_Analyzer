"""Financial calculation engine — pure functions, no side effects."""

from src.calculations.helpers import safe_div, safe_pct, is_valid
from src.calculations.growth import (
    cagr, eps_cagr, revenue_cagr, pat_cagr, ebitda_cagr, fcf_cagr, book_value_cagr,
)
from src.calculations.profitability import (
    operating_margin, ebitda_margin, ebit_margin, net_margin,
    roe, roce, roa,
)
from src.calculations.leverage import (
    debt_equity, net_debt, net_debt_ebitda, interest_coverage,
    debt_to_assets,
)
from src.calculations.cashflow import (
    free_cash_flow, cfo_pat_ratio, fcf_pat_ratio, fcf_margin, fcf_yield,
    capex_revenue_pct,
)
from src.calculations.valuation import (
    pe_ratio, pb_ratio, peg_ratio, enterprise_value,
    ev_ebitda, ev_ebit, earnings_yield, dividend_yield_calc,
    book_value_per_share, eps_calc,
)
from src.calculations.efficiency import (
    receivable_days, inventory_days, payable_days,
    cash_conversion_cycle, asset_turnover, working_capital_days,
)

__all__ = [
    "safe_div", "safe_pct", "is_valid",
    "cagr", "eps_cagr", "revenue_cagr", "pat_cagr", "ebitda_cagr", "fcf_cagr", "book_value_cagr",
    "operating_margin", "ebitda_margin", "ebit_margin", "net_margin", "roe", "roce", "roa",
    "debt_equity", "net_debt", "net_debt_ebitda", "interest_coverage", "debt_to_assets",
    "free_cash_flow", "cfo_pat_ratio", "fcf_pat_ratio", "fcf_margin", "fcf_yield",
    "capex_revenue_pct",
    "pe_ratio", "pb_ratio", "peg_ratio", "enterprise_value", "ev_ebitda", "ev_ebit",
    "earnings_yield", "dividend_yield_calc", "book_value_per_share", "eps_calc",
    "receivable_days", "inventory_days", "payable_days", "cash_conversion_cycle",
    "asset_turnover", "working_capital_days",
]
