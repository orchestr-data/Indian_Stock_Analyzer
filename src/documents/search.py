"""Local full-text search over document sections."""

from __future__ import annotations
import logging
import re
from typing import Optional

import duckdb

from src.database.connection import DatabaseConnection
from src.models.documents import DocumentSearchResult

logger = logging.getLogger(__name__)


class DocumentSearch:
    """Searches extracted document text stored in document_sections."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._conn = db.conn

    def search(
        self,
        company_id: int,
        query: str,
        document_type: Optional[str] = None,
        fiscal_year: Optional[int] = None,
        max_results: int = 50,
    ) -> list[DocumentSearchResult]:
        """Full-text search over document sections for a company."""
        query = query.strip()
        if not query:
            return []

        # Build SQL with LIKE — DuckDB supports ILIKE for case-insensitive
        like_pattern = f"%{query}%"

        sql = """
            SELECT
                ds.document_id,
                d.company_id,
                d.document_type,
                d.fiscal_year,
                d.file_name,
                ds.page_start AS page_number,
                ds.text
            FROM document_sections ds
            JOIN documents d ON ds.document_id = d.document_id
            WHERE d.company_id = ?
              AND ds.text ILIKE ?
        """
        params: list = [company_id, like_pattern]

        if document_type:
            sql += " AND d.document_type = ?"
            params.append(document_type)
        if fiscal_year:
            sql += " AND d.fiscal_year = ?"
            params.append(fiscal_year)

        sql += f" LIMIT {max_results}"

        try:
            rows = self._conn.execute(sql, params).fetchdf()
        except Exception as exc:
            logger.error("Search failed: %s", exc)
            return []

        results = []
        for _, row in rows.iterrows():
            snippet = self._extract_snippet(str(row["text"]), query)
            results.append(DocumentSearchResult(
                document_id=int(row["document_id"]),
                company_id=int(row["company_id"]),
                document_type=str(row["document_type"]),
                fiscal_year=int(row["fiscal_year"]) if row["fiscal_year"] else None,
                file_name=str(row["file_name"]),
                page_number=int(row["page_number"]),
                snippet=snippet,
                score=1.0,
            ))

        return results

    @staticmethod
    def _extract_snippet(text: str, query: str, context_chars: int = 200) -> str:
        """Extract a short snippet around the first query match."""
        idx = text.lower().find(query.lower())
        if idx == -1:
            return text[:context_chars] + "..."
        start = max(0, idx - context_chars // 2)
        end = min(len(text), idx + len(query) + context_chars // 2)
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet
