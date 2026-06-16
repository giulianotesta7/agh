"""Package publish, listing, and file download routes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat as stat_module
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ValidationError

from agh.common.ids import generate_prefixed_id
from agh.common.package_limits import (
    MAX_PACKAGE_FILE_BYTES,
    MAX_PACKAGE_FILES,
    MAX_PACKAGE_PATH_LENGTH,
    MAX_PACKAGE_PUBLISH_BODY_BYTES,
    MAX_PACKAGE_TOTAL_BYTES,
)
from agh.common.package_manifest import (
    PackageManifest,
    PackageManifestError,
    load_package_manifest,
)
from agh.common.validation import (
    PackageVersionRef,
    is_semver,
    is_valid_slug,
    parse_package_version_ref,
)
from agh.server.auth import CurrentUser, get_current_user
from agh.server.db import connect_database

router = APIRouter(prefix="/packages", tags=["packages"])

# Package list, resolve, and file download intentionally form a global authenticated package registry.
# Project membership gates project assignment and pull-manifest access, not read
# access to published package artifacts.

PACKAGE_ARTIFACT_MISSING_DETAIL = "package file not found"
PACKAGE_ARTIFACT_STORAGE_DETAIL = "package artifact storage unavailable"


class PackagePublish(BaseModel):
    files: dict[str, str]


def _connect(request: Request) -> sqlite3.Connection:
    return connect_database(getattr(request.app.state, "db_path", None))


def _publish_data_dir(request: Request) -> Path:
    return Path(request.app.state.data_dir)


def _require_package_publisher(current_user: CurrentUser) -> None:
    if current_user.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _package_version_response(row: sqlite3.Row) -> dict[str, Any]:
    manifest = json.loads(row["manifest_json"])
    return {
        "id": f"{row['domain']}/{row['name']}@{row['version']}",
        "package_id": row["package_id"],
        "domain": row["domain"],
        "name": row["name"],
        "version": row["version"],
        "description": manifest["description"],
        "tags": manifest.get("tags", []),
        "checksum": row["checksum"],
        "created_at": row["created_at"],
    }


def _package_version_resolve_response(row: sqlite3.Row) -> dict[str, str]:
    package_ref = f"{row['domain']}/{row['name']}@{row['version']}"
    return {
        "id": row["version_id"],
        "package_ref": package_ref,
        "domain": row["domain"],
        "name": row["name"],
        "version": row["version"],
    }


def _raise_package_artifact_missing() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=PACKAGE_ARTIFACT_MISSING_DETAIL,
    )


def _raise_package_artifact_storage_unavailable(
    exc: OSError | UnicodeDecodeError,
) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=PACKAGE_ARTIFACT_STORAGE_DETAIL,
    ) from exc


def _read_published_package_file(storage_dir: Path, safe_path: Path) -> str:
    candidate = storage_dir / safe_path
    _require_package_artifact_read_target(storage_dir, candidate)
    try:
        return candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _raise_package_artifact_storage_unavailable(exc)


def _parse_package_version_ref_or_400(value: str) -> PackageVersionRef:
    try:
        return parse_package_version_ref(value, allow_latest=False)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


def _resolve_package_version_ref(
    connection: sqlite3.Connection, package_ref: PackageVersionRef
) -> sqlite3.Row:
    base_query = """
        SELECT package_versions.id AS version_id, packages.domain, packages.name,
               package_versions.version
        FROM package_versions
        JOIN packages ON packages.id = package_versions.package_id
    """
    if package_ref.kind == "id":
        rows = connection.execute(
            f"{base_query} WHERE package_versions.id = ?", (package_ref.value,)
        ).fetchall()
    elif package_ref.kind == "canonical":
        rows = connection.execute(
            f"{base_query} WHERE packages.domain = ? AND packages.name = ? AND package_versions.version = ?",
            (package_ref.domain, package_ref.name, package_ref.version),
        ).fetchall()
    else:
        rows = connection.execute(
            f"{base_query} WHERE packages.name = ? AND package_versions.version = ? ORDER BY packages.domain ASC",
            (package_ref.name, package_ref.version),
        ).fetchall()
    if len(rows) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="package version ref is ambiguous across package domains",
        )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="package version not found"
        )
    return rows[0]


@router.get("")
def list_packages(
    request: Request, current_user: CurrentUser = Depends(get_current_user)
) -> dict[str, list[dict[str, Any]]]:
    connection = _connect(request)
    try:
        rows = connection.execute(
            """
            SELECT packages.id AS package_id, packages.domain, packages.name,
                   package_versions.id AS version_id, package_versions.version,
                   package_versions.manifest_json, package_versions.checksum,
                   package_versions.created_at
            FROM package_versions
            JOIN packages ON packages.id = package_versions.package_id
            ORDER BY packages.domain ASC, packages.name ASC, package_versions.version ASC
            """
        ).fetchall()
        return {"packages": [_package_version_response(row) for row in rows]}
    finally:
        connection.close()


@router.get("/versions:resolve")
def resolve_package_version(
    ref: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    package_ref = _parse_package_version_ref_or_400(ref)
    connection = _connect(request)
    try:
        return _package_version_resolve_response(
            _resolve_package_version_ref(connection, package_ref)
        )
    finally:
        connection.close()


@router.post("", status_code=status.HTTP_201_CREATED)
async def publish_package(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    _require_package_publisher(current_user)
    payload = await _read_package_publish_payload(request)
    data_dir = _publish_data_dir(request)
    packages_root = data_dir / "packages"
    staging_dir = packages_root / ".staging" / generate_prefixed_id("pkgv")
    try:
        _validate_publish_payload(payload.files)
        _ensure_safe_packages_root(packages_root)
        _write_payload_to_staging(staging_dir, payload.files)
        manifest = _validate_staged_package(staging_dir)
        checksum = _package_checksum(staging_dir)
        manifest_json = json.dumps(
            {
                "domain": manifest.domain,
                "name": manifest.name,
                "version": manifest.version,
                "description": manifest.description,
                "tags": manifest.tags,
            },
            sort_keys=True,
        )
        storage_dir = (
            data_dir / "packages" / manifest.domain / manifest.name / manifest.version
        )
        connection = _connect(request)
        try:
            connection.execute("BEGIN IMMEDIATE")
            storage_created = False
            try:
                existing = _find_package_version(
                    connection, manifest.domain, manifest.name, manifest.version
                )
                if existing is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="package version already exists",
                    )
                package_row = connection.execute(
                    "SELECT id FROM packages WHERE domain = ? AND name = ?",
                    (manifest.domain, manifest.name),
                ).fetchone()
                if package_row is None:
                    package_id = generate_prefixed_id("pkg")
                    connection.execute(
                        "INSERT INTO packages (id, domain, name, created_by) VALUES (?, ?, ?, ?)",
                        (package_id, manifest.domain, manifest.name, current_user.id),
                    )
                else:
                    package_id = str(package_row["id"])

                version_id = generate_prefixed_id("pkgv")
                _recover_or_prepare_storage_target(
                    connection, packages_root, storage_dir
                )
                storage_created = True
                _store_staged_package(staging_dir, storage_dir)
                connection.execute(
                    """
                    INSERT INTO package_versions
                        (id, package_id, version, manifest_json, storage_path, checksum)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        package_id,
                        manifest.version,
                        manifest_json,
                        str(storage_dir),
                        checksum,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                if storage_created and storage_dir.exists():
                    shutil.rmtree(storage_dir, ignore_errors=True)
                if "UNIQUE" in str(exc):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="package version already exists",
                    ) from exc
                raise
            except HTTPException:
                connection.rollback()
                raise
            except Exception:
                connection.rollback()
                if storage_created and storage_dir.exists():
                    shutil.rmtree(storage_dir, ignore_errors=True)
                raise
            else:
                connection.commit()
            created = _get_package_version(
                connection, manifest.domain, manifest.name, manifest.version
            )
            return _package_version_response(created)
        finally:
            connection.close()
    except PackageManifestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


@router.get("/{domain}/{name}/versions/{version}/files/{file_path:path}")
def get_package_file(
    domain: str,
    name: str,
    version: str,
    file_path: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    _validate_package_parts(domain, name, version)
    try:
        safe_path = _safe_relative_path(file_path)
    except PackageManifestError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PACKAGE_ARTIFACT_MISSING_DETAIL,
        ) from exc
    connection = _connect(request)
    try:
        row = _find_package_version(connection, domain, name, version)
        if row is None:
            _raise_package_artifact_missing()
        storage_dir = Path(row["storage_path"])
        return Response(
            _read_published_package_file(storage_dir, safe_path),
            media_type="text/plain; charset=utf-8",
        )
    finally:
        connection.close()


def _validate_package_parts(domain: str, name: str, version: str) -> None:
    if not is_valid_slug(domain) or not is_valid_slug(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="package not found"
        )
    try:
        _assert_publish_version(version)
    except PackageManifestError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="package not found"
        ) from exc


def _find_package_version(
    connection: sqlite3.Connection, domain: str, name: str, version: str
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT packages.id AS package_id, packages.domain, packages.name,
               package_versions.id AS version_id, package_versions.version,
               package_versions.manifest_json, package_versions.storage_path,
               package_versions.checksum, package_versions.created_at
        FROM package_versions
        JOIN packages ON packages.id = package_versions.package_id
        WHERE packages.domain = ? AND packages.name = ? AND package_versions.version = ?
        """,
        (domain, name, version),
    ).fetchone()


def _get_package_version(
    connection: sqlite3.Connection, domain: str, name: str, version: str
) -> sqlite3.Row:
    row = _find_package_version(connection, domain, name, version)
    if row is None:
        raise RuntimeError("published package version missing after commit")
    return row


async def _read_package_publish_payload(request: Request) -> PackagePublish:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_PACKAGE_PUBLISH_BODY_BYTES:
            raise HTTPException(
                status_code=413,
                detail="package publish payload is too large",
            )
        body.extend(chunk)
    try:
        raw_payload = json.loads(body.decode("utf-8"))
        return PackagePublish(**raw_payload)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValidationError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid package publish payload",
        ) from exc


def _validate_publish_payload(files: dict[str, str]) -> None:
    if not files:
        raise PackageManifestError("package files are required")
    if len(files) > MAX_PACKAGE_FILES:
        raise PackageManifestError(
            f"package cannot contain more than {MAX_PACKAGE_FILES} files"
        )
    total_bytes = 0
    for raw_path, content in files.items():
        if not isinstance(content, str):
            raise PackageManifestError(f"package file must be text: {raw_path}")
        if len(raw_path) > MAX_PACKAGE_PATH_LENGTH:
            raise PackageManifestError(f"package file path is too long: {raw_path}")
        file_bytes = len(content.encode("utf-8"))
        if file_bytes > MAX_PACKAGE_FILE_BYTES:
            raise PackageManifestError(f"package file is too large: {raw_path}")
        total_bytes += file_bytes
        if total_bytes > MAX_PACKAGE_TOTAL_BYTES:
            raise PackageManifestError("package payload is too large")


def _write_payload_to_staging(staging_dir: Path, files: dict[str, str]) -> None:
    staging_dir.mkdir(parents=True, exist_ok=False)
    for raw_path, content in files.items():
        if not isinstance(content, str):
            raise PackageManifestError(f"package file must be text: {raw_path}")
        relative_path = _safe_relative_path(raw_path)
        destination = staging_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(destination, flags, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
        except Exception:
            os.close(fd)
            raise


def _validate_staged_package(staging_dir: Path) -> PackageManifest:
    manifest = load_package_manifest(staging_dir / "agh.package.toml")
    _assert_publish_version(manifest.version)
    _validate_allowed_package_files(staging_dir)
    _validate_skills(staging_dir)
    _validate_publishable_artifacts(staging_dir)
    return manifest


def _validate_allowed_package_files(staging_dir: Path) -> None:
    allowed_root_names = {"agh.package.toml", "instructions", "skills"}
    for entry in staging_dir.iterdir():
        if entry.name not in allowed_root_names:
            raise PackageManifestError(f"unexpected package file path: {entry.name}")
        if entry.name == "agh.package.toml" and not entry.is_file():
            raise PackageManifestError("agh.package.toml must be a file")
        if entry.name == "instructions":
            _validate_instruction_files(staging_dir, entry)
        if entry.name == "skills" and not entry.is_dir():
            raise PackageManifestError("skills must be a directory")


def _validate_instruction_files(staging_dir: Path, instructions_dir: Path) -> None:
    if not instructions_dir.is_dir():
        raise PackageManifestError("instructions must be a directory")
    allowed_names = {"AGENTS.md", "CLAUDE.md"}
    for entry in instructions_dir.iterdir():
        if entry.name not in allowed_names or not entry.is_file():
            relative = entry.relative_to(staging_dir).as_posix()
            raise PackageManifestError(f"unexpected package file path: {relative}")


def _validate_publishable_artifacts(staging_dir: Path) -> None:
    if (
        (staging_dir / "instructions" / "AGENTS.md").is_file()
        or (staging_dir / "instructions" / "CLAUDE.md").is_file()
        or _has_skill_artifact(staging_dir)
    ):
        return
    raise PackageManifestError(
        "package must include at least one instruction file or skill"
    )


def _has_skill_artifact(staging_dir: Path) -> bool:
    skills_dir = staging_dir / "skills"
    if not skills_dir.exists() or not skills_dir.is_dir():
        return False
    return any(
        (child / "SKILL.md").is_file()
        for child in skills_dir.iterdir()
        if child.is_dir()
    )


def _assert_publish_version(version: str) -> None:
    if version == "latest":
        raise PackageManifestError("latest is not allowed for publish")
    if not is_semver(version):
        raise PackageManifestError(f"invalid version: {version}")


def _validate_skills(staging_dir: Path) -> None:
    skills_dir = staging_dir / "skills"
    if not skills_dir.exists():
        return
    if not skills_dir.is_dir():
        raise PackageManifestError("skills must be a directory")
    for child in skills_dir.iterdir():
        if not child.is_dir():
            raise PackageManifestError(f"invalid skill entry: {child.name}")
        if not is_valid_slug(child.name):
            raise PackageManifestError(f"invalid skill name: {child.name}")
        for entry in child.iterdir():
            if entry.name != "SKILL.md" or not entry.is_file():
                relative = entry.relative_to(staging_dir).as_posix()
                raise PackageManifestError(f"unexpected package file path: {relative}")
        if not (child / "SKILL.md").is_file():
            raise PackageManifestError(f"skills/{child.name}/SKILL.md is required")


def _safe_relative_path(raw_path: str) -> Path:
    if not raw_path or "\\" in raw_path:
        raise PackageManifestError(f"invalid package file path: {raw_path}")
    posix = PurePosixPath(raw_path)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts):
        raise PackageManifestError(f"invalid package file path: {raw_path}")
    return Path(*posix.parts)


def _ensure_safe_packages_root(packages_root: Path) -> None:
    if packages_root.exists() and packages_root.is_symlink():
        raise PackageManifestError(
            f"refusing to write through symlinked packages directory: {packages_root}"
        )
    packages_root.mkdir(parents=True, exist_ok=True)


def _recover_or_prepare_storage_target(
    connection: sqlite3.Connection, packages_root: Path, storage_dir: Path
) -> None:
    """Validate the final storage path and remove unreferenced orphan contents."""
    _ensure_safe_packages_root(packages_root)
    root = packages_root.resolve()
    resolved_storage = storage_dir.resolve(strict=False)
    try:
        relative_parts = resolved_storage.relative_to(root).parts
    except ValueError as exc:
        raise PackageManifestError("invalid package storage path") from exc
    current = root
    for part in relative_parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise PackageManifestError(
                f"refusing to write through symlinked package path: {current}"
            )
    if not storage_dir.exists():
        return
    if not storage_dir.is_dir() or _storage_path_is_referenced(connection, storage_dir):
        raise PackageManifestError("package storage path already exists")
    shutil.rmtree(storage_dir)


def _storage_path_is_referenced(
    connection: sqlite3.Connection, storage_dir: Path
) -> bool:
    target = storage_dir.resolve(strict=False)
    target_text = str(storage_dir)
    rows = connection.execute("SELECT storage_path FROM package_versions").fetchall()
    for row in rows:
        stored_path = Path(row["storage_path"])
        if str(stored_path) == target_text:
            return True
        if stored_path.resolve(strict=False) == target:
            return True
    return False


def _store_staged_package(staging_dir: Path, storage_dir: Path) -> None:
    storage_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(staging_dir, storage_dir, symlinks=False)


def _package_checksum(package_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in package_dir.rglob("*") if item.is_file()):
        relative = path.relative_to(package_dir).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _require_package_artifact_read_target(storage_dir: Path, candidate: Path) -> None:
    try:
        resolved_root = storage_dir.resolve(strict=True)
        resolved_candidate = candidate.resolve(strict=True)
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        _raise_package_artifact_missing()
    except (FileNotFoundError, NotADirectoryError):
        _raise_package_artifact_missing()
    except OSError as exc:
        _raise_package_artifact_storage_unavailable(exc)
    try:
        candidate_stat = resolved_candidate.stat()
    except (FileNotFoundError, NotADirectoryError):
        _raise_package_artifact_missing()
    except OSError as exc:
        _raise_package_artifact_storage_unavailable(exc)
    if not stat_module.S_ISREG(candidate_stat.st_mode):
        _raise_package_artifact_missing()
    current = candidate
    paths: list[Path] = []
    while current != storage_dir:
        paths.append(current)
        current = current.parent
    paths.append(storage_dir)
    for path in paths:
        try:
            path_stat = path.lstat()
        except (FileNotFoundError, NotADirectoryError):
            _raise_package_artifact_missing()
        except OSError as exc:
            _raise_package_artifact_storage_unavailable(exc)
        if stat_module.S_ISLNK(path_stat.st_mode):
            _raise_package_artifact_missing()
