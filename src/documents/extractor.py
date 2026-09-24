"""PDF text extraction using PyMuPDF."""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts text from PDF files using PyMuPDF (fitz)."""

    def extract(self, file_path: str | Path) -> dict[int, str]:
        """Return {page_number: text} for all pages."""
        try:
            import fitz
        except ImportError:
            logger.warning("PyMuPDF (fitz) not installed. PDF extraction unavailable.")
            return {}

        path = Path(file_path)
        if not path.exists():
            logger.error("PDF not found: %s", path)
            return {}

        pages: dict[int, str] = {}
        try:
            doc = fitz.open(str(path))
            for i in range(len(doc)):
                page = doc.load_page(i)
                pages[i + 1] = page.get_text()
            doc.close()
            logger.info("Extracted %d pages from %s", len(pages), path.name)
        except Exception as exc:
            logger.error("PDF extraction failed for %s: %s", path.name, exc)

        return pages

    def page_count(self, file_path: str | Path) -> int:
        """Return the number of pages in a PDF."""
        try:
            import fitz
            doc = fitz.open(str(file_path))
            n = len(doc)
            doc.close()
            return n
        except Exception:
            return 0
