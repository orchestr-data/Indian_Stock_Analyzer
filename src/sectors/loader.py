"""Sector configuration loader — reads YAML configs from config/sectors/."""

from __future__ import annotations
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_SECTORS_DIR = Path(__file__).parent.parent.parent / "config" / "sectors"


@lru_cache(maxsize=1)
def _load_all_sector_configs() -> dict[str, dict[str, Any]]:
    """Load all sector YAML files, keyed by sector enum name."""
    configs: dict[str, dict[str, Any]] = {}
    if not _SECTORS_DIR.exists():
        logger.warning("Sectors config directory not found: %s", _SECTORS_DIR)
        return configs

    for yaml_file in _SECTORS_DIR.glob("*.yaml"):
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            sector_key = data.get("sector", yaml_file.stem.upper())
            configs[sector_key] = data
        except Exception as exc:
            logger.error("Failed to load sector config %s: %s", yaml_file, exc)

    logger.info("Loaded %d sector configurations", len(configs))
    return configs


class SectorLoader:
    """Provides access to sector configuration."""

    def get(self, sector: str) -> dict[str, Any]:
        """Return sector config, falling back to DEFAULT."""
        configs = _load_all_sector_configs()
        return configs.get(sector.upper(), configs.get("DEFAULT", {}))

    def get_primary_metrics(self, sector: str) -> list[str]:
        cfg = self.get(sector)
        return cfg.get("primary_metrics", [])

    def get_excluded_metrics(self, sector: str) -> list[str]:
        cfg = self.get(sector)
        return cfg.get("excluded_metrics", [])

    def get_valuation_metrics(self, sector: str) -> list[str]:
        cfg = self.get(sector)
        return cfg.get("valuation_metrics", [])

    def get_observation_rules(self, sector: str) -> dict[str, Any]:
        cfg = self.get(sector)
        return cfg.get("observation_rules", {})

    def get_document_sections_of_interest(self, sector: str) -> list[str]:
        cfg = self.get(sector)
        return cfg.get("document_sections_of_interest", [])

    def all_sector_names(self) -> list[str]:
        return sorted(_load_all_sector_configs().keys())
