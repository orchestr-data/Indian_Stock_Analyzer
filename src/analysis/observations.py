"""Observation engine — generates structured factual observations.

Observations are factual statements about trends and metrics.
They are NOT investment recommendations.
No BUY/SELL/HOLD. No scores. No verdicts.
"""

from __future__ import annotations
import logging
from typing import Optional

import pandas as pd

from src.calculations.helpers import is_valid
from src.models.observations import Observation, ObservationCategory, ObservationSeverity
from src.sectors.loader import SectorLoader
from src.config import get_thresholds

logger = logging.getLogger(__name__)


class ObservationEngine:
    """Generates structured observations from financial data."""

    def __init__(self, sector: str = "DEFAULT") -> None:
        self._sector = sector
        self._loader = SectorLoader()
        self._rules = self._loader.get_observation_rules(sector)
        self._thresholds = get_thresholds()

    def generate_all(
        self,
        income_df: pd.DataFrame,
        balance_df: pd.DataFrame,
        cashflow_df: pd.DataFrame,
        shareholding_df: pd.DataFrame,
        market_data: Optional[dict] = None,
    ) -> list[Observation]:
        """Generate all observations for a company."""
        obs: list[Observation] = []

        obs.extend(self._revenue_trend(income_df))
        obs.extend(self._pat_trend(income_df))
        obs.extend(self._margin_trend(income_df))
        obs.extend(self._cash_conversion(income_df, cashflow_df))
        obs.extend(self._receivable_trend(income_df, balance_df))
        obs.extend(self._debt_trend(balance_df, income_df))
        obs.extend(self._promoter_observations(shareholding_df))
        obs.extend(self._share_dilution(income_df))
        obs.extend(self._other_income_check(income_df))
        if market_data:
            obs.extend(self._valuation_vs_history(income_df, market_data))

        return obs

    # ------------------------------------------------------------------
    # Individual observation generators
    # ------------------------------------------------------------------

    def _revenue_trend(self, df: pd.DataFrame) -> list[Observation]:
        obs = []
        if "revenue" not in df.columns or len(df) < 3:
            return obs

        df = df.sort_values("fiscal_year").reset_index(drop=True)
        revenues = df["revenue"].tolist()
        years = df["fiscal_year"].tolist()

        # Count consecutive growth
        consec = 0
        for i in range(len(revenues) - 1, 0, -1):
            if is_valid(revenues[i]) and is_valid(revenues[i - 1]):
                if revenues[i] > revenues[i - 1]:
                    consec += 1
                else:
                    break

        if consec >= 5:
            obs.append(Observation(
                category=ObservationCategory.POSITIVE,
                severity=ObservationSeverity.INFO,
                metric="revenue",
                period=f"FY{years[-consec - 1]} – FY{years[-1]}",
                message=f"Revenue has grown in each of the last {consec} reported years.",
                suggested_investigation="Verify the nature of growth: organic vs. acquisitions, pricing vs. volume.",
            ))
        elif consec >= 3:
            obs.append(Observation(
                category=ObservationCategory.POSITIVE,
                severity=ObservationSeverity.INFO,
                metric="revenue",
                period=f"FY{years[-consec - 1]} – FY{years[-1]}",
                message=f"Revenue has grown in each of the last {consec} reported years.",
            ))

        # Check if latest year declined
        if len(revenues) >= 2 and is_valid(revenues[-1]) and is_valid(revenues[-2]):
            if revenues[-1] < revenues[-2]:
                pct = abs(revenues[-1] - revenues[-2]) / abs(revenues[-2]) * 100
                obs.append(Observation(
                    category=ObservationCategory.WARNING,
                    severity=ObservationSeverity.MEDIUM,
                    metric="revenue",
                    period=f"FY{years[-2]} – FY{years[-1]}",
                    starting_value=revenues[-2],
                    ending_value=revenues[-1],
                    message=f"Revenue declined by {pct:.1f}% in the latest reported year.",
                    suggested_investigation="Investigate reason for revenue decline.",
                    unit="₹ Cr",
                ))

        return obs

    def _pat_trend(self, df: pd.DataFrame) -> list[Observation]:
        obs = []
        if "pat" not in df.columns or len(df) < 2:
            return obs
        df = df.sort_values("fiscal_year").reset_index(drop=True)
        pats = df["pat"].tolist()
        years = df["fiscal_year"].tolist()

        if len(pats) >= 2 and is_valid(pats[-1]) and is_valid(pats[-2]):
            if pats[-2] > 0 and pats[-1] < 0:
                obs.append(Observation(
                    category=ObservationCategory.WARNING,
                    severity=ObservationSeverity.HIGH,
                    metric="pat",
                    period=f"FY{years[-2]} – FY{years[-1]}",
                    starting_value=pats[-2],
                    ending_value=pats[-1],
                    message="Company swung to a net loss in the latest reported year.",
                    suggested_investigation="Review exceptional items, one-time charges, and operating drivers.",
                    unit="₹ Cr",
                ))
        return obs

    def _margin_trend(self, df: pd.DataFrame) -> list[Observation]:
        obs = []
        if "operating_profit" not in df.columns or "revenue" not in df.columns:
            return obs

        df = df.sort_values("fiscal_year").reset_index(drop=True)
        threshold = self._thresholds.get("operating_margin", {}).get("material_change_pp", 3.0)

        margins = []
        years = []
        for _, row in df.iterrows():
            rev = row.get("revenue")
            op = row.get("operating_profit")
            if is_valid(rev) and is_valid(op) and rev > 0:
                margins.append(op / rev * 100.0)
                years.append(int(row["fiscal_year"]))

        if len(margins) < 2:
            return obs

        # Latest vs 3 years ago
        if len(margins) >= 3:
            change = margins[-1] - margins[-4] if len(margins) >= 4 else margins[-1] - margins[-3]
            start_year = years[-4] if len(years) >= 4 else years[-3]
            if change < -threshold:
                obs.append(Observation(
                    category=ObservationCategory.WARNING,
                    severity=ObservationSeverity.MEDIUM,
                    metric="operating_margin",
                    period=f"FY{start_year} – FY{years[-1]}",
                    starting_value=round(margins[-4 if len(margins) >= 4 else -3], 1),
                    ending_value=round(margins[-1], 1),
                    message=f"Operating margin declined by {abs(change):.1f} percentage points.",
                    reason=f"Change of {change:.1f}pp exceeds material threshold of {threshold}pp",
                    suggested_investigation="Review cost structure, pricing power, and competitive dynamics.",
                    unit="%",
                ))
            elif change > threshold:
                obs.append(Observation(
                    category=ObservationCategory.POSITIVE,
                    severity=ObservationSeverity.INFO,
                    metric="operating_margin",
                    period=f"FY{start_year} – FY{years[-1]}",
                    starting_value=round(margins[-4 if len(margins) >= 4 else -3], 1),
                    ending_value=round(margins[-1], 1),
                    message=f"Operating margin expanded by {change:.1f} percentage points.",
                    unit="%",
                ))

        # Consecutive decline
        consec_dec = 0
        for i in range(len(margins) - 1, 0, -1):
            if margins[i] < margins[i - 1]:
                consec_dec += 1
            else:
                break
        if consec_dec >= 3:
            obs.append(Observation(
                category=ObservationCategory.WARNING,
                severity=ObservationSeverity.MEDIUM,
                metric="operating_margin",
                period=f"FY{years[-consec_dec - 1]} – FY{years[-1]}",
                starting_value=round(margins[-consec_dec - 1], 1),
                ending_value=round(margins[-1], 1),
                message=f"Operating margin has declined for {consec_dec} consecutive years.",
                suggested_investigation="Investigate whether margin compression is structural or cyclical.",
                unit="%",
            ))

        return obs

    def _cash_conversion(
        self, income_df: pd.DataFrame, cashflow_df: pd.DataFrame
    ) -> list[Observation]:
        obs = []
        rules = self._rules
        if not rules.get("check_cash_conversion", True):
            return obs

        if "pat" not in income_df.columns or "operating_cash_flow" not in cashflow_df.columns:
            return obs

        income_df = income_df.sort_values("fiscal_year")
        cashflow_df = cashflow_df.sort_values("fiscal_year")

        merged = income_df[["fiscal_year", "pat"]].merge(
            cashflow_df[["fiscal_year", "operating_cash_flow"]], on="fiscal_year", how="inner"
        )
        if merged.empty:
            return obs

        thresh = self._thresholds.get("cash_conversion", {})
        warn_below = thresh.get("warning_below", 0.7)
        consec_req = thresh.get("consecutive_years", 3)

        below_count = 0
        ratios = []
        for _, row in merged.iterrows():
            pat = row["pat"]
            cfo = row["operating_cash_flow"]
            if is_valid(pat) and is_valid(cfo) and pat > 0:
                ratio = cfo / pat
                ratios.append((int(row["fiscal_year"]), ratio))
                if ratio < warn_below:
                    below_count += 1

        # Consecutive recent years
        consec_below = 0
        for yr, ratio in reversed(ratios):
            if ratio < warn_below:
                consec_below += 1
            else:
                break

        if consec_below >= consec_req:
            first_yr = ratios[-consec_below][0]
            last_yr = ratios[-1][0]
            obs.append(Observation(
                category=ObservationCategory.INVESTIGATE,
                severity=ObservationSeverity.MEDIUM,
                metric="cfo_pat",
                period=f"FY{first_yr} – FY{last_yr}",
                message=f"CFO/PAT was below {warn_below} for {consec_below} consecutive years.",
                reason="Accounting profit may not be fully supported by operating cash flow.",
                suggested_investigation=(
                    "Review working capital changes, receivables, "
                    "and any non-cash income items. Compare PAT growth with CFO growth."
                ),
            ))
        elif consec_below >= 1 and ratios:
            yr, ratio = ratios[-1]
            if ratio < warn_below:
                obs.append(Observation(
                    category=ObservationCategory.NEUTRAL,
                    severity=ObservationSeverity.LOW,
                    metric="cfo_pat",
                    period=f"FY{yr}",
                    ending_value=round(ratio, 2),
                    message=f"CFO/PAT of {ratio:.2f} is below {warn_below} in the latest year.",
                    suggested_investigation="Monitor whether this is a one-year event or a trend.",
                    unit="x",
                ))

        # Also observe when conversion is strong
        if ratios and ratios[-1][1] >= 1.0:
            yr, ratio = ratios[-1]
            obs.append(Observation(
                category=ObservationCategory.POSITIVE,
                severity=ObservationSeverity.INFO,
                metric="cfo_pat",
                period=f"FY{yr}",
                ending_value=round(ratio, 2),
                message=f"CFO/PAT of {ratio:.2f} indicates strong cash conversion.",
                unit="x",
            ))

        return obs

    def _receivable_trend(
        self, income_df: pd.DataFrame, balance_df: pd.DataFrame
    ) -> list[Observation]:
        obs = []
        if not self._rules.get("check_receivable_growth", True):
            return obs
        if "revenue" not in income_df.columns or "receivables" not in balance_df.columns:
            return obs

        income_df = income_df.sort_values("fiscal_year")
        balance_df = balance_df.sort_values("fiscal_year")

        merged = income_df[["fiscal_year", "revenue"]].merge(
            balance_df[["fiscal_year", "receivables"]], on="fiscal_year", how="inner"
        )
        if len(merged) < 2:
            return obs

        days_series = []
        for _, row in merged.iterrows():
            rev = row["revenue"]
            rec = row["receivables"]
            if is_valid(rev) and is_valid(rec) and rev > 0:
                days_series.append((int(row["fiscal_year"]), rec / rev * 365.0))

        if len(days_series) < 2:
            return obs

        first_yr, first_days = days_series[0]
        last_yr, last_days = days_series[-1]
        warn_thresh = self._thresholds.get("receivable_days", {}).get("absolute_increase_warning", 15)

        if last_days - first_days > warn_thresh:
            obs.append(Observation(
                category=ObservationCategory.INVESTIGATE,
                severity=ObservationSeverity.MEDIUM,
                metric="receivable_days",
                period=f"FY{first_yr} – FY{last_yr}",
                starting_value=round(first_days, 0),
                ending_value=round(last_days, 0),
                message=f"Receivable days increased from {first_days:.0f} to {last_days:.0f} days.",
                reason="Rising receivable days relative to revenue may indicate collection issues.",
                suggested_investigation=(
                    "Understand whether the increase reflects business model changes, "
                    "customer mix, or collection difficulties."
                ),
                unit="days",
            ))

        return obs

    def _debt_trend(
        self, balance_df: pd.DataFrame, income_df: pd.DataFrame
    ) -> list[Observation]:
        obs = []
        if "borrowings" not in balance_df.columns:
            return obs
        balance_df = balance_df.sort_values("fiscal_year")
        borrow_vals = [(int(r["fiscal_year"]), r["borrowings"])
                       for _, r in balance_df.iterrows()
                       if is_valid(r.get("borrowings"))]

        if len(borrow_vals) < 2:
            return obs

        # Check if debt declined for multiple years
        consec_dec = 0
        for i in range(len(borrow_vals) - 1, 0, -1):
            if borrow_vals[i][1] < borrow_vals[i - 1][1]:
                consec_dec += 1
            else:
                break

        if consec_dec >= 3:
            obs.append(Observation(
                category=ObservationCategory.POSITIVE,
                severity=ObservationSeverity.INFO,
                metric="borrowings",
                period=f"FY{borrow_vals[-consec_dec - 1][0]} – FY{borrow_vals[-1][0]}",
                starting_value=borrow_vals[-consec_dec - 1][1],
                ending_value=borrow_vals[-1][1],
                message=f"Borrowings declined for {consec_dec} consecutive years.",
                unit="₹ Cr",
            ))

        # Debt-free or near zero
        if borrow_vals[-1][1] == 0 or (is_valid(borrow_vals[-1][1]) and borrow_vals[-1][1] < 50):
            obs.append(Observation(
                category=ObservationCategory.POSITIVE,
                severity=ObservationSeverity.INFO,
                metric="borrowings",
                period=f"FY{borrow_vals[-1][0]}",
                ending_value=borrow_vals[-1][1],
                message="Company has minimal or zero borrowings.",
                unit="₹ Cr",
            ))

        return obs

    def _promoter_observations(self, shareholding_df: pd.DataFrame) -> list[Observation]:
        obs = []
        if shareholding_df.empty or "promoter_pct" not in shareholding_df.columns:
            return obs

        df = shareholding_df.sort_values("period_end_date").reset_index(drop=True)
        promoters = [(str(r["period_end_date"]), r["promoter_pct"])
                     for _, r in df.iterrows()
                     if is_valid(r.get("promoter_pct"))]

        if len(promoters) >= 2:
            first_dt, first_pct = promoters[0]
            last_dt, last_pct = promoters[-1]
            change = last_pct - first_pct

            thresh = self._thresholds.get("promoter_holding", {}).get("material_change_pct", 2.0)
            if abs(change) >= thresh:
                cat = ObservationCategory.WARNING if change < 0 else ObservationCategory.NEUTRAL
                obs.append(Observation(
                    category=cat,
                    severity=ObservationSeverity.LOW,
                    metric="promoter_holding",
                    period=f"{first_dt} – {last_dt}",
                    starting_value=round(first_pct, 1),
                    ending_value=round(last_pct, 1),
                    message=f"Promoter holding {'declined' if change < 0 else 'increased'} "
                            f"from {first_pct:.1f}% to {last_pct:.1f}%.",
                    suggested_investigation=(
                        "Investigate whether this is due to secondary sales, "
                        "dilution, or reclassification." if change < 0 else None
                    ),
                    unit="%",
                ))

        # Pledge check
        if "promoter_pledge_pct" in df.columns:
            pledges = [(str(r["period_end_date"]), r["promoter_pledge_pct"])
                       for _, r in df.iterrows()
                       if is_valid(r.get("promoter_pledge_pct")) and r["promoter_pledge_pct"] > 0]

            if pledges:
                last_dt, last_pledge = pledges[-1]
                obs.append(Observation(
                    category=ObservationCategory.INVESTIGATE,
                    severity=ObservationSeverity.MEDIUM,
                    metric="promoter_pledge",
                    period=last_dt,
                    ending_value=round(last_pledge, 1),
                    message=f"Promoter shares are pledged ({last_pledge:.1f}% of promoter holding).",
                    reason="Pledge creates forced-sale risk if share price falls.",
                    suggested_investigation=(
                        "Understand the purpose of the pledge and monitor for changes."
                    ),
                    unit="%",
                ))

        return obs

    def _share_dilution(self, income_df: pd.DataFrame) -> list[Observation]:
        obs = []
        if "weighted_avg_shares" not in income_df.columns or len(income_df) < 3:
            return obs

        df = income_df.sort_values("fiscal_year")
        shares = [(int(r["fiscal_year"]), r["weighted_avg_shares"])
                  for _, r in df.iterrows()
                  if is_valid(r.get("weighted_avg_shares"))]

        if len(shares) < 2:
            return obs

        first_yr, first_shares = shares[0]
        last_yr, last_shares = shares[-1]
        years_elapsed = last_yr - first_yr
        if years_elapsed <= 0:
            return obs

        pct_change = (last_shares - first_shares) / first_shares * 100.0
        warn_thresh = self._thresholds.get("share_dilution", {}).get("warning_pct_5y", 10.0)

        if pct_change > warn_thresh:
            obs.append(Observation(
                category=ObservationCategory.INVESTIGATE,
                severity=ObservationSeverity.LOW,
                metric="share_count",
                period=f"FY{first_yr} – FY{last_yr}",
                starting_value=round(first_shares, 2),
                ending_value=round(last_shares, 2),
                message=f"Share count increased approximately {pct_change:.1f}% over {years_elapsed} years.",
                reason="Dilution reduces per-share value for existing shareholders.",
                suggested_investigation=(
                    "Investigate the source: ESOPs, QIP, rights issue, "
                    "preferential allotment, or acquisitions."
                ),
                unit="Cr shares",
            ))

        return obs

    def _other_income_check(self, income_df: pd.DataFrame) -> list[Observation]:
        obs = []
        if "other_income" not in income_df.columns or "pbt" not in income_df.columns:
            return obs

        df = income_df.sort_values("fiscal_year")
        thresh = self._thresholds.get("other_income_pbt", {}).get("flag_above_pct", 25.0)

        for _, row in df.tail(1).iterrows():
            other = row.get("other_income")
            pbt = row.get("pbt")
            if is_valid(other) and is_valid(pbt) and pbt > 0:
                pct = other / pbt * 100.0
                if pct > thresh:
                    obs.append(Observation(
                        category=ObservationCategory.INVESTIGATE,
                        severity=ObservationSeverity.LOW,
                        metric="other_income_pbt_pct",
                        period=f"FY{int(row['fiscal_year'])}",
                        ending_value=round(pct, 1),
                        message=f"Other income represented {pct:.1f}% of PBT in the latest year.",
                        reason="High other income dependency may indicate non-recurring earnings.",
                        suggested_investigation=(
                            "Identify the source: interest income, asset sales, "
                            "forex gains, or one-time items."
                        ),
                        unit="%",
                    ))

        return obs

    def _valuation_vs_history(
        self, income_df: pd.DataFrame, market_data: dict
    ) -> list[Observation]:
        obs = []
        current_pe = market_data.get("pe")
        if not is_valid(current_pe):
            return obs

        # Would need historical PE data — placeholder
        return obs
