"""Document and document section models for PDFs."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class Document(BaseModel):
    """An imported company document (PDF)."""

    document_id: Optional[int] = None
    company_id: int
    document_type: str  # "annual_report", "investor_presentation", "concall", "earnings"
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    file_name: str
    file_path: str
    file_hash: str
    import_timestamp: datetime
    page_count: int = 0
    text_extracted: bool = False


class DocumentSection(BaseModel):
    """An identified section within a document."""

    section_id: Optional[int] = None
    document_id: int
    section_name: str
    page_start: int
    page_end: int
    text: str = ""


class DocumentSearchResult(BaseModel):
    """A search result from document full-text search."""

    document_id: int
    company_id: int
    document_type: str
    fiscal_year: Optional[int]
    file_name: str
    page_number: int
    snippet: str
    score: float = 1.0
