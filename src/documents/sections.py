"""Section identifier — attempts to find common annual report sections."""

from __future__ import annotations
import re
from typing import Optional


COMMON_SECTIONS = [
    "Management Discussion and Analysis",
    "Risk Factors",
    "Auditor Report",
    "Related Party Transactions",
    "Contingent Liabilities",
    "Corporate Governance",
    "Remuneration",
    "Subsidiaries",
    "Capital Expenditure",
    "Business Overview",
    "Financial Highlights",
    "Directors Report",
    "Cash Flow Statement",
    "Notes to Accounts",
    "Segment Results",
]

_SECTION_PATTERNS = [
    (sec, re.compile(r"\b" + re.escape(sec.lower()) + r"\b"))
    for sec in COMMON_SECTIONS
]


def identify_section(text: str) -> Optional[str]:
    """Try to identify which common section a block of text belongs to."""
    text_lower = text.lower()
    for sec_name, pattern in _SECTION_PATTERNS:
        if pattern.search(text_lower):
            return sec_name
    return None


def find_sections_in_pages(
    text_by_page: dict[int, str]
) -> list[dict]:
    """Scan pages to find section boundaries.

    Returns a list of {section_name, page_start} dicts.
    """
    found: list[dict] = []
    for page_num, text in sorted(text_by_page.items()):
        # Short pages with a matching heading are likely section starts
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines[:5]:  # Check first 5 lines of page
            for sec_name, pattern in _SECTION_PATTERNS:
                if pattern.search(line.lower()) and len(line) < 80:
                    found.append({"section_name": sec_name, "page_start": page_num})
                    break
    return found
