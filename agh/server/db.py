"""SQLite connection and migration helpers for the AGH server."""

from __future__ import annotations

import logging
import os
import sqlite3
import shutil
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

DATABASE_FILENAME = "agh.sqlite3"
MIGRATIONS_PACKAGE = "agh.server.migrations"
LOGGER = logging.getLogger(__name__)
LEGACY_PACKAGE_ID_PREFIX = "pack_"
PACKAGE_ID_PREFIX = "pkg_"
LEGACY_PACKAGE_VERSION_ID_PREFIX = "packv_"
PACKAGE_VERSION_ID_PREFIX = "pkgv_"
LEGACY_RELATIVE_PACKAGE_STORAGE_PREFIX = "packs/"
RELATIVE_PACKAGE_STORAGE_PREFIX = "packages/"
LEGACY_PACKAGE_STORAGE_SEGMENT = "/packs/"
PACKAGE_STORAGE_SEGMENT = "/packages/"
PACKAGE_STORAGE_SQL_SUFFIX_START = len(LEGACY_RELATIVE_PACKAGE_STORAGE_PREFIX) + 1


@dataclass(frozen=True)
class PackageConflictKey:
    """A concrete target-table key that must not already exist."""

    columns: tuple[str, ...]
    values: tuple[object, ...]

    @classmethod
    def single(cls, column: str, value: object) -> PackageConflictKey:
        return cls((column,), (value,))

    @classmethod
    def pair(
        cls,
        first_column: str,
        first_value: object,
        second_column: str,
        second_value: object,
    ) -> PackageConflictKey:
        return cls((first_column, second_column), (first_value, second_value))

    def where_clause(self) -> str:
        return " AND ".join(f"{column} = ?" for column in self.columns)

    def params(self) -> tuple[object, ...]:
        return self.values

    def describe(self) -> str:
        return ", ".join(
            f"{column}={value!r}" for column, value in zip(self.columns, self.values)
        )


@dataclass(frozen=True)
class PackageMigrationPackageRow:
    """Package row mapped from legacy storage to the canonical schema."""

    id: str
    domain: str
    name: str
    created_by: str
    created_at: str

    @classmethod
    def from_legacy(cls, legacy: sqlite3.Row) -> PackageMigrationPackageRow:
        return cls(
            id=_rewrite_package_id(legacy["id"]),
            domain=legacy["domain"],
            name=legacy["name"],
            created_by=legacy["created_by"],
            created_at=legacy["created_at"],
        )

    @property
    def domain_name_key(self) -> tuple[str, str]:
        return (self.domain, self.name)

    def insert_values(self) -> tuple[str, str, str, str, str]:
        return (self.id, self.domain, self.name, self.created_by, self.created_at)


@dataclass(frozen=True)
class PackageMigrationVersionRow:
    """Package-version row mapped from legacy storage to the canonical schema."""

    id: str
    package_id: str
    version: str
    manifest_json: str
    storage_path: str
    created_at: str
    checksum: str

    @classmethod
    def from_legacy(cls, legacy: sqlite3.Row) -> PackageMigrationVersionRow:
        return cls(
            id=_rewrite_package_version_id(legacy["id"]),
            package_id=_rewrite_package_id(legacy["pack_id"]),
            version=legacy["version"],
            manifest_json=legacy["manifest_json"],
            storage_path=_rewrite_package_storage_path(legacy["storage_path"]),
            created_at=legacy["created_at"],
            checksum=legacy["checksum"],
        )

    @property
    def package_version_key(self) -> tuple[str, str]:
        return (self.package_id, self.version)

    def insert_values(self) -> tuple[str, str, str, str, str, str, str]:
        return (
            self.id,
            self.package_id,
            self.version,
            self.manifest_json,
            self.storage_path,
            self.created_at,
            self.checksum,
        )


@dataclass(frozen=True)
class ProjectPackageMigrationRow:
    """Project-package assignment row mapped from legacy storage."""

    id: str
    project_id: str
    package_id: str
    version_ref: str
    position: int
    active: int
    created_at: str

    @classmethod
    def from_legacy(cls, legacy: sqlite3.Row) -> ProjectPackageMigrationRow:
        return cls(
            id=legacy["id"],
            project_id=legacy["project_id"],
            package_id=_rewrite_package_id(legacy["pack_id"]),
            version_ref=legacy["version_ref"],
            position=legacy["position"],
            active=legacy["active"],
            created_at=legacy["created_at"],
        )

    @property
    def project_package_key(self) -> tuple[str, str]:
        return (self.project_id, self.package_id)

    def insert_values(self) -> tuple[str, str, str, str, int, int, str]:
        return (
            self.id,
            self.project_id,
            self.package_id,
            self.version_ref,
            self.position,
            self.active,
            self.created_at,
        )


@dataclass(frozen=True)
class PackageTableMigrationPlan:
    """Rows to copy from legacy schema into canonical package tables."""

    packages: list[PackageMigrationPackageRow]
    package_versions: list[PackageMigrationVersionRow]
    project_packages: list[ProjectPackageMigrationRow]

    def insert_rows(self) -> dict[str, list[tuple[object, ...]]]:
        return {
            "packages": [package.insert_values() for package in self.packages],
            "package_versions": [
                version.insert_values() for version in self.package_versions
            ],
            "project_packages": [
                assignment.insert_values() for assignment in self.project_packages
            ],
        }

    def inserted_ids(self) -> dict[str, list[str]]:
        return {
            "packages": [package.id for package in self.packages],
            "package_versions": [version.id for version in self.package_versions],
            "project_packages": [assignment.id for assignment in self.project_packages],
        }


def get_data_dir() -> Path:
    """Return the AGH data directory."""
    return Path(os.environ.get("AGH_DATA_DIR", ".agh-data"))


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
    data_dir = _migration_data_dir(connection_or_path) if owns_connection else None
    _configure_connection(connection)

    try:
        _ensure_schema_migrations_table(connection)
        connection.execute("BEGIN IMMEDIATE")
        try:
            applied_versions = _applied_versions(connection)
            for version, sql in _iter_migrations():
                if version in applied_versions:
                    continue
                _apply_migration(connection, version, sql, data_dir=data_dir)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
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


def _apply_migration(
    connection: sqlite3.Connection, version: str, sql: str, *, data_dir: Path | None
) -> None:
    """Apply one migration atomically and record its version."""
    connection.execute("SAVEPOINT agh_migration")
    try:
        if version == "003_rename_packs_to_packages":
            _apply_package_rename_migration(connection, data_dir=data_dir)
        else:
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


def _migration_data_dir(connection_or_path: Path | str | None) -> Path | None:
    if connection_or_path is None:
        return get_data_dir()
    db_path = Path(connection_or_path)
    if str(db_path) == ":memory:":
        return None
    return db_path.parent


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _apply_package_rename_migration(
    connection: sqlite3.Connection, *, data_dir: Path | None
) -> None:
    has_legacy_tables = _table_exists(connection, "packs")
    LOGGER.info(
        "Starting package rename migration",
        extra={"legacy_tables": has_legacy_tables, "data_dir": str(data_dir)},
    )
    try:
        migration_plan = (
            _build_package_table_migration_plan(connection)
            if has_legacy_tables
            else None
        )
        _validate_package_storage_preflight(data_dir=data_dir)
        if has_legacy_tables:
            assert migration_plan is not None
            _migrate_package_tables(connection, plan=migration_plan)
        _repair_package_storage(connection, data_dir=data_dir)
    except Exception:
        LOGGER.exception(
            "Package rename migration failed; database changes will roll back. "
            "Filesystem moves are rollback-safe; resolve the reported conflict and "
            "retry startup."
        )
        raise
    LOGGER.info("Package rename migration completed")


def _migrate_package_tables(
    connection: sqlite3.Connection, *, plan: PackageTableMigrationPlan
) -> None:
    _execute_migration_sql(connection, _PACKAGE_TABLES_SQL)
    before_counts = {
        "packages": _table_row_count(connection, "packages"),
        "package_versions": _table_row_count(connection, "package_versions"),
        "project_packages": _table_row_count(connection, "project_packages"),
    }

    insert_rows = plan.insert_rows()
    connection.executemany(
        """
        INSERT INTO packages (id, domain, name, created_by, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        insert_rows["packages"],
    )
    connection.executemany(
        """
        INSERT INTO package_versions
            (id, package_id, version, manifest_json, storage_path, created_at, checksum)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        insert_rows["package_versions"],
    )
    connection.executemany(
        """
        INSERT INTO project_packages
            (id, project_id, package_id, version_ref, position, active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        insert_rows["project_packages"],
    )
    _validate_inserted_row_counts(connection, before_counts, plan)
    _validate_migrated_keys(connection, plan)
    _execute_migration_sql(
        connection,
        """
        DROP TABLE project_packs;
        DROP TABLE pack_versions;
        DROP TABLE packs;
        """,
    )


_PACKAGE_TABLES_SQL = """
        CREATE TABLE IF NOT EXISTS packages (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            name TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (domain, name),
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS package_versions (
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

        CREATE TABLE IF NOT EXISTS project_packages (
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


def _build_package_table_migration_plan(
    connection: sqlite3.Connection,
) -> PackageTableMigrationPlan:
    package_rows = [
        PackageMigrationPackageRow.from_legacy(row)
        for row in connection.execute(
            "SELECT id, domain, name, created_by, created_at FROM packs"
        ).fetchall()
    ]
    package_ids = {package.id for package in package_rows}
    version_rows = [
        PackageMigrationVersionRow.from_legacy(row)
        for row in connection.execute(
            """
            SELECT id, pack_id, version, manifest_json, storage_path, created_at, checksum
            FROM pack_versions
            """
        ).fetchall()
    ]
    assignment_rows = [
        ProjectPackageMigrationRow.from_legacy(row)
        for row in connection.execute(
            """
            SELECT id, project_id, pack_id, version_ref, position, active, created_at
            FROM project_packs
            """
        ).fetchall()
    ]

    _validate_package_migration_plan(
        connection,
        package_rows=package_rows,
        version_rows=version_rows,
        assignment_rows=assignment_rows,
        package_ids=package_ids,
    )
    return PackageTableMigrationPlan(
        packages=package_rows,
        package_versions=version_rows,
        project_packages=assignment_rows,
    )


def _validate_package_migration_plan(
    connection: sqlite3.Connection,
    *,
    package_rows: list[PackageMigrationPackageRow],
    version_rows: list[PackageMigrationVersionRow],
    assignment_rows: list[ProjectPackageMigrationRow],
    package_ids: set[str],
) -> None:
    _reject_duplicate_keys("packages.id", [package.id for package in package_rows])
    _reject_duplicate_keys(
        "packages.domain/name", [package.domain_name_key for package in package_rows]
    )
    _reject_duplicate_keys(
        "package_versions.id", [version.id for version in version_rows]
    )
    _reject_duplicate_keys(
        "package_versions.package/version",
        [version.package_version_key for version in version_rows],
    )
    _reject_duplicate_keys(
        "project_packages.id", [assignment.id for assignment in assignment_rows]
    )
    _reject_duplicate_keys(
        "project_packages.project/package",
        [assignment.project_package_key for assignment in assignment_rows],
    )
    missing_version_packages = sorted(
        {version.package_id for version in version_rows} - package_ids
    )
    if missing_version_packages:
        _raise_package_migration_conflict(
            "package_versions reference missing packages: "
            f"{', '.join(missing_version_packages)}"
        )
    missing_assignment_packages = sorted(
        {assignment.package_id for assignment in assignment_rows} - package_ids
    )
    if missing_assignment_packages:
        _raise_package_migration_conflict(
            "project_packages reference missing packages: "
            f"{', '.join(missing_assignment_packages)}"
        )

    _reject_existing_package_conflicts(
        connection,
        table="packages",
        keys=[PackageConflictKey.single("id", package.id) for package in package_rows],
    )
    _reject_existing_package_conflicts(
        connection,
        table="packages",
        keys=[
            PackageConflictKey.pair("domain", package.domain, "name", package.name)
            for package in package_rows
        ],
    )
    _reject_existing_package_conflicts(
        connection,
        table="package_versions",
        keys=[PackageConflictKey.single("id", version.id) for version in version_rows],
    )
    _reject_existing_package_conflicts(
        connection,
        table="package_versions",
        keys=[
            PackageConflictKey.pair(
                "package_id", version.package_id, "version", version.version
            )
            for version in version_rows
        ],
    )
    _reject_existing_package_conflicts(
        connection,
        table="project_packages",
        keys=[
            PackageConflictKey.single("id", assignment.id)
            for assignment in assignment_rows
        ],
    )
    _reject_existing_package_conflicts(
        connection,
        table="project_packages",
        keys=[
            PackageConflictKey.pair(
                "project_id", assignment.project_id, "package_id", assignment.package_id
            )
            for assignment in assignment_rows
        ],
    )


def _reject_duplicate_keys(label: str, keys: list[object]) -> None:
    seen: set[object] = set()
    duplicates: set[object] = set()
    for key in keys:
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    if duplicates:
        _raise_package_migration_conflict(f"duplicate mapped {label}: {duplicates}")


def _reject_existing_package_conflicts(
    connection: sqlite3.Connection, *, table: str, keys: list[PackageConflictKey]
) -> None:
    if not _table_exists(connection, table):
        return
    for key in keys:
        row = connection.execute(
            f"SELECT 1 FROM {table} WHERE {key.where_clause()}", key.params()
        ).fetchone()
        if row is not None:
            _raise_package_migration_conflict(
                f"target {table} already contains mapped key {key.describe()}"
            )


def _validate_inserted_row_counts(
    connection: sqlite3.Connection,
    before_counts: dict[str, int],
    plan: PackageTableMigrationPlan,
) -> None:
    for table, rows in plan.insert_rows().items():
        expected = before_counts[table] + len(rows)
        actual = _table_row_count(connection, table)
        if actual != expected:
            _raise_package_migration_conflict(
                f"{table} migration row count mismatch: expected {expected}, got {actual}"
            )


def _validate_migrated_keys(
    connection: sqlite3.Connection, plan: PackageTableMigrationPlan
) -> None:
    for table, ids in plan.inserted_ids().items():
        for key in ids:
            if (
                connection.execute(
                    f"SELECT 1 FROM {table} WHERE id = ?", (key,)
                ).fetchone()
                is None
            ):
                _raise_package_migration_conflict(
                    f"{table} missing migrated key after insert: {key}"
                )


def _table_row_count(connection: sqlite3.Connection, table: str) -> int:
    if not _table_exists(connection, table):
        return 0
    row = connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
    return int(row["total"])


def _rewrite_package_id(value: str) -> str:
    return _rewrite_prefixed_value(
        value,
        legacy_prefix=LEGACY_PACKAGE_ID_PREFIX,
        canonical_prefix=PACKAGE_ID_PREFIX,
    )


def _rewrite_package_version_id(value: str) -> str:
    return _rewrite_prefixed_value(
        value,
        legacy_prefix=LEGACY_PACKAGE_VERSION_ID_PREFIX,
        canonical_prefix=PACKAGE_VERSION_ID_PREFIX,
    )


def _rewrite_package_storage_path(value: str) -> str:
    if value.startswith(LEGACY_RELATIVE_PACKAGE_STORAGE_PREFIX):
        suffix = value.removeprefix(LEGACY_RELATIVE_PACKAGE_STORAGE_PREFIX)
        return f"{RELATIVE_PACKAGE_STORAGE_PREFIX}{suffix}"
    return value.replace(LEGACY_PACKAGE_STORAGE_SEGMENT, PACKAGE_STORAGE_SEGMENT)


def _rewrite_prefixed_value(
    value: str, *, legacy_prefix: str, canonical_prefix: str
) -> str:
    if not value.startswith(legacy_prefix):
        return value
    return f"{canonical_prefix}{value.removeprefix(legacy_prefix)}"


def _raise_package_migration_conflict(message: str) -> None:
    raise RuntimeError(f"package migration conflict: {message}")


def _validate_package_storage_preflight(*, data_dir: Path | None) -> None:
    if data_dir is None:
        return
    old_root = data_dir / "packs"
    new_root = data_dir / "packages"
    if not old_root.exists():
        return
    if old_root.is_symlink():
        raise RuntimeError(f"refusing to migrate symlinked package storage: {old_root}")
    if not old_root.is_dir():
        raise RuntimeError(f"legacy package storage is not a directory: {old_root}")
    if not new_root.exists():
        return
    if new_root.is_symlink() or not new_root.is_dir():
        raise RuntimeError(f"package storage target is unsafe: {new_root}")
    for child in sorted(old_root.iterdir(), key=lambda path: path.name):
        if child.is_symlink():
            raise RuntimeError(
                f"refusing to migrate symlinked package storage: {child}"
            )
        target = new_root / child.name
        if target.exists():
            _validate_existing_package_storage_target(source=child, target=target)


def _validate_existing_package_storage_target(*, source: Path, target: Path) -> None:
    if source.is_symlink() or target.is_symlink():
        raise RuntimeError(f"package storage target is unsafe: {target}")
    if _is_empty_directory_tree(source):
        return
    if _is_empty_directory_tree(target):
        return
    if _package_storage_paths_are_identical(source=source, target=target):
        return
    raise RuntimeError(f"package storage target already exists: {target}")


def _repair_package_storage(
    connection: sqlite3.Connection, *, data_dir: Path | None
) -> None:
    connection.execute(
        """
        UPDATE package_versions
        SET storage_path = CASE
            WHEN storage_path LIKE ? THEN ? || substr(storage_path, ?)
            ELSE replace(storage_path, ?, ?)
        END
        WHERE storage_path LIKE ? OR storage_path LIKE ?
        """,
        (
            f"{LEGACY_RELATIVE_PACKAGE_STORAGE_PREFIX}%",
            RELATIVE_PACKAGE_STORAGE_PREFIX,
            PACKAGE_STORAGE_SQL_SUFFIX_START,
            LEGACY_PACKAGE_STORAGE_SEGMENT,
            PACKAGE_STORAGE_SEGMENT,
            f"{LEGACY_RELATIVE_PACKAGE_STORAGE_PREFIX}%",
            f"%{LEGACY_PACKAGE_STORAGE_SEGMENT}%",
        ),
    )
    if data_dir is None:
        return
    old_root = data_dir / "packs"
    new_root = data_dir / "packages"
    if not old_root.exists():
        return
    _move_legacy_package_storage(old_root=old_root, new_root=new_root)


def _move_legacy_package_storage(*, old_root: Path, new_root: Path) -> None:
    created_target_root = False
    moved: list[tuple[Path, Path]] = []
    if not new_root.exists():
        new_root.mkdir(parents=True)
        created_target_root = True
    try:
        for child in sorted(old_root.iterdir(), key=lambda path: path.name):
            target = new_root / child.name
            if child.is_symlink():
                raise RuntimeError(
                    f"refusing to migrate symlinked package storage: {child}"
                )
            if target.exists():
                source_resolved = _reconcile_existing_package_storage_target(
                    source=child, target=target
                )
                if source_resolved:
                    continue
            moved.append((target, child))
            shutil.move(str(child), str(target))
        old_root.rmdir()
    except Exception:
        _rollback_legacy_package_storage_moves(
            moved=moved, created_target_root=created_target_root, new_root=new_root
        )
        raise


def _rollback_legacy_package_storage_moves(
    *, moved: list[tuple[Path, Path]], created_target_root: bool, new_root: Path
) -> None:
    for target, original in reversed(moved):
        if not target.exists():
            continue
        if original.exists():
            _remove_retry_safe_target_residue(source=original, target=target)
        else:
            shutil.move(str(target), str(original))
    if created_target_root:
        with suppress(OSError):
            new_root.rmdir()


def _reconcile_existing_package_storage_target(*, source: Path, target: Path) -> bool:
    if source.is_symlink() or target.is_symlink():
        raise RuntimeError(f"package storage target is unsafe: {target}")
    if _remove_empty_legacy_storage_residue(source):
        LOGGER.info(
            "Reconciled previously moved package storage target",
            extra={"source": str(source), "target": str(target)},
        )
        return True
    if _remove_empty_package_storage_target(target):
        LOGGER.info(
            "Removed empty package storage target before retrying move",
            extra={"source": str(source), "target": str(target)},
        )
        return False
    if _package_storage_paths_are_identical(source=source, target=target):
        _remove_package_storage_path(source)
        LOGGER.info(
            "Removed legacy package storage residue after equivalence check",
            extra={"source": str(source), "target": str(target)},
        )
        return True
    raise RuntimeError(f"package storage target already exists: {target}")


def _remove_empty_legacy_storage_residue(path: Path) -> bool:
    if path.is_symlink():
        raise RuntimeError(f"refusing to migrate symlinked package storage: {path}")
    if not _is_empty_directory_tree(path):
        return False
    _remove_empty_directory_tree(path)
    return True


def _remove_empty_package_storage_target(path: Path) -> bool:
    if path.is_symlink():
        raise RuntimeError(f"package storage target is unsafe: {path}")
    if not _is_empty_directory_tree(path):
        return False
    _remove_empty_directory_tree(path)
    return True


def _remove_retry_safe_target_residue(*, source: Path, target: Path) -> None:
    if _remove_empty_package_storage_target(target):
        return
    if _package_storage_paths_are_identical(source=source, target=target):
        _remove_package_storage_path(target)


def _is_empty_directory_tree(path: Path) -> bool:
    if path.is_symlink() or not path.is_dir():
        return False
    for child in path.iterdir():
        if child.is_symlink() or not child.is_dir():
            return False
        if not _is_empty_directory_tree(child):
            return False
    return True


def _remove_empty_directory_tree(path: Path) -> None:
    for child in path.iterdir():
        _remove_empty_directory_tree(child)
    path.rmdir()


def _package_storage_paths_are_identical(*, source: Path, target: Path) -> bool:
    return _package_storage_signature(source) == _package_storage_signature(target)


def _package_storage_signature(path: Path) -> dict[Path, tuple[str, bytes]]:
    if path.is_symlink():
        raise RuntimeError(f"refusing to migrate symlinked package storage: {path}")
    if path.is_file():
        return {Path(): ("file", path.read_bytes())}
    if not path.is_dir():
        return {Path(): ("other", str(path.stat().st_mode).encode())}

    signature: dict[Path, tuple[str, bytes]] = {Path(): ("dir", b"")}
    for child in sorted(path.rglob("*")):
        if child.is_symlink():
            raise RuntimeError(
                f"refusing to migrate symlinked package storage: {child}"
            )
        relative = child.relative_to(path)
        if child.is_dir():
            signature[relative] = ("dir", b"")
        elif child.is_file():
            signature[relative] = ("file", child.read_bytes())
        else:
            signature[relative] = ("other", str(child.stat().st_mode).encode())
    return signature


def _remove_package_storage_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
