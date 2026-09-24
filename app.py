"""Indian Stock Fundamental Analyzer — main Streamlit entry point."""

from __future__ import annotations
import logging
import sys
from pathlib import Path

# Add project root to path so `src` imports work regardless of how streamlit is launched
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import streamlit as st

from src.config import setup_logging, get_db_path
from src.database.connection import get_connection
from src.database.repository import Repository
from src.ingestion.importer import ImportOrchestrator
from src.ingestion.document_importer import DocumentImporter
from src.sectors.registry import SectorRegistry

# ------------------------------------------------------------------ setup
setup_logging()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Indian Stock Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------ DB
@st.cache_resource
def get_db():
    return get_connection()


db = get_db()
repo = Repository(db.conn)
sector_registry = SectorRegistry()

# ------------------------------------------------------------------ sidebar
def render_sidebar():
    st.sidebar.title("📊 Indian Stock Analyzer")
    st.sidebar.caption("Local. No cloud AI. No recommendations.")
    st.sidebar.divider()

    # Company search / selector
    companies = repo.list_companies()

    company_id = None
    company = None

    if not companies.empty:
        options = {
            f"{row['ticker']} — {row['company_name']}": int(row["company_id"])
            for _, row in companies.iterrows()
        }
        selected = st.sidebar.selectbox(
            "Select Company",
            list(options.keys()),
            key="selected_company",
        )
        if selected:
            company_id = options[selected]
            company = repo.get_company_by_id(company_id)
    else:
        st.sidebar.info("No companies imported yet.")

    # Statement type
    stmt_types = ["Consolidated", "Standalone"]
    if company_id:
        available = repo.get_available_statement_types(company_id)
        if available:
            stmt_types = available

    statement_type = st.sidebar.selectbox(
        "Statement Type",
        stmt_types,
        key="statement_type",
    )

    # Sector override — persisted to DB
    if company_id and company:
        current_sector = company.get("sector", "DEFAULT")
        all_sectors = sorted(sector_registry.all_sectors())
        try:
            sector_idx = all_sectors.index(current_sector)
        except ValueError:
            sector_idx = 0
        override_sector = st.sidebar.selectbox(
            "Sector",
            all_sectors,
            index=sector_idx,
            key="sector_override_select",
            help="Overrides the sector detected on import. Saved to the database.",
        )
        if override_sector != current_sector:
            if st.sidebar.button("Save Sector", key="save_sector_btn", type="primary"):
                repo.update_company_sector(company_id, override_sector)
                st.rerun()

    # Navigation
    st.sidebar.divider()
    st.sidebar.markdown("**Navigation**")
    page = st.sidebar.radio(
        "Page",
        [
            "Overview",
            "Business",
            "Growth",
            "Profitability",
            "Balance Sheet",
            "Cash Flow",
            "Efficiency",
            "Valuation",
            "Ownership",
            "Quarterly",
            "Peers",
            "Documents",
            "Observations",
            "Sector Analysis",
            "Corporate Actions",
            "Data Quality",
            "Raw Data",
        ],
        key="page",
    )

    # Import section
    st.sidebar.divider()
    st.sidebar.markdown("**Import Data**")

    with st.sidebar.expander("Import Screener Excel"):
        uploaded = st.file_uploader(
            "Screener.in Excel export (.xlsx)",
            type=["xlsx"],
            key="screener_upload",
        )
        ticker_override = st.text_input("Ticker override (optional)", key="ticker_override")
        sector_opt = st.selectbox(
            "Sector",
            ["Auto-detect"] + sector_registry.all_sectors(),
            key="sector_opt",
        )
        if st.button("Import", key="import_btn") and uploaded:
            _handle_screener_import(uploaded, ticker_override, sector_opt)

    with st.sidebar.expander("Import PDF Document"):
        pdf_uploaded = st.file_uploader(
            "Annual Report / Presentation (.pdf)",
            type=["pdf"],
            key="pdf_upload",
        )
        doc_type = st.selectbox(
            "Document Type",
            ["annual_report", "investor_presentation", "earnings_presentation",
             "concall_transcript", "other"],
            key="doc_type",
        )
        pdf_fy = st.number_input("Fiscal Year (optional)", min_value=2000, max_value=2040,
                                  value=2025, key="pdf_fy")
        if st.button("Import PDF", key="import_pdf_btn") and pdf_uploaded and company_id:
            _handle_pdf_import(pdf_uploaded, company_id, company, doc_type, pdf_fy)

    # Peer selection
    st.sidebar.divider()
    st.sidebar.markdown("**Peer Comparison**")
    if not companies.empty:
        peer_options = {
            f"{row['ticker']} — {row['company_name']}": int(row["company_id"])
            for _, row in companies.iterrows()
        }
        selected_peers = st.sidebar.multiselect(
            "Select peers (2–10)",
            list(peer_options.keys()),
            max_selections=10,
            key="peer_selection",
        )
        peer_ids = [peer_options[p] for p in selected_peers]
    else:
        peer_ids = []

    return company_id, company, statement_type, page, peer_ids


def _handle_screener_import(uploaded, ticker_override, sector_opt):
    """Save uploaded file to temp and run import."""
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = tmp.name

    try:
        orchestrator = ImportOrchestrator(db)
        sector = None if sector_opt == "Auto-detect" else sector_opt
        result = orchestrator.import_screener_excel(tmp_path, ticker_override or None, sector)

        if result.success:
            st.sidebar.success(
                f"✅ Imported: {result.company_name} | {result.statement_type} | "
                f"{len(result.fiscal_years_imported)} years"
            )
            if result.warnings:
                for w in result.warnings[:3]:
                    st.sidebar.warning(w)
            st.rerun()
        else:
            for err in result.errors:
                st.sidebar.error(f"❌ {err}")
    finally:
        os.unlink(tmp_path)


def _handle_pdf_import(pdf_uploaded, company_id, company, doc_type, pdf_fy):
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_uploaded.getbuffer())
        tmp_path = tmp.name

    try:
        importer = DocumentImporter(db)
        result = importer.import_pdf(
            tmp_path, company_id,
            ticker=company["ticker"] if company else "UNKNOWN",
            document_type=doc_type,
            fiscal_year=pdf_fy,
        )
        if result["success"]:
            st.sidebar.success(
                f"✅ PDF imported: {result['page_count']} pages | "
                f"Text extracted: {result['text_extracted']}"
            )
            st.rerun()
        else:
            st.sidebar.error(f"❌ {result.get('error', 'Unknown error')}")
    finally:
        os.unlink(tmp_path)


# ------------------------------------------------------------------ data loaders
@st.cache_data(ttl=30)
def load_company_data(company_id: int, statement_type: str):
    """Load all financial data for a company."""
    income = repo.get_annual_income(company_id, statement_type)
    balance = repo.get_balance_sheet(company_id, statement_type)
    cashflow = repo.get_cash_flow(company_id, statement_type)
    shareholding = repo.get_shareholding(company_id)
    quarterly = repo.get_quarterly_income(company_id, statement_type)
    market = repo.get_latest_market_data(company_id)
    imports = repo.get_import_history(company_id)
    documents = repo.get_documents(company_id)
    return income, balance, cashflow, shareholding, quarterly, market, imports, documents


# ------------------------------------------------------------------ main
def main():
    company_id, company, statement_type, page, peer_ids = render_sidebar()

    # Welcome screen when nothing imported
    if company_id is None:
        st.title("📊 Indian Stock Fundamental Analyzer")
        st.markdown(
            """
**Local. Private. No cloud AI. No recommendations.**

This tool helps you systematically investigate Indian companies using
fundamental analysis techniques. It is a research aid — not an investment advisor.

---
### Getting Started

1. **Download** a company export from [Screener.in](https://www.screener.in)
   (Excel format — requires free account)
2. **Import** the file using the sidebar panel on the left
3. **Explore** financial trends, ratios, and observations

---
### What this tool does
- Imports and stores Screener.in Excel exports locally
- Calculates financial ratios from first principles
- Surfaces factual observations and trend changes
- Compares companies you have imported
- Searches imported annual report PDFs

### What this tool does NOT do
- It does NOT make BUY / SELL / HOLD recommendations
- It does NOT score companies out of 100
- It does NOT use cloud AI APIs
- It does NOT automatically download any data
            """
        )
        return

    # Load data
    income_df, balance_df, cashflow_df, shareholding_df, quarterly_df, \
        market_data, import_history_df, documents_df = load_company_data(company_id, statement_type)

    sector = company.get("sector", "DEFAULT") if company else "DEFAULT"
    sector_config = sector_registry.get_config(sector)

    # Route to page
    if page == "Overview":
        from src.ui import overview
        overview.render(company, income_df, balance_df, cashflow_df, market_data, statement_type, sector)

    elif page == "Business":
        from src.ui import business
        business.render(company, sector_config)

    elif page == "Growth":
        from src.ui import growth
        growth.render(income_df, cashflow_df, statement_type)

    elif page == "Profitability":
        from src.ui import profitability
        profitability.render(income_df, balance_df, statement_type, sector)

    elif page == "Balance Sheet":
        from src.ui import balance_sheet
        balance_sheet.render(balance_df, income_df, statement_type, sector)

    elif page == "Cash Flow":
        from src.ui import cashflow
        cashflow.render(income_df, cashflow_df, balance_df, market_data, statement_type)

    elif page == "Efficiency":
        from src.ui import efficiency
        efficiency.render(income_df, balance_df, statement_type, sector)

    elif page == "Valuation":
        from src.ui import valuation
        market_history_df = repo.get_all_market_data(company_id)
        valuation.render(income_df, balance_df, cashflow_df, market_data, market_history_df, statement_type, sector)

    elif page == "Ownership":
        from src.ui import ownership
        ownership.render(shareholding_df, income_df)

    elif page == "Quarterly":
        from src.ui import quarterly
        quarterly.render(quarterly_df, statement_type)

    elif page == "Peers":
        from src.ui import peers
        from src.analysis.peer_comparison import PeerComparisonEngine
        if peer_ids:
            engine = PeerComparisonEngine(repo)
            comparison_df = engine.build_comparison(peer_ids, statement_type)
        else:
            comparison_df = pd.DataFrame()
        peers.render(comparison_df)

    elif page == "Documents":
        from src.ui import documents
        documents.render(company_id, documents_df, db)

    elif page == "Observations":
        from src.ui import observations
        observations.render(
            income_df, balance_df, cashflow_df, shareholding_df, market_data, sector
        )

    elif page == "Sector Analysis":
        from src.ui import sector_metrics as sector_metrics_page
        sector_metrics_page.render(company, income_df, balance_df, sector, repo)

    elif page == "Corporate Actions":
        from src.ui import corporate_actions as corporate_actions_page
        corporate_actions_page.render(company_id, company, income_df, cashflow_df, repo)

    elif page == "Data Quality":
        from src.ui import data_quality
        data_quality.render(
            company_id, income_df, balance_df, cashflow_df,
            shareholding_df, import_history_df, statement_type,
        )

    elif page == "Raw Data":
        from src.ui import raw_data
        raw_data.render(
            company_id, income_df, balance_df, cashflow_df,
            shareholding_df, import_history_df, statement_type,
        )


if __name__ == "__main__":
    main()
