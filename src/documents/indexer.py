"""Document indexer — stores extracted page text in the database."""

from __future__ import annotations
import logging

import duckdb

from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Stores document text pages in the database for search."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._conn = db.conn

    def index_document(self, document_id: int, text_by_page: dict[int, str]) -> None:
        """Store each page as a section row. Pages grouped later."""
        for page_num, text in text_by_page.items():
            if not text.strip():
                continue
            try:
                sec_id = self._conn.execute(
                    "SELECT nextval('seq_document_sections')"
                ).fetchone()[0]
                self._conn.execute(
                    """
                    INSERT INTO document_sections
                        (section_id, document_id, section_name, page_start, page_end, text)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [sec_id, document_id, f"Page {page_num}", page_num, page_num, text[:10000]],
                )
            except Exception as exc:
                logger.error("Failed to index page %d of doc %d: %s", page_num, document_id, exc)

        # Mark document as text-extracted
        self._conn.execute(
            "UPDATE documents SET text_extracted = TRUE, page_count = ? WHERE document_id = ?",
            [max(text_by_page.keys()) if text_by_page else 0, document_id],
        )
        logger.info("Indexed %d pages for document %d", len(text_by_page), document_id)
