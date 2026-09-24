"""Document importer — imports PDFs (annual reports, presentations, etc.)."""

from __future__ import annotations
import hashlib
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import get_companies_path
from src.database.connection import DatabaseConnection
from src.database.repository import Repository

logger = logging.getLogger(__name__)

DOCUMENT_TYPES = {
    "annual_report": "Annual Report",
    "investor_presentation": "Investor Presentation",
    "earnings_presentation": "Earnings Presentation",
    "concall_transcript": "Conference Call Transcript",
    "other": "Other Document",
}


class DocumentImporter:
    """Imports PDF documents and extracts text for local search."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self._repo = Repository(db.conn)

    def import_pdf(
        self,
        file_path: str | Path,
        company_id: int,
        ticker: str,
        document_type: str,
        fiscal_year: Optional[int] = None,
        fiscal_quarter: Optional[int] = None,
    ) -> dict:
        """Import a PDF document, extract text, and store in database."""
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        file_hash = self._hash_file(path)

        # Copy to company documents folder
        dest = self._copy_to_storage(path, ticker, document_type, fiscal_year)

        # Try to extract text with PyMuPDF
        page_count = 0
        text_by_page: dict[int, str] = {}

        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            page_count = len(doc)
            for page_num in range(page_count):
                page = doc.load_page(page_num)
                text_by_page[page_num + 1] = page.get_text()
            doc.close()
            logger.info("Extracted text from %d pages", page_count)
        except ImportError:
            logger.warning("PyMuPDF not installed — text extraction skipped")
        except Exception as exc:
            logger.warning("Text extraction failed: %s", exc)

        # Store document metadata
        doc_id = self._repo.insert_document(
            company_id=company_id,
            document_type=document_type,
            fiscal_year=fiscal_year,
            file_name=path.name,
            file_path=str(dest),
            file_hash=file_hash,
            page_count=page_count,
        )

        # Store extracted text in document sections (one section per page for now)
        if text_by_page:
            self._store_text(doc_id, text_by_page)

        return {
            "success": True,
            "document_id": doc_id,
            "page_count": page_count,
            "text_extracted": bool(text_by_page),
            "stored_at": str(dest),
        }

    def _store_text(self, doc_id: int, text_by_page: dict[int, str]) -> None:
        """Store page text — grouped into sections later by the indexer."""
        from src.documents.indexer import DocumentIndexer
        indexer = DocumentIndexer(self._db)
        indexer.index_document(doc_id, text_by_page)

    def _copy_to_storage(
        self, path: Path, ticker: str, doc_type: str, fiscal_year: Optional[int]
    ) -> Path:
        companies_root = get_companies_path()
        subdir_map = {
            "annual_report": "annual_reports",
            "investor_presentation": "presentations",
            "earnings_presentation": "presentations",
            "concall_transcript": "concalls",
            "other": "documents",
        }
        subdir = subdir_map.get(doc_type, "documents")
        dest_dir = companies_root / ticker.upper() / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        if not dest.exists():
            shutil.copy2(path, dest)
        return dest

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
