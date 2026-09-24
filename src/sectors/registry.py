"""Sector registry — combines loader and mapper."""

from __future__ import annotations
from typing import Any

from src.sectors.loader import SectorLoader
from src.sectors.mapper import SectorMapper
from src.models.company import SectorEnum


class SectorRegistry:
    """Central access point for sector configuration."""

    def __init__(self) -> None:
        self._loader = SectorLoader()
        self._mapper = SectorMapper()

    def get_config(self, sector: str | SectorEnum) -> dict[str, Any]:
        key = sector.value if isinstance(sector, SectorEnum) else sector
        return self._loader.get(key)

    def primary_metrics(self, sector: str | SectorEnum) -> list[str]:
        key = sector.value if isinstance(sector, SectorEnum) else sector
        return self._loader.get_primary_metrics(key)

    def excluded_metrics(self, sector: str | SectorEnum) -> list[str]:
        key = sector.value if isinstance(sector, SectorEnum) else sector
        return self._loader.get_excluded_metrics(key)

    def valuation_metrics(self, sector: str | SectorEnum) -> list[str]:
        key = sector.value if isinstance(sector, SectorEnum) else sector
        return self._loader.get_valuation_metrics(key)

    def observation_rules(self, sector: str | SectorEnum) -> dict[str, Any]:
        key = sector.value if isinstance(sector, SectorEnum) else sector
        return self._loader.get_observation_rules(key)

    def map_industry(self, industry_text: str) -> SectorEnum:
        return self._mapper.map(industry_text)

    def is_financial_sector(self, sector: str | SectorEnum) -> bool:
        key = sector.value if isinstance(sector, SectorEnum) else sector
        return key in ("BANKING", "NBFC", "INSURANCE")

    def all_sectors(self) -> list[str]:
        return self._loader.all_sector_names()
