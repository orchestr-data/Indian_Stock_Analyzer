"""Balance sheet quality analysis."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
from src.calculations.helpers import is_valid


@dataclass
class BalanceSheetQuality:
    debt_trend: list[tuple[int, Optional[float]]] = field(default_factory=list)
    cash_trend: list[tuple[int, Optional[float]]] = field(default_factory=list)
    net_debt_trend: list[tuple[int, Optional[float]]] = field(default_factory=list)
    equity_trend: list[tuple[int, Optional[float]]] = field(default_factory=list)
    cwip_trend: list[tuple[int, Optional[float]]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def analyze_balance_sheet(balance_df: pd.DataFrame) -> BalanceSheetQuality:
    result = BalanceSheetQuality()
    if balance_df.empty:
        return result

    df = balance_df.sort_values("fiscal_year")
    for _, row in df.iterrows():
        fy = int(row["fiscal_year"])
        borr = row.get("borrowings") if is_valid(row.get("borrowings")) else None
        cash = row.get("cash_and_equivalents") if is_valid(row.get("cash_and_equivalents")) else None
        equity = row.get("shareholders_equity") if is_valid(row.get("shareholders_equity")) else None
        cwip = row.get("cwip") if is_valid(row.get("cwip")) else None

        result.debt_trend.append((fy, borr))
        result.cash_trend.append((fy, cash))
        result.equity_trend.append((fy, equity))
        result.cwip_trend.append((fy, cwip))

        nd = None
        if borr is not None:
            nd = borr - (cash or 0.0)
        result.net_debt_trend.append((fy, nd))

    return result
