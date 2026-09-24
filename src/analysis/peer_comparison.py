"""Peer comparison engine — compares multiple companies on key metrics."""

from __future__ import annotations
from typing import Optional

import pandas as pd

from src.database.repository import Repository
from src.calculations import (
    operating_margin, roe, roce, debt_equity, cfo_pat_ratio,
    free_cash_flow, receivable_days,
)


class PeerComparisonEngine:
    """Builds a comparison table across user-selected peer companies."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def build_comparison(
        self,
        company_ids: list[int],
        statement_type: str = "Consolidated",
    ) -> pd.DataFrame:
        """Return a DataFrame with one row per company and columns for each metric."""
        rows = []
        for company_id in company_ids:
            company = self._repo.get_company_by_id(company_id)
            if company is None:
                continue

            income = self._repo.get_annual_income(company_id, statement_type)
            balance = self._repo.get_balance_sheet(company_id, statement_type)
            cashflow = self._repo.get_cash_flow(company_id, statement_type)

            row = {"company_id": company_id, "company_name": company["company_name"],
                   "ticker": company["ticker"], "sector": company["sector"]}

            if not income.empty:
                latest = income.sort_values("fiscal_year").iloc[-1]
                latest_yr = int(latest["fiscal_year"])
                prev = income.sort_values("fiscal_year").iloc[-2] if len(income) >= 2 else None

                rev = latest.get("revenue")
                op = latest.get("operating_profit")
                pat = latest.get("pat")
                ebit = latest.get("ebit")

                row["latest_fy"] = latest_yr
                row["revenue_cr"] = rev
                row["pat_cr"] = pat

                om = operating_margin(op, rev)
                row["operating_margin_pct"] = om.value

                if not balance.empty:
                    bl = balance.sort_values("fiscal_year").iloc[-1]
                    eq = bl.get("shareholders_equity")
                    borr = bl.get("borrowings")
                    cash = bl.get("cash_and_equivalents")
                    prev_eq = prev_bl = None
                    if len(balance) >= 2:
                        prev_bl = balance.sort_values("fiscal_year").iloc[-2]
                        prev_eq = prev_bl.get("shareholders_equity")

                    r = roe(pat, eq, prev_eq)
                    row["roe_pct"] = r.value

                    prev_borr = prev_bl.get("borrowings") if prev_bl is not None else None
                    prev_cash = prev_bl.get("cash_and_equivalents") if prev_bl is not None else None
                    prev_eq2 = prev_eq

                    rc = roce(ebit, eq, borr, cash, prev_eq2, prev_borr, prev_cash)
                    row["roce_pct"] = rc.value

                    de = debt_equity(borr, eq)
                    row["debt_equity"] = de.value

                if not cashflow.empty:
                    cf = cashflow.sort_values("fiscal_year").iloc[-1]
                    cfo = cf.get("operating_cash_flow")
                    capex = cf.get("capital_expenditure")
                    fcf = free_cash_flow(cfo, capex)
                    row["fcf_cr"] = fcf.value
                    ratio = cfo_pat_ratio(cfo, pat)
                    row["cfo_pat"] = ratio.value

            rows.append(row)

        return pd.DataFrame(rows)
