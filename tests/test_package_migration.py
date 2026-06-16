from __future__ import annotations

import sqlite3
import shutil
from pathlib import Path

import pytest

import agh.server.db as db_module
from agh.server.db import connect_database, run_migrations


def _install_legacy_pack_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member')),
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            repo_url TEXT NOT NULL,
            repo_url_normalized TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE UNIQUE INDEX idx_projects_repo_url_normalized_active
            ON projects(repo_url_normalized) WHERE active = 1;
        CREATE UNIQUE INDEX idx_projects_name_active
            ON projects(name) WHERE active = 1;
        CREATE TABLE packs (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            name TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (domain, name),
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
        );
        CREATE TABLE pack_versions (
            id TEXT PRIMARY KEY,
            pack_id TEXT NOT NULL,
            version TEXT NOT NULL,
            manifest_json TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            checksum TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (pack_id, version),
            FOREIGN KEY (pack_id) REFERENCES packs(id) ON DELETE CASCADE
        );
        CREATE TABLE project_packs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            pack_id TEXT NOT NULL,
            version_ref TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (project_id, pack_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (pack_id) REFERENCES packs(id) ON DELETE CASCADE
        );
        CREATE TABLE schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO schema_migrations (version)
        VALUES ('001_initial_schema'), ('002_unique_project_names');
        """
    )


def _seed_legacy_pack_data(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO users (id, email, role) VALUES (?, ?, ?)",
        ("usr_0000000000000001", "owner@example.com", "owner"),
    )
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
    connection.execute(
        "INSERT INTO packs (id, domain, name, created_by) VALUES (?, ?, ?, ?)",
        ("pack_0000000000000001", "acme", "onboarding", "usr_0000000000000001"),
    )
    connection.execute(
        """
        INSERT INTO pack_versions
            (id, pack_id, version, manifest_json, storage_path, checksum)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "packv_0000000000000001",
            "pack_0000000000000001",
            "1.0.0",
            "{}",
            "packs/acme/onboarding/1.0.0",
            "sha256:abc",
        ),
    )
    connection.execute(
        """
        INSERT INTO project_packs (id, project_id, pack_id, version_ref, position)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "asn_0000000000000001",
            "prj_0000000000000001",
            "pack_0000000000000001",
            "latest",
            3,
        ),
    )
    connection.commit()


def _install_existing_package_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE packages (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            name TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (domain, name),
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
        );
        CREATE TABLE package_versions (
            id TEXT PRIMARY KEY,
            package_id TEXT NOT NULL,
            version TEXT NOT NULL,
            manifest_json TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            checksum TEXT NOT NULL,
            UNIQUE (package_id, version),
            FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE
        );
        CREATE TABLE project_packages (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            package_id TEXT NOT NULL,
            version_ref TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (project_id, package_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE
        );
        """
    )


def _legacy_tables_exist(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM sqlite_master
        WHERE type = 'table' AND name IN ('packs', 'pack_versions', 'project_packs')
        """
    ).fetchone()
    return row["total"] == 3


def test_legacy_pack_tables_migrate_to_package_tables_with_rewritten_ids(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
    finally:
        connection.close()

    run_migrations(db_path)

    connection = connect_database(db_path)
    try:
        package = connection.execute("SELECT * FROM packages").fetchone()
        version = connection.execute("SELECT * FROM package_versions").fetchone()
        assignment = connection.execute("SELECT * FROM project_packages").fetchone()

        assert package["id"] == "pkg_0000000000000001"
        assert version["id"] == "pkgv_0000000000000001"
        assert version["package_id"] == package["id"]
        assert assignment["id"] == "asn_0000000000000001"
        assert assignment["package_id"] == package["id"]
        assert assignment["version_ref"] == "latest"
        assert assignment["position"] == 3
    finally:
        connection.close()


def test_storage_repair_moves_legacy_packs_to_packages_and_rewrites_storage_paths(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
    finally:
        connection.close()
    source = tmp_path / "packs" / "acme" / "onboarding" / "1.0.0"
    source.mkdir(parents=True)
    (source / "agh.package.toml").write_text("legacy artifact", encoding="utf-8")

    run_migrations(db_path)

    target = tmp_path / "packages" / "acme" / "onboarding" / "1.0.0"
    assert not source.exists()
    assert (target / "agh.package.toml").read_text(
        encoding="utf-8"
    ) == "legacy artifact"

    connection = connect_database(db_path)
    try:
        row = connection.execute("SELECT storage_path FROM package_versions").fetchone()
        assert row["storage_path"] == "packages/acme/onboarding/1.0.0"
    finally:
        connection.close()


def test_storage_repair_rolls_back_partial_move_failure_for_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
    finally:
        connection.close()

    first_source = tmp_path / "packs" / "acme"
    second_source = tmp_path / "packs" / "other"
    first_source.mkdir(parents=True)
    second_source.mkdir(parents=True)
    (first_source / "artifact.txt").write_text("first", encoding="utf-8")
    (second_source / "artifact.txt").write_text("second", encoding="utf-8")
    (tmp_path / "packages").mkdir()

    real_move = shutil.move
    move_calls = 0

    def fail_second_move(source: str, target: str) -> str:
        nonlocal move_calls
        move_calls += 1
        if move_calls == 2:
            raise OSError("simulated second move failure")
        return str(real_move(source, target))

    monkeypatch.setattr(db_module.shutil, "move", fail_second_move)

    with pytest.raises(OSError, match="simulated second move failure"):
        run_migrations(db_path)

    assert (tmp_path / "packs" / "acme" / "artifact.txt").read_text(
        encoding="utf-8"
    ) == "first"
    assert (tmp_path / "packs" / "other" / "artifact.txt").read_text(
        encoding="utf-8"
    ) == "second"
    assert not (tmp_path / "packages" / "acme").exists()

    connection = connect_database(db_path)
    try:
        assert _legacy_tables_exist(connection)
        assert (
            connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                ("003_rename_packs_to_packages",),
            ).fetchone()
            is None
        )
    finally:
        connection.close()

    monkeypatch.setattr(db_module.shutil, "move", real_move)
    run_migrations(db_path)

    assert not (tmp_path / "packs").exists()
    assert (tmp_path / "packages" / "acme" / "artifact.txt").read_text(
        encoding="utf-8"
    ) == "first"
    assert (tmp_path / "packages" / "other" / "artifact.txt").read_text(
        encoding="utf-8"
    ) == "second"


def test_storage_repair_reconciles_crash_interrupted_partial_move_on_retry(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
    finally:
        connection.close()

    moved_target = tmp_path / "packages" / "acme" / "onboarding" / "1.0.0"
    moved_target.mkdir(parents=True)
    (moved_target / "agh.package.toml").write_text(
        "moved before crash", encoding="utf-8"
    )
    empty_source_residue = tmp_path / "packs" / "acme"
    empty_source_residue.mkdir(parents=True)
    remaining_source = tmp_path / "packs" / "other"
    remaining_source.mkdir(parents=True)
    (remaining_source / "artifact.txt").write_text("still legacy", encoding="utf-8")

    run_migrations(db_path)

    assert not (tmp_path / "packs").exists()
    assert (moved_target / "agh.package.toml").read_text(encoding="utf-8") == (
        "moved before crash"
    )
    assert (tmp_path / "packages" / "other" / "artifact.txt").read_text(
        encoding="utf-8"
    ) == "still legacy"

    connection = connect_database(db_path)
    try:
        row = connection.execute("SELECT storage_path FROM package_versions").fetchone()
        assert row["storage_path"] == "packages/acme/onboarding/1.0.0"
        assert not _legacy_tables_exist(connection)
    finally:
        connection.close()


def test_storage_repair_removes_empty_target_and_retries_legacy_source_move(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
    finally:
        connection.close()

    source = tmp_path / "packs" / "acme"
    target = tmp_path / "packages" / "acme"
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    (source / "artifact.txt").write_text("legacy data", encoding="utf-8")

    run_migrations(db_path)

    assert not source.exists()
    assert (target / "artifact.txt").read_text(encoding="utf-8") == "legacy data"


def test_storage_repair_removes_identical_non_empty_legacy_source_residue(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
    finally:
        connection.close()

    source = tmp_path / "packs" / "acme"
    target = tmp_path / "packages" / "acme"
    source_nested = source / "onboarding" / "1.0.0"
    target_nested = target / "onboarding" / "1.0.0"
    source_nested.mkdir(parents=True)
    target_nested.mkdir(parents=True)
    (source_nested / "agh.package.toml").write_text("same", encoding="utf-8")
    (target_nested / "agh.package.toml").write_text("same", encoding="utf-8")

    run_migrations(db_path)

    assert not source.exists()
    assert (target_nested / "agh.package.toml").read_text(encoding="utf-8") == "same"


def test_storage_repair_fails_closed_on_different_source_and_target_content(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
    finally:
        connection.close()

    source = tmp_path / "packs" / "acme"
    target = tmp_path / "packages" / "acme"
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    (source / "artifact.txt").write_text("legacy", encoding="utf-8")
    (target / "artifact.txt").write_text("different", encoding="utf-8")

    with pytest.raises(RuntimeError, match="package storage target already exists"):
        run_migrations(db_path)

    assert (source / "artifact.txt").read_text(encoding="utf-8") == "legacy"
    assert (target / "artifact.txt").read_text(encoding="utf-8") == "different"

    connection = connect_database(db_path)
    try:
        assert _legacy_tables_exist(connection)
        assert (
            connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                ("003_rename_packs_to_packages",),
            ).fetchone()
            is None
        )
    finally:
        connection.close()


def test_storage_repair_rolls_back_when_legacy_root_removal_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
    finally:
        connection.close()

    source = tmp_path / "packs" / "acme"
    source.mkdir(parents=True)
    (source / "artifact.txt").write_text("legacy", encoding="utf-8")
    (tmp_path / "packages").mkdir()

    real_rmdir = Path.rmdir

    def fail_legacy_root_rmdir(path: Path) -> None:
        if path == tmp_path / "packs":
            raise OSError("simulated legacy root rmdir failure")
        real_rmdir(path)

    monkeypatch.setattr(Path, "rmdir", fail_legacy_root_rmdir)

    with pytest.raises(OSError, match="simulated legacy root rmdir failure"):
        run_migrations(db_path)

    assert (tmp_path / "packs" / "acme" / "artifact.txt").read_text(
        encoding="utf-8"
    ) == "legacy"
    assert not (tmp_path / "packages" / "acme").exists()

    connection = connect_database(db_path)
    try:
        assert _legacy_tables_exist(connection)
        assert (
            connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                ("003_rename_packs_to_packages",),
            ).fetchone()
            is None
        )
    finally:
        connection.close()


def test_storage_repair_preserves_different_partial_target_when_move_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
    finally:
        connection.close()

    source = tmp_path / "packs" / "acme"
    source.mkdir(parents=True)
    (source / "artifact.txt").write_text("legacy", encoding="utf-8")
    (tmp_path / "packages").mkdir()

    def fail_after_partial_target(source_path: str, target_path: str) -> str:
        target = Path(target_path)
        target.mkdir(parents=True)
        (target / "artifact.txt").write_text("partial", encoding="utf-8")
        raise OSError("simulated cross-device copy failure")

    monkeypatch.setattr(db_module.shutil, "move", fail_after_partial_target)

    with pytest.raises(OSError, match="simulated cross-device copy failure"):
        run_migrations(db_path)

    assert (tmp_path / "packs" / "acme" / "artifact.txt").read_text(
        encoding="utf-8"
    ) == "legacy"
    assert (tmp_path / "packages" / "acme" / "artifact.txt").read_text(
        encoding="utf-8"
    ) == "partial"

    connection = connect_database(db_path)
    try:
        assert _legacy_tables_exist(connection)
        assert (
            connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                ("003_rename_packs_to_packages",),
            ).fetchone()
            is None
        )
    finally:
        connection.close()


def test_package_table_id_collision_fails_closed_and_preserves_legacy_data(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
        _install_existing_package_schema(connection)
        connection.execute(
            "INSERT INTO packages (id, domain, name, created_by) VALUES (?, ?, ?, ?)",
            ("pkg_0000000000000001", "acme", "conflict", "usr_0000000000000001"),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(RuntimeError, match="package migration conflict"):
        run_migrations(db_path)

    connection = connect_database(db_path)
    try:
        assert _legacy_tables_exist(connection)
        legacy = connection.execute("SELECT * FROM packs").fetchall()
        assert [row["id"] for row in legacy] == ["pack_0000000000000001"]
        target = connection.execute("SELECT * FROM packages").fetchall()
        assert [(row["id"], row["name"]) for row in target] == [
            ("pkg_0000000000000001", "conflict")
        ]
        assert (
            connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                ("003_rename_packs_to_packages",),
            ).fetchone()
            is None
        )
    finally:
        connection.close()


def test_package_table_collision_preserves_identical_legacy_storage_residue(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
        _install_existing_package_schema(connection)
        connection.execute(
            "INSERT INTO packages (id, domain, name, created_by) VALUES (?, ?, ?, ?)",
            ("pkg_0000000000000001", "acme", "conflict", "usr_0000000000000001"),
        )
        connection.commit()
    finally:
        connection.close()

    source = tmp_path / "packs" / "acme"
    target = tmp_path / "packages" / "acme"
    source_nested = source / "onboarding" / "1.0.0"
    target_nested = target / "onboarding" / "1.0.0"
    source_nested.mkdir(parents=True)
    target_nested.mkdir(parents=True)
    (source_nested / "agh.package.toml").write_text("same", encoding="utf-8")
    (target_nested / "agh.package.toml").write_text("same", encoding="utf-8")

    with pytest.raises(RuntimeError, match="package migration conflict"):
        run_migrations(db_path)

    assert (source_nested / "agh.package.toml").read_text(encoding="utf-8") == "same"
    assert (target_nested / "agh.package.toml").read_text(encoding="utf-8") == "same"

    connection = connect_database(db_path)
    try:
        assert _legacy_tables_exist(connection)
        assert (
            connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                ("003_rename_packs_to_packages",),
            ).fetchone()
            is None
        )
    finally:
        connection.close()


def test_package_table_collision_preserves_empty_target_retry_state(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "agh.sqlite3"
    connection = connect_database(db_path)
    try:
        _install_legacy_pack_schema(connection)
        _seed_legacy_pack_data(connection)
        _install_existing_package_schema(connection)
        connection.execute(
            "INSERT INTO packages (id, domain, name, created_by) VALUES (?, ?, ?, ?)",
            ("pkg_0000000000000001", "acme", "conflict", "usr_0000000000000001"),
        )
        connection.commit()
    finally:
        connection.close()

    source = tmp_path / "packs" / "acme"
    target = tmp_path / "packages" / "acme"
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    (source / "artifact.txt").write_text("legacy data", encoding="utf-8")

    with pytest.raises(RuntimeError, match="package migration conflict"):
        run_migrations(db_path)

    assert (source / "artifact.txt").read_text(encoding="utf-8") == "legacy data"
    assert target.exists()
    assert list(target.iterdir()) == []

    connection = connect_database(db_path)
    try:
        assert _legacy_tables_exist(connection)
        assert (
            connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                ("003_rename_packs_to_packages",),
            ).fetchone()
            is None
        )
    finally:
        connection.close()
