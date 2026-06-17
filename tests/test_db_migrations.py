"""SQLite migration tests for AGH server storage."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from agh.server import db
from agh.server.db import connect_database, get_database_path, run_migrations
from agh.common.ids import generate_prefixed_id, is_valid_prefixed_id


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
            "collections",
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
            "004_collections",
            "005_collection_constraints",
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
            "004_collections",
            "005_collection_constraints",
        ]
        assert table_names(connection) >= {
            "users",
            "tokens",
            "projects",
            "project_members",
            "packages",
            "package_versions",
            "project_packages",
            "collections",
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
            "004_collections",
            "005_collection_constraints",
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

        collection_columns = column_names(connection, "collections")
        assert {
            "id",
            "name",
            "description",
            "active",
            "created_by",
        } <= collection_columns

        connection.execute(
            "INSERT INTO collections (id, name, created_by) VALUES (?, ?, ?)",
            ("col_0000000000000001", "Team Skills", "usr_0000000000000001"),
        )
        collection = connection.execute(
            "SELECT description, active FROM collections WHERE id = ?",
            ("col_0000000000000001",),
        ).fetchone()
        assert dict(collection) == {"description": "", "active": 1}

        try:
            connection.execute(
                """
                INSERT INTO collections (id, name, active, created_by)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "col_0000000000000002",
                    "Broken Skills",
                    2,
                    "usr_0000000000000001",
                ),
            )
        except sqlite3.IntegrityError:
            pass
        else:  # pragma: no cover - assertion failure path
            raise AssertionError("collections.active check was not enforced")

        try:
            connection.execute(
                "INSERT INTO collections (id, name, created_by) VALUES (?, ?, ?)",
                ("col_0000000000000003", "Team Skills", "usr_0000000000000001"),
            )
        except sqlite3.IntegrityError:
            pass
        else:  # pragma: no cover - assertion failure path
            raise AssertionError("collections.name uniqueness was not enforced")

        try:
            connection.execute(
                "INSERT INTO collections (id, name, created_by) VALUES (?, ?, ?)",
                ("col_0000000000000004", "Unknown Creator", "usr_missing0000001"),
            )
        except sqlite3.IntegrityError:
            pass
        else:  # pragma: no cover - assertion failure path
            raise AssertionError("collections.created_by foreign key was not enforced")

        try:
            connection.execute(
                "INSERT INTO collections (id, name, description, created_by) VALUES (?, ?, ?, ?)",
                (
                    "col_0000000000000005",
                    "x" * 81,
                    "valid description",
                    "usr_0000000000000001",
                ),
            )
        except sqlite3.IntegrityError:
            pass
        else:  # pragma: no cover - assertion failure path
            raise AssertionError("collections.name length check was not enforced")

        try:
            connection.execute(
                "INSERT INTO collections (id, name, description, created_by) VALUES (?, ?, ?, ?)",
                (
                    "col_0000000000000006",
                    "Long Description",
                    "x" * 1001,
                    "usr_0000000000000001",
                ),
            )
        except sqlite3.IntegrityError:
            pass
        else:  # pragma: no cover - assertion failure path
            raise AssertionError(
                "collections.description length check was not enforced"
            )
    finally:
        connection.close()


def test_collection_id_prefix_is_supported() -> None:
    collection_id = generate_prefixed_id("col")

    assert is_valid_prefixed_id(collection_id, "col")


def _collections_table_sql(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'collections'"
    ).fetchone()
    assert row is not None
    return str(row[0])


def test_collection_constraints_migration_adds_missing_check_constraints() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        # Simulate a database that applied the original 004 migration without
        # length constraints, then run the current migration set.
        connection.executescript(
            Path("agh/server/migrations/001_initial_schema.sql").read_text(
                encoding="utf-8"
            )
        )
        connection.execute(
            """
            CREATE TABLE schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        for version in (
            "001_initial_schema",
            "002_unique_project_names",
            "003_rename_packs_to_packages",
            "004_collections",
        ):
            connection.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)", (version,)
            )
        # Simulate the original 004_collections.sql schema (no length constraints).
        connection.execute(
            """
            CREATE TABLE collections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
            )
            """
        )
        connection.execute(
            "INSERT INTO users (id, email, role) VALUES (?, ?, ?)",
            ("usr_0000000000000001", "owner@example.com", "owner"),
        )
        connection.execute(
            "INSERT INTO collections (id, name, description, created_by) VALUES (?, ?, ?, ?)",
            (
                "col_0000000000000001",
                "Legacy Collection",
                "Exists before constraints",
                "usr_0000000000000001",
            ),
        )
        connection.commit()

        assert "CHECK (length(name) <= 80)" not in _collections_table_sql(connection)
        assert "CHECK (length(description) <= 1000)" not in _collections_table_sql(
            connection
        )

        run_migrations(connection)

        # Existing rows are preserved.
        rows = connection.execute(
            "SELECT id, name, description FROM collections"
        ).fetchall()
        assert [dict(row) for row in rows] == [
            {
                "id": "col_0000000000000001",
                "name": "Legacy Collection",
                "description": "Exists before constraints",
            }
        ]

        # Constraints are now present.
        assert "CHECK (length(name) <= 80)" in _collections_table_sql(connection)
        assert "CHECK (length(description) <= 1000)" in _collections_table_sql(
            connection
        )

        applied = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert [row[0] for row in applied] == [
            "001_initial_schema",
            "002_unique_project_names",
            "003_rename_packs_to_packages",
            "004_collections",
            "005_collection_constraints",
        ]
    finally:
        connection.close()


def _setup_pre_005_collections_database(connection: sqlite3.Connection) -> None:
    """Apply schema through 004 and insert a test user for collection migration tests."""
    connection.executescript(
        Path("agh/server/migrations/001_initial_schema.sql").read_text(encoding="utf-8")
    )
    connection.execute(
        """
        CREATE TABLE schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    for version in (
        "001_initial_schema",
        "002_unique_project_names",
        "003_rename_packs_to_packages",
        "004_collections",
    ):
        connection.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)", (version,)
        )
    # Simulate the original 004_collections.sql schema (no length constraints).
    connection.execute(
        """
        CREATE TABLE collections (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
        )
        """
    )
    connection.execute(
        "INSERT INTO users (id, email, role) VALUES (?, ?, ?)",
        ("usr_0000000000000001", "owner@example.com", "owner"),
    )
    connection.commit()


def test_collection_constraints_migration_fails_on_over_limit_legacy_rows() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        _setup_pre_005_collections_database(connection)
        connection.execute(
            "INSERT INTO collections (id, name, description, created_by) VALUES (?, ?, ?, ?)",
            (
                "col_0000000000000001",
                "x" * 81,
                "valid description",
                "usr_0000000000000001",
            ),
        )
        connection.execute(
            "INSERT INTO collections (id, name, description, created_by) VALUES (?, ?, ?, ?)",
            (
                "col_0000000000000002",
                "valid name",
                "y" * 1001,
                "usr_0000000000000001",
            ),
        )
        connection.execute(
            "INSERT INTO collections (id, name, description, created_by) VALUES (?, ?, ?, ?)",
            (
                "col_0000000000000003",
                "both too long",
                "z" * 1001,
                "usr_0000000000000001",
            ),
        )
        connection.commit()

        with pytest.raises(RuntimeError) as exc_info:
            run_migrations(connection)

        message = str(exc_info.value)
        assert "collection constraints migration would truncate legacy data" in message
        assert "col_0000000000000001" in message
        assert "col_0000000000000002" in message
        assert "col_0000000000000003" in message
        assert "name (81 > 80)" in message
        assert "description (1001 > 1000)" in message
    finally:
        connection.close()


def test_collection_constraints_migration_failure_keeps_original_table_intact() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        _setup_pre_005_collections_database(connection)
        connection.execute(
            "INSERT INTO collections (id, name, description, created_by) VALUES (?, ?, ?, ?)",
            (
                "col_0000000000000001",
                "x" * 81,
                "valid description",
                "usr_0000000000000001",
            ),
        )
        connection.commit()
        original_sql = _collections_table_sql(connection)
        original_rows = connection.execute(
            "SELECT id, name FROM collections"
        ).fetchall()

        with pytest.raises(RuntimeError):
            run_migrations(connection)

        assert "collections" in table_names(connection)
        assert "_collections_new" not in table_names(connection)
        assert _collections_table_sql(connection) == original_sql
        rows = connection.execute("SELECT id, name FROM collections").fetchall()
        assert [tuple(row) for row in rows] == [tuple(row) for row in original_rows]

        applied = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert [row[0] for row in applied] == [
            "001_initial_schema",
            "002_unique_project_names",
            "003_rename_packs_to_packages",
            "004_collections",
        ]
    finally:
        connection.close()


def test_collection_constraints_migration_is_idempotent() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        run_migrations(connection)
        first_sql = _collections_table_sql(connection)

        run_migrations(connection)
        second_sql = _collections_table_sql(connection)

        assert first_sql == second_sql
        assert "CHECK (length(name) <= 80)" in second_sql
        assert "CHECK (length(description) <= 1000)" in second_sql
    finally:
        connection.close()


def test_collection_length_constraints_enforce_exact_boundaries() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        run_migrations(connection)
        connection.execute(
            "INSERT INTO users (id, email, role) VALUES (?, ?, ?)",
            ("usr_0000000000000001", "owner@example.com", "owner"),
        )

        # Exact limit values are accepted.
        connection.execute(
            "INSERT INTO collections (id, name, description, created_by) VALUES (?, ?, ?, ?)",
            (
                "col_0000000000000001",
                "x" * 80,
                "y" * 1000,
                "usr_0000000000000001",
            ),
        )

        # One character over the name limit is rejected.
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO collections (id, name, description, created_by) VALUES (?, ?, ?, ?)",
                (
                    "col_0000000000000002",
                    "x" * 81,
                    "valid description",
                    "usr_0000000000000001",
                ),
            )

        # One character over the description limit is rejected.
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO collections (id, name, description, created_by) VALUES (?, ?, ?, ?)",
                (
                    "col_0000000000000003",
                    "valid name",
                    "y" * 1001,
                    "usr_0000000000000001",
                ),
            )
    finally:
        connection.close()
