"""Database repository — all reads and writes through this layer."""

from __future__ import annotations
import logging
from typing import Optional

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


class Repository:
    """Thin data access layer over DuckDB.

    All SQL lives here. Business logic does not.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Companies
    # ------------------------------------------------------------------

    def upsert_company(
        self,
        ticker: str,
        company_name: str,
        nse_symbol: Optional[str] = None,
        bse_code: Optional[str] = None,
        isin: Optional[str] = None,
        sector: str = "DEFAULT",
        industry: Optional[str] = None,
    ) -> int:
        """Insert or update a company record, returning company_id."""
        existing = self._conn.execute(
            "SELECT company_id FROM companies WHERE ticker = ?", [ticker]
        ).fetchone()

        if existing:
            company_id = existing[0]
            self._conn.execute(
                """
                UPDATE companies SET
                    company_name = ?, nse_symbol = ?, bse_code = ?,
                    isin = ?, sector = ?, industry = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE company_id = ?
                """,
                [company_name, nse_symbol, bse_code, isin, sector, industry, company_id],
            )
        else:
            company_id = self._conn.execute(
                "SELECT nextval('seq_companies')"
            ).fetchone()[0]
            self._conn.execute(
                """
                INSERT INTO companies
                    (company_id, ticker, company_name, nse_symbol, bse_code,
                     isin, sector, industry, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                [company_id, ticker, company_name, nse_symbol, bse_code,
                 isin, sector, industry],
            )
        return company_id

    def get_company_by_ticker(self, ticker: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM companies WHERE ticker = ?", [ticker]
        ).fetchdf()
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def get_company_by_id(self, company_id: int) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM companies WHERE company_id = ?", [company_id]
        ).fetchdf()
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def update_company_sector(self, company_id: int, sector: str) -> None:
        """Override the sector for a company (persisted to DB)."""
        self._conn.execute(
            "UPDATE companies SET sector = ?, last_updated = CURRENT_TIMESTAMP WHERE company_id = ?",
            [sector, company_id],
        )

    def list_companies(self) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT company_id, ticker, company_name, sector, last_updated "
            "FROM companies ORDER BY company_name"
        ).fetchdf()

    def search_companies(self, query: str) -> pd.DataFrame:
        q = f"%{query.upper()}%"
        return self._conn.execute(
            """
            SELECT company_id, ticker, company_name, sector
            FROM companies
            WHERE UPPER(ticker) LIKE ? OR UPPER(company_name) LIKE ?
            ORDER BY company_name
            """,
            [q, q],
        ).fetchdf()

    # ------------------------------------------------------------------
    # Source imports
    # ------------------------------------------------------------------

    def log_import(
        self,
        company_id: int,
        source_type: str,
        source_name: str,
        source_file: str,
        file_hash: str,
        statement_type: str,
        status: str,
        warnings: Optional[list[str]] = None,
    ) -> int:
        import_id = self._conn.execute(
            "SELECT nextval('seq_source_imports')"
        ).fetchone()[0]
        warnings_str = "; ".join(warnings) if warnings else None
        self._conn.execute(
            """
            INSERT INTO source_imports
                (import_id, company_id, source_type, source_name, source_file,
                 file_hash, statement_type, import_timestamp, status, warnings)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """,
            [import_id, company_id, source_type, source_name, source_file,
             file_hash, statement_type, status, warnings_str],
        )
        return import_id

    def file_already_imported(self, file_hash: str) -> bool:
        row = self._conn.execute(
            "SELECT import_id FROM source_imports WHERE file_hash = ? AND status = 'success'",
            [file_hash],
        ).fetchone()
        return row is not None

    def get_import_history(self, company_id: int) -> pd.DataFrame:
        return self._conn.execute(
            """
            SELECT import_id, source_type, source_file, statement_type,
                   import_timestamp, status, warnings
            FROM source_imports WHERE company_id = ?
            ORDER BY import_timestamp DESC
            """,
            [company_id],
        ).fetchdf()

    # ------------------------------------------------------------------
    # Annual Income
    # ------------------------------------------------------------------

    def upsert_annual_income(self, company_id: int, statement_type: str,
                              fiscal_year: int, data: dict) -> None:
        self._conn.execute(
            """
            INSERT INTO annual_income
                (id, company_id, statement_type, fiscal_year,
                 revenue, expenses, operating_profit, ebitda, ebit,
                 other_income, interest, depreciation, amortization,
                 pbt, tax, pat, minority_interest, pat_attributable,
                 basic_eps, diluted_eps, weighted_avg_shares)
            VALUES (nextval('seq_annual_income'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (company_id, statement_type, fiscal_year) DO UPDATE SET
                revenue = EXCLUDED.revenue,
                expenses = EXCLUDED.expenses,
                operating_profit = EXCLUDED.operating_profit,
                ebitda = EXCLUDED.ebitda,
                ebit = EXCLUDED.ebit,
                other_income = EXCLUDED.other_income,
                interest = EXCLUDED.interest,
                depreciation = EXCLUDED.depreciation,
                amortization = EXCLUDED.amortization,
                pbt = EXCLUDED.pbt,
                tax = EXCLUDED.tax,
                pat = EXCLUDED.pat,
                minority_interest = EXCLUDED.minority_interest,
                pat_attributable = EXCLUDED.pat_attributable,
                basic_eps = EXCLUDED.basic_eps,
                diluted_eps = EXCLUDED.diluted_eps,
                weighted_avg_shares = EXCLUDED.weighted_avg_shares
            """,
            [
                company_id, statement_type, fiscal_year,
                data.get("revenue"), data.get("expenses"), data.get("operating_profit"),
                data.get("ebitda"), data.get("ebit"), data.get("other_income"),
                data.get("interest"), data.get("depreciation"), data.get("amortization"),
                data.get("pbt"), data.get("tax"), data.get("pat"),
                data.get("minority_interest"), data.get("pat_attributable"),
                data.get("basic_eps"), data.get("diluted_eps"), data.get("weighted_avg_shares"),
            ],
        )

    def get_annual_income(self, company_id: int, statement_type: str) -> pd.DataFrame:
        return self._conn.execute(
            """
            SELECT * FROM annual_income
            WHERE company_id = ? AND statement_type = ?
            ORDER BY fiscal_year
            """,
            [company_id, statement_type],
        ).fetchdf()

    # ------------------------------------------------------------------
    # Quarterly Income
    # ------------------------------------------------------------------

    def upsert_quarterly_income(self, company_id: int, statement_type: str,
                                 fiscal_year: int, fiscal_quarter: int, data: dict) -> None:
        self._conn.execute(
            """
            INSERT INTO quarterly_income
                (id, company_id, statement_type, fiscal_year, fiscal_quarter, period_end_date,
                 revenue, expenses, operating_profit, ebitda, ebit, other_income,
                 interest, depreciation, pbt, tax, pat, eps, operating_margin)
            VALUES (nextval('seq_quarterly_income'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (company_id, statement_type, fiscal_year, fiscal_quarter) DO UPDATE SET
                revenue = EXCLUDED.revenue,
                expenses = EXCLUDED.expenses,
                operating_profit = EXCLUDED.operating_profit,
                pbt = EXCLUDED.pbt,
                tax = EXCLUDED.tax,
                pat = EXCLUDED.pat,
                eps = EXCLUDED.eps,
                operating_margin = EXCLUDED.operating_margin
            """,
            [
                company_id, statement_type, fiscal_year, fiscal_quarter,
                data.get("period_end_date"),
                data.get("revenue"), data.get("expenses"), data.get("operating_profit"),
                data.get("ebitda"), data.get("ebit"), data.get("other_income"),
                data.get("interest"), data.get("depreciation"),
                data.get("pbt"), data.get("tax"), data.get("pat"),
                data.get("eps"), data.get("operating_margin"),
            ],
        )

    def get_quarterly_income(self, company_id: int, statement_type: str) -> pd.DataFrame:
        return self._conn.execute(
            """
            SELECT * FROM quarterly_income
            WHERE company_id = ? AND statement_type = ?
            ORDER BY fiscal_year, fiscal_quarter
            """,
            [company_id, statement_type],
        ).fetchdf()

    # ------------------------------------------------------------------
    # Balance Sheet
    # ------------------------------------------------------------------

    def upsert_balance_sheet(self, company_id: int, statement_type: str,
                              fiscal_year: int, data: dict) -> None:
        self._conn.execute(
            """
            INSERT INTO balance_sheet
                (id, company_id, statement_type, fiscal_year,
                 equity_capital, reserves, shareholders_equity,
                 borrowings, short_term_debt, long_term_debt, other_current_liabilities,
                 total_liabilities, cash_and_equivalents, receivables, inventory,
                 payables, other_current_assets, fixed_assets, cwip,
                 investments, other_assets, total_assets)
            VALUES (nextval('seq_balance_sheet'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (company_id, statement_type, fiscal_year) DO UPDATE SET
                equity_capital = EXCLUDED.equity_capital,
                reserves = EXCLUDED.reserves,
                shareholders_equity = EXCLUDED.shareholders_equity,
                borrowings = EXCLUDED.borrowings,
                short_term_debt = EXCLUDED.short_term_debt,
                long_term_debt = EXCLUDED.long_term_debt,
                cash_and_equivalents = EXCLUDED.cash_and_equivalents,
                receivables = EXCLUDED.receivables,
                inventory = EXCLUDED.inventory,
                payables = EXCLUDED.payables,
                fixed_assets = EXCLUDED.fixed_assets,
                cwip = EXCLUDED.cwip,
                investments = EXCLUDED.investments,
                total_assets = EXCLUDED.total_assets,
                total_liabilities = EXCLUDED.total_liabilities
            """,
            [
                company_id, statement_type, fiscal_year,
                data.get("equity_capital"), data.get("reserves"), data.get("shareholders_equity"),
                data.get("borrowings"), data.get("short_term_debt"), data.get("long_term_debt"),
                data.get("other_current_liabilities"), data.get("total_liabilities"),
                data.get("cash_and_equivalents"), data.get("receivables"), data.get("inventory"),
                data.get("payables"), data.get("other_current_assets"), data.get("fixed_assets"),
                data.get("cwip"), data.get("investments"), data.get("other_assets"),
                data.get("total_assets"),
            ],
        )

    def get_balance_sheet(self, company_id: int, statement_type: str) -> pd.DataFrame:
        return self._conn.execute(
            """
            SELECT * FROM balance_sheet
            WHERE company_id = ? AND statement_type = ?
            ORDER BY fiscal_year
            """,
            [company_id, statement_type],
        ).fetchdf()

    # ------------------------------------------------------------------
    # Cash Flow
    # ------------------------------------------------------------------

    def upsert_cash_flow(self, company_id: int, statement_type: str,
                          fiscal_year: int, data: dict) -> None:
        self._conn.execute(
            """
            INSERT INTO cash_flow
                (id, company_id, statement_type, fiscal_year,
                 operating_cash_flow, investing_cash_flow, financing_cash_flow,
                 capital_expenditure, free_cash_flow, dividends_paid,
                 debt_raised, debt_repaid, share_issuance, buybacks)
            VALUES (nextval('seq_cash_flow'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (company_id, statement_type, fiscal_year) DO UPDATE SET
                operating_cash_flow = EXCLUDED.operating_cash_flow,
                investing_cash_flow = EXCLUDED.investing_cash_flow,
                financing_cash_flow = EXCLUDED.financing_cash_flow,
                capital_expenditure = EXCLUDED.capital_expenditure,
                free_cash_flow = EXCLUDED.free_cash_flow,
                dividends_paid = EXCLUDED.dividends_paid,
                debt_raised = EXCLUDED.debt_raised,
                debt_repaid = EXCLUDED.debt_repaid,
                share_issuance = EXCLUDED.share_issuance,
                buybacks = EXCLUDED.buybacks
            """,
            [
                company_id, statement_type, fiscal_year,
                data.get("operating_cash_flow"), data.get("investing_cash_flow"),
                data.get("financing_cash_flow"), data.get("capital_expenditure"),
                data.get("free_cash_flow"), data.get("dividends_paid"),
                data.get("debt_raised"), data.get("debt_repaid"),
                data.get("share_issuance"), data.get("buybacks"),
            ],
        )

    def get_cash_flow(self, company_id: int, statement_type: str) -> pd.DataFrame:
        return self._conn.execute(
            """
            SELECT * FROM cash_flow
            WHERE company_id = ? AND statement_type = ?
            ORDER BY fiscal_year
            """,
            [company_id, statement_type],
        ).fetchdf()

    # ------------------------------------------------------------------
    # Shareholding
    # ------------------------------------------------------------------

    def upsert_shareholding(self, company_id: int, period_end_date: str, data: dict) -> None:
        self._conn.execute(
            """
            INSERT INTO shareholding
                (id, company_id, period_end_date, fiscal_year, fiscal_quarter,
                 promoter_pct, promoter_pledge_pct, fii_pct, dii_pct,
                 government_pct, public_pct, other_pct)
            VALUES (nextval('seq_shareholding'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (company_id, period_end_date) DO UPDATE SET
                promoter_pct = EXCLUDED.promoter_pct,
                promoter_pledge_pct = EXCLUDED.promoter_pledge_pct,
                fii_pct = EXCLUDED.fii_pct,
                dii_pct = EXCLUDED.dii_pct,
                government_pct = EXCLUDED.government_pct,
                public_pct = EXCLUDED.public_pct,
                other_pct = EXCLUDED.other_pct
            """,
            [
                company_id, period_end_date,
                data.get("fiscal_year"), data.get("fiscal_quarter"),
                data.get("promoter_pct"), data.get("promoter_pledge_pct"),
                data.get("fii_pct"), data.get("dii_pct"),
                data.get("government_pct"), data.get("public_pct"),
                data.get("other_pct"),
            ],
        )

    def get_shareholding(self, company_id: int) -> pd.DataFrame:
        return self._conn.execute(
            """
            SELECT * FROM shareholding
            WHERE company_id = ?
            ORDER BY period_end_date
            """,
            [company_id],
        ).fetchdf()

    # ------------------------------------------------------------------
    # Market Data
    # ------------------------------------------------------------------

    def upsert_market_data(self, company_id: int, date_str: str, data: dict) -> None:
        self._conn.execute(
            """
            INSERT INTO market_data
                (id, company_id, date, price, market_cap, shares_outstanding,
                 pe, pb, enterprise_value, ev_ebitda, ev_ebit, dividend_yield)
            VALUES (nextval('seq_market_data'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (company_id, date) DO UPDATE SET
                price = EXCLUDED.price,
                market_cap = EXCLUDED.market_cap,
                shares_outstanding = EXCLUDED.shares_outstanding,
                pe = EXCLUDED.pe,
                pb = EXCLUDED.pb,
                enterprise_value = EXCLUDED.enterprise_value,
                ev_ebitda = EXCLUDED.ev_ebitda,
                ev_ebit = EXCLUDED.ev_ebit,
                dividend_yield = EXCLUDED.dividend_yield
            """,
            [
                company_id, date_str,
                data.get("price"), data.get("market_cap"), data.get("shares_outstanding"),
                data.get("pe"), data.get("pb"), data.get("enterprise_value"),
                data.get("ev_ebitda"), data.get("ev_ebit"), data.get("dividend_yield"),
            ],
        )

    def get_all_market_data(self, company_id: int) -> pd.DataFrame:
        return self._conn.execute(
            """
            SELECT date, price, market_cap, shares_outstanding,
                   pe, pb, enterprise_value, ev_ebitda, ev_ebit, dividend_yield
            FROM market_data
            WHERE company_id = ?
            ORDER BY date
            """,
            [company_id],
        ).fetchdf()

    def get_latest_market_data(self, company_id: int) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM market_data WHERE company_id = ? ORDER BY date DESC LIMIT 1",
            [company_id],
        ).fetchdf()
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    # ------------------------------------------------------------------
    # Corporate Actions
    # ------------------------------------------------------------------

    def insert_corporate_action(self, company_id: int, action_date: str,
                                 action_type: str, description: str,
                                 ratio_or_amount: Optional[str] = None) -> None:
        self._conn.execute(
            """
            INSERT INTO corporate_actions
                (id, company_id, action_date, action_type, description, ratio_or_amount)
            VALUES (nextval('seq_corporate_actions'), ?, ?, ?, ?, ?)
            """,
            [company_id, action_date, action_type, description, ratio_or_amount],
        )

    def upsert_corporate_action(
        self,
        company_id: int,
        action_date: str,
        action_type: str,
        description: str,
        ratio_or_amount: Optional[str] = None,
    ) -> None:
        """Insert or update — keyed on (company_id, action_date, action_type)."""
        existing = self._conn.execute(
            """
            SELECT id FROM corporate_actions
            WHERE company_id = ? AND action_date = ? AND action_type = ?
            """,
            [company_id, action_date, action_type],
        ).fetchone()
        if existing:
            self._conn.execute(
                "UPDATE corporate_actions SET description = ?, ratio_or_amount = ? WHERE id = ?",
                [description, ratio_or_amount, existing[0]],
            )
        else:
            self._conn.execute(
                """
                INSERT INTO corporate_actions
                    (id, company_id, action_date, action_type, description, ratio_or_amount)
                VALUES (nextval('seq_corporate_actions'), ?, ?, ?, ?, ?)
                """,
                [company_id, action_date, action_type, description, ratio_or_amount],
            )

    def delete_corporate_action(self, action_id: int) -> None:
        self._conn.execute("DELETE FROM corporate_actions WHERE id = ?", [action_id])

    def get_corporate_actions(self, company_id: int) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT * FROM corporate_actions WHERE company_id = ? ORDER BY action_date DESC",
            [company_id],
        ).fetchdf()

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def insert_document(self, company_id: int, document_type: str, fiscal_year: Optional[int],
                         file_name: str, file_path: str, file_hash: str,
                         page_count: int = 0) -> int:
        doc_id = self._conn.execute(
            "SELECT nextval('seq_documents')"
        ).fetchone()[0]
        self._conn.execute(
            """
            INSERT INTO documents
                (document_id, company_id, document_type, fiscal_year,
                 file_name, file_path, file_hash, import_timestamp, page_count, text_extracted)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, FALSE)
            """,
            [doc_id, company_id, document_type, fiscal_year, file_name, file_path,
             file_hash, page_count],
        )
        return doc_id

    def get_documents(self, company_id: int) -> pd.DataFrame:
        return self._conn.execute(
            "SELECT * FROM documents WHERE company_id = ? ORDER BY fiscal_year DESC",
            [company_id],
        ).fetchdf()

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def get_available_statement_types(self, company_id: int) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT statement_type FROM annual_income WHERE company_id = ?",
            [company_id],
        ).fetchall()
        return [r[0] for r in rows]

    def get_available_fiscal_years(self, company_id: int, statement_type: str) -> list[int]:
        rows = self._conn.execute(
            """
            SELECT DISTINCT fiscal_year FROM annual_income
            WHERE company_id = ? AND statement_type = ?
            ORDER BY fiscal_year
            """,
            [company_id, statement_type],
        ).fetchall()
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Sector Metrics
    # ------------------------------------------------------------------

    def upsert_sector_metric(
        self,
        company_id: int,
        period_end_date: str,
        metric_name: str,
        metric_value: Optional[float],
        metric_unit: str = "",
        source: str = "manual",
    ) -> None:
        existing = self._conn.execute(
            """
            SELECT id FROM sector_metrics
            WHERE company_id = ? AND period_end_date = ? AND metric_name = ?
            """,
            [company_id, period_end_date, metric_name],
        ).fetchone()
        if existing:
            self._conn.execute(
                """
                UPDATE sector_metrics
                SET metric_value = ?, metric_unit = ?, source = ?
                WHERE id = ?
                """,
                [metric_value, metric_unit, source, existing[0]],
            )
        else:
            self._conn.execute(
                """
                INSERT INTO sector_metrics
                    (id, company_id, period_end_date, metric_name, metric_value, metric_unit, source)
                VALUES (nextval('seq_sector_metrics'), ?, ?, ?, ?, ?, ?)
                """,
                [company_id, period_end_date, metric_name, metric_value, metric_unit, source],
            )

    def get_sector_metrics(self, company_id: int) -> pd.DataFrame:
        return self._conn.execute(
            """
            SELECT period_end_date, metric_name, metric_value, metric_unit, source
            FROM sector_metrics
            WHERE company_id = ?
            ORDER BY period_end_date, metric_name
            """,
            [company_id],
        ).fetchdf()

    def delete_sector_metrics_for_period(
        self, company_id: int, period_end_date: str
    ) -> int:
        """Delete all sector metrics for a given company + period. Returns rows deleted."""
        result = self._conn.execute(
            "SELECT COUNT(*) FROM sector_metrics WHERE company_id = ? AND period_end_date = ?",
            [company_id, period_end_date],
        ).fetchone()
        count = result[0] if result else 0
        self._conn.execute(
            "DELETE FROM sector_metrics WHERE company_id = ? AND period_end_date = ?",
            [company_id, period_end_date],
        )
        return count
