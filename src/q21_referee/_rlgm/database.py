# Area: RLGM
# PRD: docs/prd-rlgm.md
"""
q21_referee._rlgm.database — Database Initialization
====================================================

Handles SQLite database initialization and connection management
for RLGM state persistence.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("q21_referee.rlgm.database")

# Path to schema file
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path: str = "rlgm.db") -> sqlite3.Connection:
    """
    Get a database connection.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        SQLite connection with row factory set
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: str = "rlgm.db") -> None:
    """
    Initialize the database with schema.

    Args:
        db_path: Path to the SQLite database file
    """
    conn = get_connection(db_path)
    try:
        with open(SCHEMA_PATH, "r") as f:
            schema = f.read()
        conn.executescript(schema)
        conn.commit()
        logger.info(f"Database initialized at {db_path}")
    finally:
        conn.close()


class BaseRepository:
    """
    Base class for database repositories.

    Provides common database operations and connection management.
    """

    def __init__(self, db_path: str = "rlgm.db"):
        """
        Initialize repository.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        return get_connection(self.db_path)

    def _execute(
        self, query: str, params: tuple = (), fetch: bool = False
    ) -> Optional[list]:
        """
        Execute a query.

        Args:
            query: SQL query string
            params: Query parameters
            fetch: If True, fetch and return results

        Returns:
            Query results if fetch=True, else None
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(query, params)
            if fetch:
                return [dict(row) for row in cursor.fetchall()]
            conn.commit()
            return None
        finally:
            conn.close()

    def _execute_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Execute query and return single result."""
        results = self._execute(query, params, fetch=True)
        return results[0] if results else None
