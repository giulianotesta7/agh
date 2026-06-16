"""SQLite migration tests for AGH server storage."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from agh.server import db
from agh.server.db import connect_database, get_database_path, run_migrations


def table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row[0] for row in rows}


def column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def test_get_database_path_respects_agh_data_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))

    assert get_database_path() == tmp_path / "agh.sqlite3"


def test_run_migrations_creates_initial_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata" / "agh.sqlite3"

    run_migrations(db_path)

    connection = connect_database(db_path)
    try:
        assert table_names(connection) >= {
            "schema_migrations",
            "users",
            "tokens",
            "projects",
            "project_members",
            "packages",
            "package_versions",
            "project_packages",
        }
        token_columns = column_names(connection, "tokens")
        assert "token_hash" in token_columns
        assert "token" not in token_columns

        applied = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert [row[0] for row in applied] == [
            "001_initial_schema",
            "002_unique_project_names",
            "003_rename_packs_to_packages",
        ]
    finally:
        connection.close()


def test_run_migrations_is_safe_for_concurrent_startup(tmp_path: Path) -> None:
    db_path = tmp_path / "agh.sqlite3"

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(run_migrations, db_path) for _ in range(8)]
        for future in futures:
            future.result()

    connection = connect_database(db_path)
    try:
        rows = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert [row[0] for row in rows] == [
            "001_initial_schema",
            "002_unique_project_names",
            "003_rename_packs_to_packages",
        ]
        assert table_names(connection) >= {
            "users",
            "tokens",
            "projects",
            "project_members",
            "packages",
            "package_versions",
            "project_packages",
        }
    finally:
        connection.close()


def test_run_migrations_is_idempotent_on_existing_connection() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        run_migrations(connection)
        run_migrations(connection)

        rows = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert [row[0] for row in rows] == [
            "001_initial_schema",
            "002_unique_project_names",
            "003_rename_packs_to_packages",
        ]
    finally:
        connection.close()


def test_failed_migration_rolls_back_statements_and_version(monkeypatch) -> None:
    connection = sqlite3.connect(":memory:")
    failing_sql = """
    CREATE TABLE partial_migration_table (id TEXT PRIMARY KEY);
    INSERT INTO missing_table (id) VALUES ('boom');
    """
    monkeypatch.setattr(db, "_iter_migrations", lambda: [("999_failing", failing_sql)])

    try:
        with pytest.raises(sqlite3.OperationalError):
            run_migrations(connection)

        assert "partial_migration_table" not in table_names(connection)
        rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
        assert rows == []
    finally:
        connection.close()


def test_project_name_uniqueness_migration_fails_on_existing_duplicates() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        initial_schema = Path("agh/server/migrations/001_initial_schema.sql").read_text(
            encoding="utf-8"
        )
        connection.executescript(initial_schema)
        connection.execute(
            "CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
        )
        connection.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            ("001_initial_schema",),
        )
        connection.executemany(
            """
            INSERT INTO projects (id, name, repo_url, repo_url_normalized)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    "prj_0000000000000001",
                    "Duplicate",
                    "https://github.com/acme/one.git",
                    "github.com/acme/one",
                ),
                (
                    "prj_0000000000000002",
                    "Duplicate",
                    "https://github.com/acme/two.git",
                    "github.com/acme/two",
                ),
            ],
        )
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError):
            run_migrations(connection)

        rows = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert [row[0] for row in rows] == ["001_initial_schema"]
    finally:
        connection.close()


def test_schema_enforces_core_uniqueness_and_foreign_keys() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        run_migrations(connection)
        connection.execute(
            "INSERT INTO users (id, email, role) VALUES (?, ?, ?)",
            ("usr_0000000000000001", "owner@example.com", "owner"),
        )
        connection.execute(
            "INSERT INTO users (id, email, role) VALUES (?, ?, ?)",
            ("usr_0000000000000002", "dev@example.com", "member"),
        )

        try:
            connection.execute(
                "INSERT INTO users (id, email, role) VALUES (?, ?, ?)",
                ("usr_0000000000000003", "owner@example.com", "member"),
            )
        except sqlite3.IntegrityError:
            pass
        else:  # pragma: no cover - assertion failure path
            raise AssertionError("users.email uniqueness was not enforced")

        connection.execute(
            """
            INSERT INTO projects (id, name, repo_url, repo_url_normalized)
            VALUES (?, ?, ?, ?)
            """,
            (
                "prj_0000000000000001",
                "Docs",
                "https://github.com/acme/docs.git",
                "github.com/acme/docs",
            ),
        )
        try:
            connection.execute(
                """
                INSERT INTO projects (id, name, repo_url, repo_url_normalized)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "prj_0000000000000002",
                    "Docs Duplicate",
                    "git@github.com:acme/docs.git",
                    "github.com/acme/docs",
                ),
            )
        except sqlite3.IntegrityError:
            pass
        else:  # pragma: no cover - assertion failure path
            raise AssertionError("active project repo uniqueness was not enforced")

        connection.execute(
            "INSERT INTO packages (id, domain, name, created_by) VALUES (?, ?, ?, ?)",
            ("pkg_0000000000000001", "acme", "onboarding", "usr_0000000000000001"),
        )
        connection.execute(
            """
            INSERT INTO package_versions
                (id, package_id, version, manifest_json, storage_path, checksum)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "pkgv_0000000000000001",
                "pkg_0000000000000001",
                "1.0.0",
                "{}",
                "packages/acme/onboarding/1.0.0",
                "sha256:abc",
            ),
        )
        try:
            connection.execute(
                """
                INSERT INTO package_versions
                    (id, package_id, version, manifest_json, storage_path, checksum)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "pkgv_0000000000000002",
                    "pkg_missing000001",
                    "1.0.0",
                    "{}",
                    "packages/missing/package/1.0.0",
                    "sha256:def",
                ),
            )
        except sqlite3.IntegrityError:
            pass
        else:  # pragma: no cover - assertion failure path
            raise AssertionError(
                "package_versions.package_id foreign key was not enforced"
            )
    finally:
        connection.close()
