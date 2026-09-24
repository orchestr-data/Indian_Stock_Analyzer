"""DuckDB schema DDL — all CREATE TABLE IF NOT EXISTS statements."""

from __future__ import annotations
import logging

import duckdb

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
-- Companies registry
CREATE TABLE IF NOT EXISTS companies (
    company_id    INTEGER PRIMARY KEY,
    ticker        VARCHAR NOT NULL,
    company_name  VARCHAR NOT NULL,
    nse_symbol    VARCHAR,
    bse_code      VARCHAR,
    isin          VARCHAR,
    sector        VARCHAR NOT NULL DEFAULT 'DEFAULT',
    industry      VARCHAR,
    sub_industry  VARCHAR,
    source        VARCHAR NOT NULL DEFAULT 'screener',
    last_updated  TIMESTAMP
);

CREATE SEQUENCE IF NOT EXISTS seq_companies START 1;

-- Source import log
CREATE TABLE IF NOT EXISTS source_imports (
    import_id       INTEGER PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(company_id),
    source_type     VARCHAR NOT NULL,
    source_name     VARCHAR NOT NULL,
    source_file     VARCHAR NOT NULL,
    file_hash       VARCHAR NOT NULL,
    statement_type  VARCHAR NOT NULL,
    import_timestamp TIMESTAMP NOT NULL,
    status          VARCHAR NOT NULL,
    warnings        VARCHAR
);

CREATE SEQUENCE IF NOT EXISTS seq_source_imports START 1;

-- Annual Income Statement
CREATE TABLE IF NOT EXISTS annual_income (
    id                  INTEGER PRIMARY KEY,
    company_id          INTEGER NOT NULL REFERENCES companies(company_id),
    statement_type      VARCHAR NOT NULL,
    fiscal_year         INTEGER NOT NULL,
    revenue             DOUBLE,
    expenses            DOUBLE,
    operating_profit    DOUBLE,
    ebitda              DOUBLE,
    ebit                DOUBLE,
    other_income        DOUBLE,
    interest            DOUBLE,
    depreciation        DOUBLE,
    amortization        DOUBLE,
    pbt                 DOUBLE,
    tax                 DOUBLE,
    pat                 DOUBLE,
    minority_interest   DOUBLE,
    pat_attributable    DOUBLE,
    basic_eps           DOUBLE,
    diluted_eps         DOUBLE,
    weighted_avg_shares DOUBLE,
    UNIQUE (company_id, statement_type, fiscal_year)
);

CREATE SEQUENCE IF NOT EXISTS seq_annual_income START 1;

-- Quarterly Income Statement
CREATE TABLE IF NOT EXISTS quarterly_income (
    id               INTEGER PRIMARY KEY,
    company_id       INTEGER NOT NULL REFERENCES companies(company_id),
    statement_type   VARCHAR NOT NULL,
    fiscal_year      INTEGER NOT NULL,
    fiscal_quarter   INTEGER NOT NULL CHECK (fiscal_quarter BETWEEN 1 AND 4),
    period_end_date  DATE,
    revenue          DOUBLE,
    expenses         DOUBLE,
    operating_profit DOUBLE,
    ebitda           DOUBLE,
    ebit             DOUBLE,
    other_income     DOUBLE,
    interest         DOUBLE,
    depreciation     DOUBLE,
    pbt              DOUBLE,
    tax              DOUBLE,
    pat              DOUBLE,
    eps              DOUBLE,
    operating_margin DOUBLE,
    UNIQUE (company_id, statement_type, fiscal_year, fiscal_quarter)
);

CREATE SEQUENCE IF NOT EXISTS seq_quarterly_income START 1;

-- Balance Sheet
CREATE TABLE IF NOT EXISTS balance_sheet (
    id                        INTEGER PRIMARY KEY,
    company_id                INTEGER NOT NULL REFERENCES companies(company_id),
    statement_type            VARCHAR NOT NULL,
    fiscal_year               INTEGER NOT NULL,
    equity_capital            DOUBLE,
    reserves                  DOUBLE,
    shareholders_equity       DOUBLE,
    borrowings                DOUBLE,
    short_term_debt           DOUBLE,
    long_term_debt            DOUBLE,
    other_current_liabilities DOUBLE,
    total_liabilities         DOUBLE,
    cash_and_equivalents      DOUBLE,
    receivables               DOUBLE,
    inventory                 DOUBLE,
    payables                  DOUBLE,
    other_current_assets      DOUBLE,
    fixed_assets              DOUBLE,
    cwip                      DOUBLE,
    investments               DOUBLE,
    other_assets              DOUBLE,
    total_assets              DOUBLE,
    UNIQUE (company_id, statement_type, fiscal_year)
);

CREATE SEQUENCE IF NOT EXISTS seq_balance_sheet START 1;

-- Cash Flow Statement
CREATE TABLE IF NOT EXISTS cash_flow (
    id                   INTEGER PRIMARY KEY,
    company_id           INTEGER NOT NULL REFERENCES companies(company_id),
    statement_type       VARCHAR NOT NULL,
    fiscal_year          INTEGER NOT NULL,
    operating_cash_flow  DOUBLE,
    investing_cash_flow  DOUBLE,
    financing_cash_flow  DOUBLE,
    capital_expenditure  DOUBLE,
    free_cash_flow       DOUBLE,
    dividends_paid       DOUBLE,
    debt_raised          DOUBLE,
    debt_repaid          DOUBLE,
    share_issuance       DOUBLE,
    buybacks             DOUBLE,
    UNIQUE (company_id, statement_type, fiscal_year)
);

CREATE SEQUENCE IF NOT EXISTS seq_cash_flow START 1;

-- Shareholding Pattern
CREATE TABLE IF NOT EXISTS shareholding (
    id                  INTEGER PRIMARY KEY,
    company_id          INTEGER NOT NULL REFERENCES companies(company_id),
    period_end_date     DATE NOT NULL,
    fiscal_year         INTEGER,
    fiscal_quarter      INTEGER,
    promoter_pct        DOUBLE,
    promoter_pledge_pct DOUBLE,
    fii_pct             DOUBLE,
    dii_pct             DOUBLE,
    government_pct      DOUBLE,
    public_pct          DOUBLE,
    other_pct           DOUBLE,
    UNIQUE (company_id, period_end_date)
);

CREATE SEQUENCE IF NOT EXISTS seq_shareholding START 1;

-- Market Data
CREATE TABLE IF NOT EXISTS market_data (
    id                INTEGER PRIMARY KEY,
    company_id        INTEGER NOT NULL REFERENCES companies(company_id),
    date              DATE NOT NULL,
    price             DOUBLE,
    market_cap        DOUBLE,
    shares_outstanding DOUBLE,
    pe                DOUBLE,
    pb                DOUBLE,
    enterprise_value  DOUBLE,
    ev_ebitda         DOUBLE,
    ev_ebit           DOUBLE,
    dividend_yield    DOUBLE,
    UNIQUE (company_id, date)
);

CREATE SEQUENCE IF NOT EXISTS seq_market_data START 1;

-- Calculated Metrics
CREATE TABLE IF NOT EXISTS calculated_metrics (
    id                   INTEGER PRIMARY KEY,
    company_id           INTEGER NOT NULL REFERENCES companies(company_id),
    statement_type       VARCHAR NOT NULL,
    period_type          VARCHAR NOT NULL,
    period_end_date      DATE,
    metric_name          VARCHAR NOT NULL,
    metric_value         DOUBLE,
    calculation_version  VARCHAR NOT NULL DEFAULT '1.0',
    source_basis         VARCHAR
);

CREATE SEQUENCE IF NOT EXISTS seq_calculated_metrics START 1;

-- Corporate Actions
CREATE TABLE IF NOT EXISTS corporate_actions (
    id               INTEGER PRIMARY KEY,
    company_id       INTEGER NOT NULL REFERENCES companies(company_id),
    action_date      DATE NOT NULL,
    action_type      VARCHAR NOT NULL,
    description      VARCHAR NOT NULL,
    ratio_or_amount  VARCHAR
);

CREATE SEQUENCE IF NOT EXISTS seq_corporate_actions START 1;

-- Documents
CREATE TABLE IF NOT EXISTS documents (
    document_id      INTEGER PRIMARY KEY,
    company_id       INTEGER NOT NULL REFERENCES companies(company_id),
    document_type    VARCHAR NOT NULL,
    fiscal_year      INTEGER,
    fiscal_quarter   INTEGER,
    file_name        VARCHAR NOT NULL,
    file_path        VARCHAR NOT NULL,
    file_hash        VARCHAR NOT NULL,
    import_timestamp TIMESTAMP NOT NULL,
    page_count       INTEGER NOT NULL DEFAULT 0,
    text_extracted   BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE SEQUENCE IF NOT EXISTS seq_documents START 1;

-- Document Sections
CREATE TABLE IF NOT EXISTS document_sections (
    section_id   INTEGER PRIMARY KEY,
    document_id  INTEGER NOT NULL REFERENCES documents(document_id),
    section_name VARCHAR NOT NULL,
    page_start   INTEGER NOT NULL,
    page_end     INTEGER NOT NULL,
    text         VARCHAR NOT NULL DEFAULT ''
);

CREATE SEQUENCE IF NOT EXISTS seq_document_sections START 1;

-- Sector-specific metrics (flexible key-value store)
CREATE TABLE IF NOT EXISTS sector_metrics (
    id             INTEGER PRIMARY KEY,
    company_id     INTEGER NOT NULL REFERENCES companies(company_id),
    period_end_date DATE NOT NULL,
    metric_name    VARCHAR NOT NULL,
    metric_value   DOUBLE,
    metric_unit    VARCHAR,
    source         VARCHAR
);

CREATE SEQUENCE IF NOT EXISTS seq_sector_metrics START 1;
"""


def create_all_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all tables if they don't already exist."""
    try:
        conn.execute(_SCHEMA_SQL)
        logger.info("Schema initialized / verified")
    except Exception as exc:
        logger.error("Schema initialization failed: %s", exc)
        raise


def drop_all_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Drop all application tables — DESTRUCTIVE, for testing only."""
    tables = [
        "sector_metrics", "document_sections", "documents",
        "corporate_actions", "calculated_metrics", "market_data",
        "shareholding", "cash_flow", "balance_sheet",
        "quarterly_income", "annual_income", "source_imports", "companies",
    ]
    for t in tables:
        conn.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    logger.warning("All tables dropped")
