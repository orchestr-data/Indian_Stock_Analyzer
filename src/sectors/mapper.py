"""Maps industry/company descriptions to sector enum values."""

from __future__ import annotations
from rapidfuzz import process, fuzz

from src.models.company import SectorEnum

_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "IT_SERVICES": [
        "information technology", "software", "it services", "bpo", "ites",
        "technology outsourcing", "consulting", "digital", "tcs", "infosys", "wipro",
        "hcl tech", "tech mahindra",
    ],
    "BANKING": [
        "bank", "banking", "commercial bank", "private bank", "public sector bank",
        "hdfc bank", "icici bank", "kotak", "sbi", "axis bank",
    ],
    "NBFC": [
        "nbfc", "non-banking financial", "housing finance", "hfc", "microfinance",
        "mfi", "gold loan", "consumer finance", "vehicle finance",
    ],
    "INSURANCE": [
        "insurance", "life insurance", "general insurance", "reinsurance", "health insurance",
    ],
    "FMCG": [
        "fmcg", "fast moving consumer", "consumer goods", "food", "beverage",
        "personal care", "household", "hul", "nestle", "britannia", "dabur",
    ],
    "PHARMA": [
        "pharma", "pharmaceutical", "drug", "api", "formulation", "biotech",
        "healthcare", "medicine",
    ],
    "AUTOMOBILES": [
        "automobile", "automotive", "vehicle", "car", "two wheeler", "tractor",
        "commercial vehicle", "auto ancillary", "auto components",
    ],
    "METALS": [
        "steel", "aluminium", "aluminum", "copper", "zinc", "iron", "metal",
        "mining", "coal", "mineral",
    ],
    "CEMENT": ["cement", "ready mix concrete", "rmc"],
    "CHEMICALS": [
        "chemical", "specialty chemical", "agrochemical", "fertilizer",
        "dye", "pigment", "fluorochemical",
    ],
    "OIL_GAS": [
        "oil", "gas", "petroleum", "refinery", "exploration", "production",
        "e&p", "lng", "cng", "pipeline",
    ],
    "POWER": [
        "power", "electricity", "energy", "utility", "generation", "transmission",
        "distribution", "renewable", "solar", "wind",
    ],
    "TELECOM": ["telecom", "telecommunication", "mobile", "broadband", "wireless"],
    "INFRASTRUCTURE": [
        "infrastructure", "construction", "road", "highway", "port", "airport",
        "real estate developer", "epc",
    ],
    "REAL_ESTATE": ["real estate", "property", "developer", "reit", "housing"],
}


class SectorMapper:
    """Maps a company's industry description to a SectorEnum."""

    def map(self, industry_text: str) -> SectorEnum:
        """Return the best matching sector for a given industry description."""
        if not industry_text:
            return SectorEnum.DEFAULT
        text = industry_text.lower()
        for sector, keywords in _SECTOR_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return SectorEnum(sector)
        return SectorEnum.DEFAULT

    def fuzzy_map(self, industry_text: str, threshold: int = 70) -> SectorEnum:
        """Use fuzzy matching when exact keyword match fails."""
        if not industry_text:
            return SectorEnum.DEFAULT
        text = industry_text.lower()
        all_keywords = [(kw, sector) for sector, kws in _SECTOR_KEYWORDS.items() for kw in kws]
        keyword_list = [kw for kw, _ in all_keywords]
        match = process.extractOne(text, keyword_list, scorer=fuzz.partial_ratio)
        if match and match[1] >= threshold:
            matched_kw = match[0]
            for kw, sector in all_keywords:
                if kw == matched_kw:
                    return SectorEnum(sector)
        return SectorEnum.DEFAULT
