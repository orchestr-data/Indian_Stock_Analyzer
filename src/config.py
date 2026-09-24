"""Application configuration loader."""

from __future__ import annotations
import logging
import logging.config
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent


@lru_cache(maxsize=1)
def get_config() -> dict[str, Any]:
    """Load and cache the main application config."""
    cfg_path = _PROJECT_ROOT / "config" / "app.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg


@lru_cache(maxsize=1)
def get_thresholds() -> dict[str, Any]:
    """Load and cache the heuristic thresholds config."""
    cfg_path = _PROJECT_ROOT / "config" / "thresholds.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_data_root() -> Path:
    cfg = get_config()
    p = Path(cfg["paths"]["data_root"])
    if not p.is_absolute():
        p = _PROJECT_ROOT / p
    return p


def get_db_path() -> Path:
    cfg = get_config()
    p = Path(cfg["database"]["path"])
    if not p.is_absolute():
        p = _PROJECT_ROOT / p
    return p


def get_raw_data_path() -> Path:
    cfg = get_config()
    p = Path(cfg["paths"]["raw_data"])
    if not p.is_absolute():
        p = _PROJECT_ROOT / p
    return p


def get_companies_path() -> Path:
    cfg = get_config()
    p = Path(cfg["paths"]["companies"])
    if not p.is_absolute():
        p = _PROJECT_ROOT / p
    return p


def setup_logging() -> None:
    """Configure application logging."""
    cfg = get_config()
    log_cfg = cfg.get("logging", {})
    level = log_cfg.get("level", "INFO")
    fmt = log_cfg.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logging.basicConfig(level=getattr(logging, level, logging.INFO), format=fmt)
