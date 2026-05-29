"""SQLite connection and migration helpers for the AGH server."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from importlib import resources
from pathlib import Path

from agh.server.app import get_data_dir

DATABASE_FILENAME = "agh.sqlite3"
MIGRATIONS_PACKAGE = "agh.server.migrations"


def get_database_path(data_dir: Path | str | None = None) -> Path:
    """Return the SQLite database path under the AGH server data root."""
    root = Path(data_dir) if data_dir is not None else get_data_dir()
    return root / DATABASE_FILENAME


def connect_database(path: Path | str | None = None) -> sqlite3.Connection:
    """Open an AGH SQLite connection with project defaults enabled."""
    db_path = Path(path) if path is not None else get_database_path()
    if str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    _configure_connection(connection)
    return connection


def run_migrations(
    connection_or_path: sqlite3.Connection | Path | str | None = None,
) -> None:
    """Apply pending SQL migrations once.

    ``connection_or_path`` may be an existing ``sqlite3.Connection`` or a path to
    a database file. When omitted, the database under ``AGH_DATA_DIR`` is used.
    Applied versions are recorded in ``schema_migrations`` and skipped on later
    calls, making this safe to run at server startup.
    """
    owns_connection = not isinstance(connection_or_path, sqlite3.Connection)
    connection = (
        connect_database(connection_or_path) if owns_connection else connection_or_path
    )
    _configure_connection(connection)

    try:
        _ensure_schema_migrations_table(connection)
        applied_versions = _applied_versions(connection)
        for version, sql in _iter_migrations():
            if version in applied_versions:
                continue
            _apply_migration(connection, version, sql)
    finally:
        if owns_connection:
            connection.close()


def _configure_connection(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")


def _ensure_schema_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    connection.commit()


def _applied_versions(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {row["version"] for row in rows}


def _apply_migration(connection: sqlite3.Connection, version: str, sql: str) -> None:
    """Apply one migration atomically and record its version."""
    connection.execute("SAVEPOINT agh_migration")
    try:
        _execute_migration_sql(connection, sql)
        connection.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            (version,),
        )
    except Exception:
        connection.execute("ROLLBACK TO SAVEPOINT agh_migration")
        connection.execute("RELEASE SAVEPOINT agh_migration")
        raise
    else:
        connection.execute("RELEASE SAVEPOINT agh_migration")


def _execute_migration_sql(connection: sqlite3.Connection, sql: str) -> None:
    """Execute migration SQL statement-by-statement inside caller transaction."""
    pending_statement = ""
    for line in sql.splitlines(keepends=True):
        pending_statement += line
        if sqlite3.complete_statement(pending_statement):
            statement = pending_statement.strip()
            pending_statement = ""
            if statement:
                connection.execute(statement)

    if pending_statement.strip():
        raise sqlite3.OperationalError("incomplete migration SQL statement")


def _iter_migrations() -> Iterable[tuple[str, str]]:
    migration_files = sorted(
        (
            file
            for file in resources.files(MIGRATIONS_PACKAGE).iterdir()
            if file.name.endswith(".sql")
        ),
        key=lambda file: file.name,
    )
    for file in migration_files:
        version = file.name.removesuffix(".sql")
        yield version, file.read_text(encoding="utf-8")
