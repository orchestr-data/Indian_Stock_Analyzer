"""Ownership / shareholding analysis."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
from src.calculations.helpers import is_valid


@dataclass
class OwnershipSnapshot:
    period: str
    promoter_pct: Optional[float]
    promoter_pledge_pct: Optional[float]
    fii_pct: Optional[float]
    dii_pct: Optional[float]
    government_pct: Optional[float]
    public_pct: Optional[float]


def build_ownership_history(shareholding_df: pd.DataFrame) -> list[OwnershipSnapshot]:
    """Build time-ordered list of ownership snapshots."""
    if shareholding_df.empty:
        return []
    df = shareholding_df.sort_values("period_end_date")
    snapshots = []
    for _, row in df.iterrows():
        snapshots.append(OwnershipSnapshot(
            period=str(row["period_end_date"])[:10],
            promoter_pct=row.get("promoter_pct") if is_valid(row.get("promoter_pct")) else None,
            promoter_pledge_pct=row.get("promoter_pledge_pct") if is_valid(row.get("promoter_pledge_pct")) else None,
            fii_pct=row.get("fii_pct") if is_valid(row.get("fii_pct")) else None,
            dii_pct=row.get("dii_pct") if is_valid(row.get("dii_pct")) else None,
            government_pct=row.get("government_pct") if is_valid(row.get("government_pct")) else None,
            public_pct=row.get("public_pct") if is_valid(row.get("public_pct")) else None,
        ))
    return snapshots
