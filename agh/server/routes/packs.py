"""Pack publish, listing, and file download routes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ValidationError

from agh.common.ids import generate_prefixed_id
from agh.common.pack_manifest import PackManifest, PackManifestError, load_pack_manifest
from agh.common.validation import is_semver, is_valid_slug
from agh.server.auth import CurrentUser, get_current_user
from agh.server.db import connect_database, get_data_dir

router = APIRouter(prefix="/packs", tags=["packs"])

MAX_PACK_FILES = 128
MAX_PACK_PATH_LENGTH = 240
MAX_PACK_FILE_BYTES = 256 * 1024
MAX_PACK_TOTAL_BYTES = 1024 * 1024
MAX_PACK_PUBLISH_BODY_BYTES = MAX_PACK_TOTAL_BYTES + (MAX_PACK_FILES * 128)


class PackPublish(BaseModel):
    files: dict[str, str]


def _connect(request: Request) -> sqlite3.Connection:
    return connect_database(getattr(request.app.state, "db_path", None))


def _require_pack_publisher(current_user: CurrentUser) -> None:
    if current_user.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _pack_version_response(row: sqlite3.Row) -> dict[str, Any]:
    manifest = json.loads(row["manifest_json"])
    return {
        "id": f"{row['domain']}/{row['name']}@{row['version']}",
        "pack_id": row["pack_id"],
        "domain": row["domain"],
        "name": row["name"],
        "version": row["version"],
        "description": manifest["description"],
        "tags": manifest.get("tags", []),
        "checksum": row["checksum"],
        "created_at": row["created_at"],
    }


@router.get("")
def list_packs(
    request: Request, current_user: CurrentUser = Depends(get_current_user)
) -> dict[str, list[dict[str, Any]]]:
    connection = _connect(request)
    try:
        rows = connection.execute(
            """
            SELECT packs.id AS pack_id, packs.domain, packs.name,
                   pack_versions.id AS version_id, pack_versions.version,
                   pack_versions.manifest_json, pack_versions.checksum,
                   pack_versions.created_at
            FROM pack_versions
            JOIN packs ON packs.id = pack_versions.pack_id
            ORDER BY packs.domain ASC, packs.name ASC, pack_versions.version ASC
            """
        ).fetchall()
        return {"packs": [_pack_version_response(row) for row in rows]}
    finally:
        connection.close()


@router.post("", status_code=status.HTTP_201_CREATED)
async def publish_pack(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    _require_pack_publisher(current_user)
    payload = await _read_pack_publish_payload(request)
    data_dir = get_data_dir().resolve()
    packs_root = data_dir / "packs"
    staging_dir = packs_root / ".staging" / generate_prefixed_id("packv")
    try:
        _validate_publish_payload(payload.files)
        _ensure_safe_packs_root(packs_root)
        _write_payload_to_staging(staging_dir, payload.files)
        manifest = _validate_staged_pack(staging_dir)
        checksum = _pack_checksum(staging_dir)
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
            data_dir / "packs" / manifest.domain / manifest.name / manifest.version
        )
        connection = _connect(request)
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = _find_pack_version(
                    connection, manifest.domain, manifest.name, manifest.version
                )
                if existing is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="pack version already exists",
                    )
                pack_row = connection.execute(
                    "SELECT id FROM packs WHERE domain = ? AND name = ?",
                    (manifest.domain, manifest.name),
                ).fetchone()
                if pack_row is None:
                    pack_id = generate_prefixed_id("pack")
                    connection.execute(
                        "INSERT INTO packs (id, domain, name, created_by) VALUES (?, ?, ?, ?)",
                        (pack_id, manifest.domain, manifest.name, current_user.id),
                    )
                else:
                    pack_id = str(pack_row["id"])

                version_id = generate_prefixed_id("packv")
                _ensure_safe_storage_target(packs_root, storage_dir)
                _store_staged_pack(staging_dir, storage_dir)
                connection.execute(
                    """
                    INSERT INTO pack_versions
                        (id, pack_id, version, manifest_json, storage_path, checksum)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        pack_id,
                        manifest.version,
                        manifest_json,
                        str(storage_dir),
                        checksum,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                if storage_dir.exists():
                    shutil.rmtree(storage_dir, ignore_errors=True)
                if "UNIQUE" in str(exc):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="pack version already exists",
                    ) from exc
                raise
            except HTTPException:
                connection.rollback()
                raise
            except Exception:
                connection.rollback()
                if storage_dir.exists():
                    shutil.rmtree(storage_dir, ignore_errors=True)
                raise
            else:
                connection.commit()
            created = _get_pack_version(
                connection, manifest.domain, manifest.name, manifest.version
            )
            return _pack_version_response(created)
        finally:
            connection.close()
    except PackManifestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


@router.get("/{domain}/{name}/versions/{version}/files/{file_path:path}")
def get_pack_file(
    domain: str,
    name: str,
    version: str,
    file_path: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    _validate_pack_parts(domain, name, version)
    try:
        safe_path = _safe_relative_path(file_path)
    except PackManifestError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="pack file not found"
        ) from exc
    connection = _connect(request)
    try:
        row = _find_pack_version(connection, domain, name, version)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="pack file not found"
            )
        storage_dir = Path(row["storage_path"])
        candidate = storage_dir / safe_path
        if not _is_safe_pack_file(storage_dir, candidate):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="pack file not found"
            )
        return Response(
            candidate.read_text(encoding="utf-8"),
            media_type="text/plain; charset=utf-8",
        )
    finally:
        connection.close()


def _validate_pack_parts(domain: str, name: str, version: str) -> None:
    if not is_valid_slug(domain) or not is_valid_slug(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="pack not found"
        )
    try:
        _assert_publish_version(version)
    except PackManifestError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="pack not found"
        ) from exc


def _find_pack_version(
    connection: sqlite3.Connection, domain: str, name: str, version: str
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT packs.id AS pack_id, packs.domain, packs.name,
               pack_versions.id AS version_id, pack_versions.version,
               pack_versions.manifest_json, pack_versions.storage_path,
               pack_versions.checksum, pack_versions.created_at
        FROM pack_versions
        JOIN packs ON packs.id = pack_versions.pack_id
        WHERE packs.domain = ? AND packs.name = ? AND pack_versions.version = ?
        """,
        (domain, name, version),
    ).fetchone()


def _get_pack_version(
    connection: sqlite3.Connection, domain: str, name: str, version: str
) -> sqlite3.Row:
    row = _find_pack_version(connection, domain, name, version)
    if row is None:
        raise RuntimeError("published pack version missing after commit")
    return row


async def _read_pack_publish_payload(request: Request) -> PackPublish:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_PACK_PUBLISH_BODY_BYTES:
            raise HTTPException(
                status_code=413,
                detail="pack publish payload is too large",
            )
        body.extend(chunk)
    try:
        raw_payload = json.loads(body.decode("utf-8"))
        return PackPublish(**raw_payload)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValidationError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid pack publish payload",
        ) from exc


def _validate_publish_payload(files: dict[str, str]) -> None:
    if not files:
        raise PackManifestError("pack files are required")
    if len(files) > MAX_PACK_FILES:
        raise PackManifestError(f"pack cannot contain more than {MAX_PACK_FILES} files")
    total_bytes = 0
    for raw_path, content in files.items():
        if not isinstance(content, str):
            raise PackManifestError(f"pack file must be text: {raw_path}")
        if len(raw_path) > MAX_PACK_PATH_LENGTH:
            raise PackManifestError(f"pack file path is too long: {raw_path}")
        file_bytes = len(content.encode("utf-8"))
        if file_bytes > MAX_PACK_FILE_BYTES:
            raise PackManifestError(f"pack file is too large: {raw_path}")
        total_bytes += file_bytes
        if total_bytes > MAX_PACK_TOTAL_BYTES:
            raise PackManifestError("pack payload is too large")


def _write_payload_to_staging(staging_dir: Path, files: dict[str, str]) -> None:
    staging_dir.mkdir(parents=True, exist_ok=False)
    for raw_path, content in files.items():
        if not isinstance(content, str):
            raise PackManifestError(f"pack file must be text: {raw_path}")
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


def _validate_staged_pack(staging_dir: Path) -> PackManifest:
    manifest = load_pack_manifest(staging_dir / "agh.pack.toml")
    _assert_publish_version(manifest.version)
    _validate_allowed_pack_files(staging_dir)
    _validate_skills(staging_dir)
    _validate_publishable_artifacts(staging_dir)
    return manifest


def _validate_allowed_pack_files(staging_dir: Path) -> None:
    allowed_root_names = {"agh.pack.toml", "instructions", "skills"}
    for entry in staging_dir.iterdir():
        if entry.name not in allowed_root_names:
            raise PackManifestError(f"unexpected pack file path: {entry.name}")
        if entry.name == "agh.pack.toml" and not entry.is_file():
            raise PackManifestError("agh.pack.toml must be a file")
        if entry.name == "instructions":
            _validate_instruction_files(staging_dir, entry)
        if entry.name == "skills" and not entry.is_dir():
            raise PackManifestError("skills must be a directory")


def _validate_instruction_files(staging_dir: Path, instructions_dir: Path) -> None:
    if not instructions_dir.is_dir():
        raise PackManifestError("instructions must be a directory")
    allowed_names = {"AGENTS.md", "CLAUDE.md"}
    for entry in instructions_dir.iterdir():
        if entry.name not in allowed_names or not entry.is_file():
            relative = entry.relative_to(staging_dir).as_posix()
            raise PackManifestError(f"unexpected pack file path: {relative}")


def _validate_publishable_artifacts(staging_dir: Path) -> None:
    if (
        (staging_dir / "instructions" / "AGENTS.md").is_file()
        or (staging_dir / "instructions" / "CLAUDE.md").is_file()
        or _has_skill_artifact(staging_dir)
    ):
        return
    raise PackManifestError("pack must include at least one instruction file or skill")


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
        raise PackManifestError("latest is not allowed for publish")
    if not is_semver(version):
        raise PackManifestError(f"invalid version: {version}")


def _validate_skills(staging_dir: Path) -> None:
    skills_dir = staging_dir / "skills"
    if not skills_dir.exists():
        return
    if not skills_dir.is_dir():
        raise PackManifestError("skills must be a directory")
    for child in skills_dir.iterdir():
        if not child.is_dir():
            raise PackManifestError(f"invalid skill entry: {child.name}")
        if not is_valid_slug(child.name):
            raise PackManifestError(f"invalid skill name: {child.name}")
        for entry in child.iterdir():
            if entry.name != "SKILL.md" or not entry.is_file():
                relative = entry.relative_to(staging_dir).as_posix()
                raise PackManifestError(f"unexpected pack file path: {relative}")
        if not (child / "SKILL.md").is_file():
            raise PackManifestError(f"skills/{child.name}/SKILL.md is required")


def _safe_relative_path(raw_path: str) -> Path:
    if not raw_path or "\\" in raw_path:
        raise PackManifestError(f"invalid pack file path: {raw_path}")
    posix = PurePosixPath(raw_path)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts):
        raise PackManifestError(f"invalid pack file path: {raw_path}")
    return Path(*posix.parts)


def _ensure_safe_packs_root(packs_root: Path) -> None:
    if packs_root.exists() and packs_root.is_symlink():
        raise PackManifestError(
            f"refusing to write through symlinked packs directory: {packs_root}"
        )
    packs_root.mkdir(parents=True, exist_ok=True)


def _ensure_safe_storage_target(packs_root: Path, storage_dir: Path) -> None:
    _ensure_safe_packs_root(packs_root)
    root = packs_root.resolve()
    resolved_storage = storage_dir.resolve(strict=False)
    try:
        relative_parts = resolved_storage.relative_to(root).parts
    except ValueError as exc:
        raise PackManifestError("invalid pack storage path") from exc
    current = root
    for part in relative_parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise PackManifestError(
                f"refusing to write through symlinked pack path: {current}"
            )
    if storage_dir.exists():
        raise PackManifestError("pack storage path already exists")


def _store_staged_pack(staging_dir: Path, storage_dir: Path) -> None:
    storage_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(staging_dir, storage_dir, symlinks=False)


def _pack_checksum(pack_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in pack_dir.rglob("*") if item.is_file()):
        relative = path.relative_to(pack_dir).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _is_safe_pack_file(storage_dir: Path, candidate: Path) -> bool:
    try:
        resolved_root = storage_dir.resolve(strict=True)
        resolved_candidate = candidate.resolve(strict=True)
        resolved_candidate.relative_to(resolved_root)
    except (OSError, ValueError):
        return False
    if not resolved_candidate.is_file():
        return False
    current = candidate
    paths: list[Path] = []
    while current != storage_dir:
        paths.append(current)
        current = current.parent
    paths.append(storage_dir)
    return not any(path.is_symlink() for path in paths)
