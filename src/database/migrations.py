"""Schema migration tracking — simple version table approach."""

from __future__ import annotations
import logging

import duckdb

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1


def ensure_migrations_table(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            applied_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            description VARCHAR NOT NULL
        )
    """)


def get_current_version(conn: duckdb.DuckDBPyConnection) -> int:
    ensure_migrations_table(conn)
    row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return row[0] if row and row[0] is not None else 0


def run_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    ensure_migrations_table(conn)
    current = get_current_version(conn)
    logger.info("Current schema version: %d, target: %d", current, CURRENT_SCHEMA_VERSION)

    if current < 1:
        _migration_1(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, description) VALUES (1, ?)",
            ["Initial schema — all core tables"],
        )
        logger.info("Applied migration 1")


def _migration_1(conn: duckdb.DuckDBPyConnection) -> None:
    """Initial schema is handled by schema.py create_all_tables."""
    pass
