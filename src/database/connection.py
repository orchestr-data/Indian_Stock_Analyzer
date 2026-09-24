"""DuckDB connection management."""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

import duckdb

from src.config import get_config

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages a single DuckDB connection for the application."""

    def __init__(self, db_path: Optional[str] = None, read_only: bool = False) -> None:
        cfg = get_config()
        self._path = db_path or cfg["database"]["path"]
        self._read_only = read_only
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(self._path, read_only=self._read_only)
            logger.info("Connected to DuckDB at %s", self._path)
        return self._conn

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        return self.connect()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.info("DuckDB connection closed")

    def __enter__(self) -> DatabaseConnection:
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


# Module-level singleton — reused across the Streamlit session
_db: Optional[DatabaseConnection] = None


def get_connection(db_path: Optional[str] = None) -> DatabaseConnection:
    """Return the module-level database connection, creating it if needed."""
    global _db
    if _db is None:
        _db = DatabaseConnection(db_path)
        _db.connect()
        _init_schema(_db)
    return _db


def _init_schema(db: DatabaseConnection) -> None:
    """Run schema initialization on first connect."""
    from src.database.schema import create_all_tables
    create_all_tables(db.conn)
