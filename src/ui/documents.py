"""Documents page — search and browse imported PDFs."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from src.documents.search import DocumentSearch
from src.database.connection import DatabaseConnection
from src.ui.components import section_header


def render(company_id: int, documents_df: pd.DataFrame, db: DatabaseConnection) -> None:
    section_header("Documents", "Search imported annual reports and presentations")

    if documents_df is None or documents_df.empty:
        st.info(
            "No documents imported yet. "
            "Use the sidebar to import annual reports or presentations (PDF format)."
        )
        return

    st.markdown(f"**{len(documents_df)} document(s) imported**")
    st.dataframe(
        documents_df[["document_type", "fiscal_year", "file_name", "page_count", "text_extracted"]],
        use_container_width=True,
    )

    st.divider()
    st.markdown("#### Search Documents")
    query = st.text_input("Search term", placeholder="e.g. related party, contingent liability, R&D")

    if query:
        searcher = DocumentSearch(db)
        results = searcher.search(company_id, query, max_results=30)
        st.markdown(f"Found **{len(results)}** matching section(s)")
        for r in results:
            with st.expander(f"📄 {r.file_name} — Page {r.page_number}"):
                st.caption(f"Document type: {r.document_type} | Year: {r.fiscal_year or 'N/A'}")
                st.markdown(r.snippet)
