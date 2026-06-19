"""Collection CRUD routes."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from agh.common.checksums import managed_payload_checksum
from agh.common.ids import generate_prefixed_id, is_valid_prefixed_id
from agh.common.validation import PackageRef, parse_package_ref
from agh.server.auth import CurrentUser, get_current_user
from agh.server.db import connect_database

LOGGER = logging.getLogger(__name__)
router = APIRouter(tags=["collections"])
MAX_COLLECTION_NAME_LENGTH = 80
MAX_COLLECTION_DESCRIPTION_LENGTH = 1000


class CollectionCreate(BaseModel):
    name: str
    description: str = ""


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    active: bool | None = None


def _connect(request: Request) -> sqlite3.Connection:
    return connect_database(getattr(request.app.state, "db_path", None))


def _require_admin(user: CurrentUser) -> None:
    if not _is_collection_manager(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _is_collection_manager(user: CurrentUser) -> bool:
    return user.role in {"owner", "admin"}


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="collection name is required",
        )
    if len(cleaned) > MAX_COLLECTION_NAME_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"collection name must be at most {MAX_COLLECTION_NAME_LENGTH} characters",
        )
    return cleaned


def _clean_description(description: str) -> str:
    if len(description) > MAX_COLLECTION_DESCRIPTION_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "collection description must be at most "
                f"{MAX_COLLECTION_DESCRIPTION_LENGTH} characters"
            ),
        )
    return description


def _row_to_response(row: sqlite3.Row) -> dict[str, str | bool]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "active": bool(row["active"]),
    }


class CollectionPackageAssign(BaseModel):
    package_ref: str
    position: int = 0


class CollectionPackageUpdate(BaseModel):
    package_ref: str | None = None
    position: int | None = None
    active: bool | None = None


def _parse_package_ref_or_400(value: str) -> PackageRef:
    try:
        return parse_package_ref(value, allow_latest=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


def _package_row_or_404(
    connection: sqlite3.Connection, package_ref: PackageRef
) -> sqlite3.Row:
    row = connection.execute(
        "SELECT id, domain, name FROM packages WHERE domain = ? AND name = ?",
        (package_ref.domain, package_ref.name),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="package not found"
        )
    return row


def _semver_key(version: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in version.split("."))  # type: ignore[return-value]


def _package_version_row_or_404(
    connection: sqlite3.Connection,
    package_id: str,
    version_ref: str,
    *,
    columns: str,
) -> sqlite3.Row:
    if version_ref == "latest":
        rows = connection.execute(
            f"SELECT {columns} FROM package_versions WHERE package_id = ?",
            (package_id,),
        ).fetchall()
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="package version not found",
            )
        return max(rows, key=lambda row: _semver_key(str(row["version"])))
    row = connection.execute(
        f"SELECT {columns} FROM package_versions WHERE package_id = ? AND version = ?",
        (package_id, version_ref),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="package version not found",
        )
    return row


def _resolve_package_version_row(
    connection: sqlite3.Connection, package_id: str, version_ref: str
) -> sqlite3.Row:
    return _package_version_row_or_404(
        connection,
        package_id,
        version_ref,
        columns="id, version, manifest_json, storage_path, checksum",
    )


def _skill_names(storage_dir: Path) -> list[str]:
    skills_dir = storage_dir / "skills"
    if not skills_dir.is_dir() or skills_dir.is_symlink():
        return []
    return sorted(
        child.name
        for child in skills_dir.iterdir()
        if child.is_dir() and (child / "SKILL.md").is_file()
    )


def _validate_skill_only_package(
    connection: sqlite3.Connection,
    package_id: str,
    version_ref: str,
    version_row: sqlite3.Row | None = None,
) -> sqlite3.Row:
    row = version_row or _resolve_package_version_row(
        connection, package_id, version_ref
    )
    storage_dir = Path(str(row["storage_path"]))
    if (storage_dir / "instructions" / "AGENTS.md").is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="package contains instructions and cannot be used as a collection skill",
        )
    if (storage_dir / "instructions" / "CLAUDE.md").is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="package contains instructions and cannot be used as a collection skill",
        )
    if not _skill_names(storage_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="package does not contain any skills",
        )
    return row


def _collection_package_response(
    connection: sqlite3.Connection, row: sqlite3.Row
) -> dict[str, str | int | bool]:
    resolved_version = str(
        _resolve_package_version_row(
            connection, str(row["package_id"]), str(row["version_ref"])
        )["version"]
    )
    return {
        "id": row["id"],
        "collection_id": row["collection_id"],
        "package_id": row["package_id"],
        "package_ref": f"{row['domain']}/{row['name']}@{row['version_ref']}",
        "resolved_ref": f"{row['domain']}/{row['name']}@{resolved_version}",
        "domain": row["domain"],
        "name": row["name"],
        "version_ref": row["version_ref"],
        "resolved_version": resolved_version,
        "position": int(row["position"]),
        "active": bool(row["active"]),
    }


def _assignment_row(
    connection: sqlite3.Connection, collection_id: str, assignment_id: str
) -> sqlite3.Row:
    if not is_valid_prefixed_id(assignment_id, "casn"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="collection package not found",
        )
    row = connection.execute(
        """
        SELECT collection_packages.id, collection_packages.collection_id,
               collection_packages.package_id, collection_packages.version_ref,
               collection_packages.position, collection_packages.active,
               packages.domain, packages.name
        FROM collection_packages
        JOIN packages ON packages.id = collection_packages.package_id
        WHERE collection_packages.collection_id = ? AND collection_packages.id = ?
        """,
        (collection_id, assignment_id),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="collection package not found",
        )
    return row


def _download_url(domain: str, name: str, version: str, path: str) -> str:
    quoted_path = quote(path, safe="/")
    return f"/api/v1/packages/{domain}/{name}/versions/{version}/files/{quoted_path}"


def _skill_artifact_checksum(storage_dir: Path, skill_name: str) -> str:
    artifact = storage_dir / "skills" / skill_name / "SKILL.md"
    return managed_payload_checksum(artifact.read_text(encoding="utf-8"))


def _active_collection_package_rows(
    connection: sqlite3.Connection, collection_id: str | None
) -> list[sqlite3.Row]:
    params: tuple[str, ...] = ()
    collection_filter = ""
    if collection_id is not None:
        collection_filter = "AND collections.id = ?"
        params = (collection_id,)
    return connection.execute(
        f"""
        SELECT collection_packages.id, collection_packages.collection_id,
               collection_packages.package_id, collection_packages.version_ref,
               collection_packages.position, collection_packages.active,
               collections.name AS collection_name, packages.domain, packages.name
        FROM collection_packages
        JOIN collections ON collections.id = collection_packages.collection_id
        JOIN packages ON packages.id = collection_packages.package_id
        WHERE collections.active = 1 AND collection_packages.active = 1
        {collection_filter}
        ORDER BY collections.name ASC, collection_packages.position ASC,
                 packages.domain ASC, packages.name ASC
        """,
        params,
    ).fetchall()


def _collection(conn: sqlite3.Connection, collection_id: str) -> sqlite3.Row:
    if not is_valid_prefixed_id(collection_id, "col"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="collection not found"
        )
    row = conn.execute(
        "SELECT id, name, description, active FROM collections WHERE id = ?",
        (collection_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="collection not found"
        )
    return row


def _get_active_collection(conn: sqlite3.Connection, collection_id: str) -> sqlite3.Row:
    row = _collection(conn, collection_id)
    if row["active"] != 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="collection not found"
        )
    return row


def _visible_collection(
    conn: sqlite3.Connection, collection_id: str, user: CurrentUser
) -> sqlite3.Row:
    row = _collection(conn, collection_id)
    if not _is_collection_manager(user) and row["active"] != 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="collection not found"
        )
    return row


@router.get("/collections")
def list_collections(
    request: Request, current_user: CurrentUser = Depends(get_current_user)
) -> dict[str, list[dict[str, str | bool]]]:
    conn = _connect(request)
    try:
        where = "" if _is_collection_manager(current_user) else "WHERE active = 1"
        rows = conn.execute(
            f"SELECT id, name, description, active FROM collections {where} ORDER BY name ASC"
        ).fetchall()
        return {"collections": [_row_to_response(row) for row in rows]}
    finally:
        conn.close()


@router.get("/collections/by-name/{name:path}")
def get_collection_by_name(
    name: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    conn = _connect(request)
    try:
        row = conn.execute(
            "SELECT id, name FROM collections WHERE name = ? AND active = 1",
            (name,),
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="collection not found"
            )
        return {"id": row["id"], "name": row["name"]}
    finally:
        conn.close()


@router.post("/collections", status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    _require_admin(current_user)
    collection_id = generate_prefixed_id("col")
    conn = _connect(request)
    try:
        try:
            conn.execute(
                """
                INSERT INTO collections (id, name, description, active, created_by)
                VALUES (?, ?, ?, 1, ?)
                """,
                (
                    collection_id,
                    _clean_name(payload.name),
                    _clean_description(payload.description),
                    current_user.id,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="collection name already exists",
            ) from exc
        return _row_to_response(_collection(conn, collection_id))
    finally:
        conn.close()


@router.get("/collections/{collection_id}")
def get_collection(
    collection_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    conn = _connect(request)
    try:
        return _row_to_response(_visible_collection(conn, collection_id, current_user))
    finally:
        conn.close()


@router.patch("/collections/{collection_id}")
def update_collection(
    collection_id: str,
    payload: CollectionUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    _require_admin(current_user)
    fields: dict[str, Any] = {}
    if payload.name is not None:
        fields["name"] = _clean_name(payload.name)
    if payload.description is not None:
        fields["description"] = _clean_description(payload.description)
    if payload.active is not None:
        fields["active"] = 1 if payload.active else 0

    conn = _connect(request)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _collection(conn, collection_id)
            if fields:
                assignments = ", ".join(f"{field} = ?" for field in fields)
                values = [*fields.values(), collection_id]
                conn.execute(
                    f"UPDATE collections SET {assignments}, updated_at = datetime('now') WHERE id = ?",
                    values,
                )
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="collection name already exists",
            ) from exc
        except Exception:
            conn.rollback()
            raise
        conn.commit()
        return _row_to_response(_collection(conn, collection_id))
    finally:
        conn.close()


@router.delete("/collections/{collection_id}")
def deactivate_collection(
    collection_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    return update_collection(
        collection_id, CollectionUpdate(active=False), request, current_user
    )


@router.get("/collections/{collection_id}/packages")
def list_collection_packages(
    collection_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, list[dict[str, str | int | bool]]]:
    conn = _connect(request)
    try:
        _visible_collection(conn, collection_id, current_user)
        active_filter = (
            ""
            if _is_collection_manager(current_user)
            else "AND collection_packages.active = 1"
        )
        rows = conn.execute(
            f"""
            SELECT collection_packages.id, collection_packages.collection_id,
                   collection_packages.package_id, collection_packages.version_ref,
                   collection_packages.position, collection_packages.active,
                   packages.domain, packages.name
            FROM collection_packages
            JOIN packages ON packages.id = collection_packages.package_id
            WHERE collection_packages.collection_id = ? {active_filter}
            ORDER BY collection_packages.position ASC, packages.domain ASC, packages.name ASC
            """,
            (collection_id,),
        ).fetchall()
        return {
            "collection_packages": [
                _collection_package_response(conn, row) for row in rows
            ]
        }
    finally:
        conn.close()


@router.post(
    "/collections/{collection_id}/packages", status_code=status.HTTP_201_CREATED
)
def assign_collection_package(
    collection_id: str,
    payload: CollectionPackageAssign,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | int | bool]:
    _require_admin(current_user)
    package_ref = _parse_package_ref_or_400(payload.package_ref)
    conn = _connect(request)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _get_active_collection(conn, collection_id)
            package_row = _package_row_or_404(conn, package_ref)
            _validate_skill_only_package(
                conn, str(package_row["id"]), package_ref.version
            )
            existing = conn.execute(
                """
                SELECT id, active FROM collection_packages
                WHERE collection_id = ? AND package_id = ?
                """,
                (collection_id, package_row["id"]),
            ).fetchone()
            if existing is not None and existing["active"] == 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="collection package assignment already exists",
                )
            if existing is None:
                assignment_id = generate_prefixed_id("casn")
                conn.execute(
                    """
                    INSERT INTO collection_packages
                        (id, collection_id, package_id, version_ref, position, active)
                    VALUES (?, ?, ?, ?, ?, 1)
                    """,
                    (
                        assignment_id,
                        collection_id,
                        package_row["id"],
                        package_ref.version,
                        payload.position,
                    ),
                )
            else:
                assignment_id = str(existing["id"])
                conn.execute(
                    """
                    UPDATE collection_packages
                    SET version_ref = ?, position = ?, active = 1,
                        updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (package_ref.version, payload.position, assignment_id),
                )
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="collection package assignment already exists",
            ) from exc
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        row = _assignment_row(conn, collection_id, assignment_id)
        return _collection_package_response(conn, row)
    finally:
        conn.close()


@router.patch("/collections/{collection_id}/packages/{assignment_id}")
def update_collection_package(
    collection_id: str,
    assignment_id: str,
    payload: CollectionPackageUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | int | bool]:
    _require_admin(current_user)
    conn = _connect(request)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _get_active_collection(conn, collection_id)
            current = _assignment_row(conn, collection_id, assignment_id)
            fields: dict[str, Any] = {}
            if payload.package_ref is not None:
                package_ref = _parse_package_ref_or_400(payload.package_ref)
                package_row = _package_row_or_404(conn, package_ref)
                effective_package_id = str(package_row["id"])
                effective_version_ref = package_ref.version
                fields["package_id"] = effective_package_id
                fields["version_ref"] = effective_version_ref
            else:
                effective_package_id = str(current["package_id"])
                effective_version_ref = str(current["version_ref"])
            will_be_active = (
                payload.active
                if payload.active is not None
                else bool(current["active"])
            )
            if will_be_active:
                _validate_skill_only_package(
                    conn, effective_package_id, effective_version_ref
                )
            if payload.position is not None:
                fields["position"] = payload.position
            if payload.active is not None:
                fields["active"] = 1 if payload.active else 0
            if fields:
                assignments = ", ".join(f"{field} = ?" for field in fields)
                values = list(fields.values()) + [current["id"]]
                sql = (
                    f"UPDATE collection_packages SET {assignments}, "
                    "updated_at = datetime('now') WHERE id = ?"
                )
                conn.execute(sql, values)
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="collection package assignment already exists",
            ) from exc
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        row = _assignment_row(conn, collection_id, assignment_id)
        return _collection_package_response(conn, row)
    finally:
        conn.close()


@router.delete("/collections/{collection_id}/packages/{assignment_id}")
def deactivate_collection_package(
    collection_id: str,
    assignment_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | int | bool]:
    _require_admin(current_user)
    conn = _connect(request)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _get_active_collection(conn, collection_id)
            _assignment_row(conn, collection_id, assignment_id)
            conn.execute(
                """
                UPDATE collection_packages
                SET active = 0, updated_at = datetime('now')
                WHERE id = ?
                """,
                (assignment_id,),
            )
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        row = _assignment_row(conn, collection_id, assignment_id)
        return _collection_package_response(conn, row)
    finally:
        conn.close()


@router.get("/skills")
def list_skills(
    request: Request,
    collection_id: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, list[dict[str, str]]]:
    conn = _connect(request)
    try:
        rows = _active_collection_package_rows(conn, collection_id)
        skills: list[dict[str, str]] = []
        for row in rows:
            version_row: sqlite3.Row | None = None
            try:
                version_row = _resolve_package_version_row(
                    conn, str(row["package_id"]), str(row["version_ref"])
                )
                _validate_skill_only_package(
                    conn,
                    str(row["package_id"]),
                    str(version_row["version"]),
                    version_row,
                )
                storage_dir = Path(str(version_row["storage_path"]))
                manifest = json.loads(str(version_row["manifest_json"]))
                description = str(manifest.get("description", ""))
                resolved_ref = f"{row['domain']}/{row['name']}@{version_row['version']}"
                for skill_name in _skill_names(storage_dir):
                    artifact_checksum = _skill_artifact_checksum(
                        storage_dir, skill_name
                    )
                    skills.append(
                        {
                            "collection_id": row["collection_id"],
                            "collection_name": row["collection_name"],
                            "skill_name": skill_name,
                            "package_ref": f"{row['domain']}/{row['name']}@{row['version_ref']}",
                            "resolved_ref": resolved_ref,
                            "checksum": artifact_checksum,
                            "artifact_checksum": artifact_checksum,
                            "package_checksum": str(version_row["checksum"]),
                            "description": description,
                        }
                    )
            except HTTPException as exc:
                LOGGER.warning(
                    "Suppressed active collection assignment: collection_id=%s "
                    "assignment_id=%s package_id=%s version_ref=%s status=%s detail=%s",
                    row["collection_id"],
                    row["id"],
                    row["package_id"],
                    row["version_ref"],
                    exc.status_code,
                    exc.detail,
                )
                continue
            except OSError as exc:
                LOGGER.warning(
                    "Suppressed active collection assignment: collection_id=%s "
                    "assignment_id=%s package_id=%s version_ref=%s storage_path=%s error=%s",
                    row["collection_id"],
                    row["id"],
                    row["package_id"],
                    row["version_ref"],
                    str(version_row["storage_path"])
                    if version_row is not None
                    else "unknown",
                    exc,
                )
                continue
            except (ValueError, KeyError) as exc:
                LOGGER.warning(
                    "Suppressed active collection assignment: collection_id=%s "
                    "assignment_id=%s package_id=%s version_ref=%s error=%s",
                    row["collection_id"],
                    row["id"],
                    row["package_id"],
                    row["version_ref"],
                    exc,
                )
                continue
        return {"skills": skills}
    finally:
        conn.close()


@router.get("/skills:resolve")
def resolve_skill(
    package_ref: str,
    skill_name: str,
    request: Request,
    collection_id: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    requested_ref = _parse_package_ref_or_400(package_ref)
    conn = _connect(request)
    try:
        rows = _active_collection_package_rows(conn, collection_id)
        matched: sqlite3.Row | None = None
        matched_version_row: sqlite3.Row | None = None
        for row in rows:
            if (
                row["domain"] == requested_ref.domain
                and row["name"] == requested_ref.name
            ):
                resolved_version_row = _resolve_package_version_row(
                    conn, str(row["package_id"]), str(row["version_ref"])
                )
                if requested_ref.version in {
                    row["version_ref"],
                    str(resolved_version_row["version"]),
                }:
                    matched = row
                    matched_version_row = resolved_version_row
                    break
        if matched is None or matched_version_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="skill not found"
            )
        version_row = _validate_skill_only_package(
            conn,
            str(matched["package_id"]),
            str(matched["version_ref"]),
            matched_version_row,
        )
        if skill_name not in _skill_names(Path(str(version_row["storage_path"]))):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="skill not found"
            )
        artifact_path = f"skills/{skill_name}/SKILL.md"
        artifact_checksum = _skill_artifact_checksum(
            Path(str(version_row["storage_path"])), skill_name
        )
        return {
            "package_version_id": str(version_row["id"]),
            "package_ref": f"{matched['domain']}/{matched['name']}@{version_row['version']}",
            "checksum": artifact_checksum,
            "artifact_checksum": artifact_checksum,
            "package_checksum": str(version_row["checksum"]),
            "artifact_path": artifact_path,
            "download_url": _download_url(
                str(matched["domain"]),
                str(matched["name"]),
                str(version_row["version"]),
                artifact_path,
            ),
        }
    except OSError as exc:
        LOGGER.warning(
            "Suppressed skill resolve storage error: package_ref=%s skill_name=%s "
            "collection_id=%s error=%s",
            package_ref,
            skill_name,
            collection_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="skill not found"
        ) from exc
    finally:
        conn.close()
