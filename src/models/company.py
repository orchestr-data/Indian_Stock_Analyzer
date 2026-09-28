"""Company and sector models."""

from __future__ import annotations
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class SectorEnum(str, Enum):
    DEFAULT = "DEFAULT"
    IT_SERVICES = "IT_SERVICES"
    BANKING = "BANKING"
    NBFC = "NBFC"
    INSURANCE = "INSURANCE"
    FMCG = "FMCG"
    MANUFACTURING = "MANUFACTURING"
    METALS = "METALS"
    POWER = "POWER"
    TELECOM = "TELECOM"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    PHARMA = "PHARMA"
    AUTOMOBILES = "AUTOMOBILES"
    CEMENT = "CEMENT"
    CHEMICALS = "CHEMICALS"
    OIL_GAS = "OIL_GAS"
    REAL_ESTATE = "REAL_ESTATE"


class Company(BaseModel):
    """Core company identity record."""

    company_id: Optional[int] = None
    ticker: str
    company_name: str
    nse_symbol: Optional[str] = None
    bse_code: Optional[str] = None
    isin: Optional[str] = None
    sector: SectorEnum = SectorEnum.DEFAULT
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    source: str = "screener"
    last_updated: Optional[datetime] = None

    @property
    def display_name(self) -> str:
        return self.company_name or self.ticker

    @property
    def exchange_symbol(self) -> str:
        """Primary exchange symbol for display."""
        if self.nse_symbol:
            return f"NSE: {self.nse_symbol}"
        if self.bse_code:
            return f"BSE: {self.bse_code}"
        return self.ticker


class SourceImport(BaseModel):
    """Record of a file import event."""

    import_id: Optional[int] = None
    company_id: int
    source_type: str  # "screener_excel", "annual_report_pdf", etc.
    source_name: str  # human label
    source_file: str  # original filename
    file_hash: str
    statement_type: str
    import_timestamp: datetime
    status: str  # "success", "warning", "failed"
    warnings: Optional[list[str]] = None
