"""Project CRUD, developer membership, and project access routes."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import quote

from fastapi import (  # pyright: ignore[reportMissingImports]
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from pydantic import BaseModel  # pyright: ignore[reportMissingImports]

from agh.common.checksums import managed_payload_checksum
from agh.common.ids import generate_prefixed_id, is_valid_prefixed_id
from agh.common.repo_url import normalize_repo_url
from agh.common.validation import PackageRef, parse_package_ref, validate_project_name
from agh.server.auth import CurrentUser, get_current_user
from agh.server.db import connect_database

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    repo_url: str


class ProjectUpdate(BaseModel):
    name: str | None = None
    repo_url: str | None = None
    active: bool | None = None


class ProjectPackageAssign(BaseModel):
    package_ref: str
    position: int = 0


class ProjectPackageUpdate(BaseModel):
    package_ref: str | None = None
    position: int | None = None
    active: bool | None = None


def _connect(request: Request) -> sqlite3.Connection:
    return connect_database(getattr(request.app.state, "db_path", None))


def _require_project_admin(current_user: CurrentUser) -> None:
    if current_user.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _project_response(row: sqlite3.Row) -> dict[str, str | bool]:
    return {
        "id": row["id"],
        "name": row["name"],
        "repo_url": row["repo_url"],
        "repo_url_normalized": row["repo_url_normalized"],
        "active": bool(row["active"]),
    }


def _clean_name(name: str) -> str:
    try:
        return validate_project_name(name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


def _normalize_repo_or_400(repo_url: str) -> str:
    try:
        return normalize_repo_url(repo_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


def _validate_project_id(project_id: str) -> None:
    if not is_valid_prefixed_id(project_id, "prj"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="project not found"
        )


def _get_project(connection: sqlite3.Connection, project_id: str) -> sqlite3.Row:
    _validate_project_id(project_id)
    row = connection.execute(
        """
        SELECT id, name, repo_url, repo_url_normalized, active
        FROM projects
        WHERE id = ?
        """,
        (project_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="project not found"
        )
    return row


def _get_active_project(connection: sqlite3.Connection, project_id: str) -> sqlite3.Row:
    row = _get_project(connection, project_id)
    if row["active"] != 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="project not found"
        )
    return row


def _ensure_member_can_read_project(
    connection: sqlite3.Connection, project_id: str, user_id: str
) -> sqlite3.Row:
    _validate_project_id(project_id)
    row = connection.execute(
        """
        SELECT projects.id, projects.name, projects.repo_url,
               projects.repo_url_normalized, projects.active
        FROM projects
        JOIN project_members ON project_members.project_id = projects.id
        WHERE projects.id = ? AND project_members.user_id = ? AND projects.active = 1
        """,
        (project_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="project not found"
        )
    return row


def _raise_project_integrity_error(exc: sqlite3.IntegrityError) -> None:
    message = str(exc)
    if "projects.name" in message or "ux_projects_name" in message:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="project name already exists",
        ) from exc
    if (
        "projects.repo_url_normalized" in message
        or "ux_projects_active_repo_url_normalized" in message
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="active project repo URL already exists",
        ) from exc
    raise exc


def _get_active_user(connection: sqlite3.Connection, user_id: str) -> sqlite3.Row:
    if not is_valid_prefixed_id(user_id, "usr"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    row = connection.execute(
        "SELECT id, active FROM users WHERE id = ? AND active = 1", (user_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    return row


def _validate_assignment_id(assignment_id: str) -> None:
    if not is_valid_prefixed_id(assignment_id, "asn"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="project package not found"
        )


def _parse_package_ref_or_400(package_ref: str) -> PackageRef:
    try:
        return parse_package_ref(package_ref, allow_latest=True)
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


def _raise_package_version_not_found() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="package version not found",
    )


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
            _raise_package_version_not_found()
        return max(rows, key=lambda row: _semver_key(str(row["version"])))
    row = connection.execute(
        f"""
        SELECT {columns}
        FROM package_versions
        WHERE package_id = ? AND version = ?
        """,
        (package_id, version_ref),
    ).fetchone()
    if row is None:
        _raise_package_version_not_found()
    return row


def _resolve_package_version(
    connection: sqlite3.Connection, package_id: str, version_ref: str
) -> str:
    row = _package_version_row_or_404(
        connection, package_id, version_ref, columns="version"
    )
    return str(row["version"])


def _resolved_package_version_row(
    connection: sqlite3.Connection, package_id: str, version_ref: str
) -> sqlite3.Row:
    return _package_version_row_or_404(
        connection,
        package_id,
        version_ref,
        columns="id, version, manifest_json, storage_path, checksum",
    )


def _project_package_response(
    connection: sqlite3.Connection, row: sqlite3.Row
) -> dict[str, str | int | bool]:
    resolved_version = _resolve_package_version(
        connection, str(row["package_id"]), str(row["version_ref"])
    )
    return {
        "id": row["id"],
        "project_id": row["project_id"],
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
    connection: sqlite3.Connection, project_id: str, assignment_id: str
) -> sqlite3.Row:
    _validate_assignment_id(assignment_id)
    row = connection.execute(
        """
        SELECT project_packages.id, project_packages.project_id, project_packages.package_id,
               project_packages.version_ref, project_packages.position, project_packages.active,
               packages.domain, packages.name
        FROM project_packages
        JOIN packages ON packages.id = project_packages.package_id
        WHERE project_packages.project_id = ? AND project_packages.id = ?
        """,
        (project_id, assignment_id),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="project package not found"
        )
    return row


def _active_project_package_rows(
    connection: sqlite3.Connection, project_id: str
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT project_packages.id, project_packages.project_id, project_packages.package_id,
               project_packages.version_ref, project_packages.position,
               packages.domain, packages.name
        FROM project_packages
        JOIN packages ON packages.id = project_packages.package_id
        WHERE project_packages.project_id = ? AND project_packages.active = 1
        ORDER BY project_packages.position ASC, packages.domain ASC, packages.name ASC
        """,
        (project_id,),
    ).fetchall()


def _package_file_download_url(domain: str, name: str, version: str, path: str) -> str:
    quoted_path = quote(path, safe="/")
    return f"/api/v1/packages/{domain}/{name}/versions/{version}/files/{quoted_path}"


def _raise_package_artifact_missing() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="package file not found",
    )


def _raise_package_artifact_storage_unavailable(
    exc: OSError | UnicodeDecodeError,
) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="package artifact storage unavailable",
    ) from exc


def _missing_package_artifact_or_none(required: bool) -> None:
    if required:
        _raise_package_artifact_missing()
    return None


def _read_package_file(
    storage_dir: Path, relative_path: str, *, required: bool
) -> str | None:
    candidate = storage_dir / relative_path
    try:
        resolved_root = storage_dir.resolve(strict=True)
        resolved_candidate = candidate.resolve(strict=True)
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return _missing_package_artifact_or_none(required)
    except (FileNotFoundError, NotADirectoryError):
        return _missing_package_artifact_or_none(required)
    except OSError as exc:
        _raise_package_artifact_storage_unavailable(exc)
    if not resolved_candidate.is_file():
        return _missing_package_artifact_or_none(required)
    if _package_artifact_path_has_symlink_component(storage_dir, candidate):
        return _missing_package_artifact_or_none(required)
    try:
        return resolved_candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _raise_package_artifact_storage_unavailable(exc)


def _package_artifact_path_has_symlink_component(
    storage_dir: Path, candidate: Path
) -> bool:
    current = candidate
    while True:
        try:
            is_symlink = current.is_symlink()
        except OSError as exc:
            _raise_package_artifact_storage_unavailable(exc)
        if is_symlink:
            return True
        if current == storage_dir:
            return False
        current = current.parent


def _instruction_artifact(
    *,
    domain: str,
    name: str,
    version: str,
    storage_dir: Path,
    path: str,
    required: bool,
) -> dict[str, str] | None:
    content = _read_package_file(storage_dir, path, required=required)
    if content is None:
        return None
    target_agent = "opencode" if path.endswith("AGENTS.md") else "claude"
    target_path = "AGENTS.md" if target_agent == "opencode" else "CLAUDE.md"
    return {
        "kind": "instruction",
        "path": path,
        "target_agent": target_agent,
        "target_path": target_path,
        "checksum": managed_payload_checksum(content),
        "download_url": _package_file_download_url(domain, name, version, path),
    }


def _skill_artifacts(
    *,
    domain: str,
    name: str,
    version: str,
    storage_dir: Path,
    expected_paths: list[str] | None = None,
) -> list[dict[str, str]]:
    if expected_paths is not None:
        artifacts: list[dict[str, str]] = []
        for path in sorted(expected_paths):
            artifacts.extend(
                _skill_artifacts_for_path(
                    domain=domain,
                    name=name,
                    version=version,
                    storage_dir=storage_dir,
                    path=path,
                    required=True,
                )
            )
        return artifacts

    skills_dir = storage_dir / "skills"
    if not skills_dir.is_dir() or skills_dir.is_symlink():
        return []
    artifacts: list[dict[str, str]] = []
    for skill_dir in sorted(item for item in skills_dir.iterdir() if item.is_dir()):
        path = f"skills/{skill_dir.name}/SKILL.md"
        artifacts.extend(
            _skill_artifacts_for_path(
                domain=domain,
                name=name,
                version=version,
                storage_dir=storage_dir,
                path=path,
                required=False,
            )
        )
    return artifacts


def _skill_artifacts_for_path(
    *,
    domain: str,
    name: str,
    version: str,
    storage_dir: Path,
    path: str,
    required: bool,
) -> list[dict[str, str]]:
    skill_name = _skill_name_from_artifact_path(path)
    if skill_name is None:
        return []
    content = _read_package_file(storage_dir, path, required=required)
    if content is None:
        return []
    checksum = managed_payload_checksum(content)
    download_url = _package_file_download_url(domain, name, version, path)
    return [
        {
            "kind": "skill",
            "path": path,
            "target_agent": "opencode",
            "target_path": f".opencode/skills/{skill_name}/SKILL.md",
            "checksum": checksum,
            "download_url": download_url,
        },
        {
            "kind": "skill",
            "path": path,
            "target_agent": "claude",
            "target_path": f".claude/skills/{skill_name}/SKILL.md",
            "checksum": checksum,
            "download_url": download_url,
        },
    ]


def _skill_name_from_artifact_path(path: str) -> str | None:
    parts = path.split("/")
    if len(parts) == 3 and parts[0] == "skills" and parts[1] and parts[2] == "SKILL.md":
        return parts[1]
    return None


def _expected_artifact_paths(manifest: dict[str, Any]) -> set[str] | None:
    raw_paths = manifest.get("artifact_paths")
    if raw_paths is None:
        return None
    if not isinstance(raw_paths, list):
        return None
    if not raw_paths or not all(
        isinstance(path, str)
        and (
            path in {"instructions/AGENTS.md", "instructions/CLAUDE.md"}
            or _skill_name_from_artifact_path(path) is not None
        )
        for path in raw_paths
    ):
        return None
    return set(raw_paths)


def _pull_manifest_package(
    connection: sqlite3.Connection, row: sqlite3.Row
) -> dict[str, Any]:
    version_row = _resolved_package_version_row(
        connection, str(row["package_id"]), str(row["version_ref"])
    )
    version = str(version_row["version"])
    domain = str(row["domain"])
    name = str(row["name"])
    storage_dir = Path(str(version_row["storage_path"]))
    manifest = json.loads(str(version_row["manifest_json"]))
    expected_paths = _expected_artifact_paths(manifest)
    artifacts: list[dict[str, str]] = []
    for instruction_path in ["instructions/AGENTS.md", "instructions/CLAUDE.md"]:
        artifact = _instruction_artifact(
            domain=domain,
            name=name,
            version=version,
            storage_dir=storage_dir,
            path=instruction_path,
            required=expected_paths is not None and instruction_path in expected_paths,
        )
        if artifact is not None:
            artifacts.append(artifact)
    expected_skill_paths = None
    if expected_paths is not None:
        expected_skill_paths = [
            path for path in expected_paths if _skill_name_from_artifact_path(path)
        ]
    artifacts.extend(
        _skill_artifacts(
            domain=domain,
            name=name,
            version=version,
            storage_dir=storage_dir,
            expected_paths=expected_skill_paths,
        )
    )
    return {
        "id": f"{domain}/{name}@{version}",
        "assignment_id": row["id"],
        "position": int(row["position"]),
        "manifest": {
            key: value for key, value in manifest.items() if key != "artifact_paths"
        },
        "artifacts": artifacts,
    }


@router.get("")
def list_projects(
    request: Request, current_user: CurrentUser = Depends(get_current_user)
) -> dict[str, list[dict[str, str | bool]]]:
    connection = _connect(request)
    try:
        if current_user.role in {"owner", "admin"}:
            rows = connection.execute(
                """
                SELECT id, name, repo_url, repo_url_normalized, active
                FROM projects
                ORDER BY name ASC, id ASC
                """
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT projects.id, projects.name, projects.repo_url,
                       projects.repo_url_normalized, projects.active
                FROM projects
                JOIN project_members ON project_members.project_id = projects.id
                WHERE project_members.user_id = ? AND projects.active = 1
                ORDER BY projects.name ASC, projects.id ASC
                """,
                (current_user.id,),
            ).fetchall()
        return {"projects": [_project_response(row) for row in rows]}
    finally:
        connection.close()


@router.get("/by-name/{name:path}")
def get_project_by_name(
    name: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    connection = _connect(request)
    try:
        if current_user.role in {"owner", "admin"}:
            row = connection.execute(
                """
                SELECT id, name
                FROM projects
                WHERE name = ? AND active = 1
                """,
                (name,),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT projects.id, projects.name
                FROM projects
                JOIN project_members ON project_members.project_id = projects.id
                WHERE projects.name = ?
                  AND project_members.user_id = ?
                  AND projects.active = 1
                """,
                (name, current_user.id),
            ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="project not found"
            )
        return {"id": row["id"], "name": row["name"]}
    finally:
        connection.close()


@router.get("/{project_id}/packages")
def list_project_packages(
    project_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, list[dict[str, str | int | bool]]]:
    connection = _connect(request)
    try:
        if current_user.role in {"owner", "admin"}:
            _get_project(connection, project_id)
            active_filter = ""
            parameters: tuple[str, ...] = (project_id,)
        else:
            _ensure_member_can_read_project(connection, project_id, current_user.id)
            active_filter = "AND project_packages.active = 1"
            parameters = (project_id,)
        rows = connection.execute(
            f"""
            SELECT project_packages.id, project_packages.project_id, project_packages.package_id,
                   project_packages.version_ref, project_packages.position,
                   project_packages.active, packages.domain, packages.name
            FROM project_packages
            JOIN packages ON packages.id = project_packages.package_id
            WHERE project_packages.project_id = ? {active_filter}
            ORDER BY project_packages.position ASC, packages.domain ASC, packages.name ASC
            """,
            parameters,
        ).fetchall()
        return {
            "project_packages": [
                _project_package_response(connection, row) for row in rows
            ]
        }
    finally:
        connection.close()


@router.get("/{project_id}/pull-manifest")
def get_pull_manifest(
    project_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    connection = _connect(request)
    try:
        if current_user.role in {"owner", "admin"}:
            project = _get_active_project(connection, project_id)
        else:
            project = _ensure_member_can_read_project(
                connection, project_id, current_user.id
            )
        rows = _active_project_package_rows(connection, project_id)
        return {
            "project": {
                "id": project["id"],
                "name": project["name"],
                "repo_url_normalized": project["repo_url_normalized"],
            },
            "packages": [_pull_manifest_package(connection, row) for row in rows],
        }
    finally:
        connection.close()


@router.get("/{project_id}/packages:available")
def list_available_project_packages(
    project_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, list[dict[str, str]]]:
    _require_project_admin(current_user)
    connection = _connect(request)
    try:
        _get_active_project(connection, project_id)
        rows = connection.execute(
            """
            SELECT packages.id AS package_id, packages.domain, packages.name,
                   package_versions.version, package_versions.manifest_json
            FROM packages
            JOIN package_versions ON package_versions.package_id = packages.id
            WHERE NOT EXISTS (
                SELECT 1
                FROM project_packages
                WHERE project_packages.project_id = ?
                  AND project_packages.package_id = packages.id
                  AND project_packages.active = 1
            )
            ORDER BY packages.domain ASC, packages.name ASC, package_versions.version ASC
            """,
            (project_id,),
        ).fetchall()
        latest_by_package: dict[str, sqlite3.Row] = {}
        for row in rows:
            package_id = str(row["package_id"])
            current = latest_by_package.get(package_id)
            if current is None or _semver_key(str(row["version"])) > _semver_key(
                str(current["version"])
            ):
                latest_by_package[package_id] = row
        packages = []
        for row in sorted(
            latest_by_package.values(), key=lambda item: (item["domain"], item["name"])
        ):
            manifest = json.loads(str(row["manifest_json"]))
            packages.append(
                {
                    "package_ref": f"{row['domain']}/{row['name']}@{row['version']}",
                    "domain": str(row["domain"]),
                    "name": str(row["name"]),
                    "version": str(row["version"]),
                    "description": str(manifest.get("description", "")),
                }
            )
        return {"packages": packages}
    finally:
        connection.close()


def _semver_key(version: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in version.split("."))  # type: ignore[return-value]


@router.post("/{project_id}/packages", status_code=status.HTTP_201_CREATED)
def assign_project_package(
    project_id: str,
    payload: ProjectPackageAssign,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | int | bool]:
    _require_project_admin(current_user)
    package_ref = _parse_package_ref_or_400(payload.package_ref)
    connection = _connect(request)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _get_active_project(connection, project_id)
            package_row = _package_row_or_404(connection, package_ref)
            _resolve_package_version(
                connection, str(package_row["id"]), package_ref.version
            )
            existing = connection.execute(
                """
                SELECT id, active FROM project_packages
                WHERE project_id = ? AND package_id = ?
                """,
                (project_id, package_row["id"]),
            ).fetchone()
            if existing is not None and existing["active"] == 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="project package assignment already exists",
                )
            if existing is None:
                assignment_id = generate_prefixed_id("asn")
                connection.execute(
                    """
                    INSERT INTO project_packages
                        (id, project_id, package_id, version_ref, position, active)
                    VALUES (?, ?, ?, ?, ?, 1)
                    """,
                    (
                        assignment_id,
                        project_id,
                        package_row["id"],
                        package_ref.version,
                        payload.position,
                    ),
                )
            else:
                assignment_id = str(existing["id"])
                connection.execute(
                    """
                    UPDATE project_packages
                    SET version_ref = ?, position = ?, active = 1,
                        updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (package_ref.version, payload.position, assignment_id),
                )
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="project package assignment already exists",
            ) from exc
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        row = _assignment_row(connection, project_id, assignment_id)
        return _project_package_response(connection, row)
    finally:
        connection.close()


@router.patch("/{project_id}/packages/{assignment_id}")
def update_project_package(
    project_id: str,
    assignment_id: str,
    payload: ProjectPackageUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | int | bool]:
    _require_project_admin(current_user)
    connection = _connect(request)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _get_active_project(connection, project_id)
            current = _assignment_row(connection, project_id, assignment_id)
            fields: dict[str, Any] = {}
            if payload.package_ref is not None:
                package_ref = _parse_package_ref_or_400(payload.package_ref)
                package_row = _package_row_or_404(connection, package_ref)
                _resolve_package_version(
                    connection, str(package_row["id"]), package_ref.version
                )
                fields["package_id"] = str(package_row["id"])
                fields["version_ref"] = package_ref.version
            if payload.position is not None:
                fields["position"] = payload.position
            if payload.active is not None:
                fields["active"] = 1 if payload.active else 0
            if fields:
                assignments = ", ".join(f"{field} = ?" for field in fields)
                values = list(fields.values()) + [current["id"]]
                sql = (
                    f"UPDATE project_packages SET {assignments}, "
                    "updated_at = datetime('now') WHERE id = ?"
                )
                connection.execute(sql, values)
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="project package assignment already exists",
            ) from exc
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        row = _assignment_row(connection, project_id, assignment_id)
        return _project_package_response(connection, row)
    finally:
        connection.close()


@router.delete("/{project_id}/packages/{assignment_id}")
def deactivate_project_package(
    project_id: str,
    assignment_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | int | bool]:
    _require_project_admin(current_user)
    connection = _connect(request)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _get_active_project(connection, project_id)
            _assignment_row(connection, project_id, assignment_id)
            connection.execute(
                """
                UPDATE project_packages
                SET active = 0, updated_at = datetime('now')
                WHERE id = ?
                """,
                (assignment_id,),
            )
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        row = _assignment_row(connection, project_id, assignment_id)
        return _project_package_response(connection, row)
    finally:
        connection.close()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    _require_project_admin(current_user)
    name = _clean_name(payload.name)
    repo_normalized = _normalize_repo_or_400(payload.repo_url)
    repo_url = payload.repo_url.strip()
    project_id = generate_prefixed_id("prj")

    connection = _connect(request)
    try:
        try:
            connection.execute(
                """
                INSERT INTO projects (id, name, repo_url, repo_url_normalized, active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (project_id, name, repo_url, repo_normalized),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            _raise_project_integrity_error(exc)
        return _project_response(_get_project(connection, project_id))
    finally:
        connection.close()


@router.get("/{project_id}")
def get_project(
    project_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    connection = _connect(request)
    try:
        if current_user.role in {"owner", "admin"}:
            row = _get_project(connection, project_id)
        else:
            row = _ensure_member_can_read_project(
                connection, project_id, current_user.id
            )
        return _project_response(row)
    finally:
        connection.close()


@router.patch("/{project_id}")
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    _require_project_admin(current_user)
    fields: dict[str, Any] = {}
    if payload.name is not None:
        fields["name"] = _clean_name(payload.name)
    if payload.repo_url is not None:
        fields["repo_url"] = payload.repo_url.strip()
        fields["repo_url_normalized"] = _normalize_repo_or_400(payload.repo_url)
    if payload.active is not None:
        fields["active"] = 1 if payload.active else 0

    connection = _connect(request)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _get_project(connection, project_id)
            if fields:
                assignments = ", ".join(f"{field} = ?" for field in fields)
                values = list(fields.values()) + [project_id]
                connection.execute(
                    f"UPDATE projects SET {assignments}, updated_at = datetime('now') WHERE id = ?",
                    values,
                )
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            _raise_project_integrity_error(exc)
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        return _project_response(_get_project(connection, project_id))
    finally:
        connection.close()


@router.delete("/{project_id}")
def deactivate_project(
    project_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    _require_project_admin(current_user)
    connection = _connect(request)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _get_project(connection, project_id)
            connection.execute(
                "UPDATE projects SET active = 0, updated_at = datetime('now') WHERE id = ?",
                (project_id,),
            )
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        return _project_response(_get_project(connection, project_id))
    finally:
        connection.close()


@router.get("/{project_id}/members")
def list_project_members(
    project_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, list[dict[str, str | bool]]]:
    _require_project_admin(current_user)
    connection = _connect(request)
    try:
        _get_active_project(connection, project_id)
        rows = connection.execute(
            """
            SELECT users.id, users.email, users.active
            FROM project_members
            JOIN users ON users.id = project_members.user_id
            WHERE project_members.project_id = ?
            ORDER BY users.email ASC, users.id ASC
            """,
            (project_id,),
        ).fetchall()
        return {
            "members": [
                {
                    "id": row["id"],
                    "email": row["email"],
                    "active": bool(row["active"]),
                }
                for row in rows
            ]
        }
    finally:
        connection.close()


@router.put("/{project_id}/members/{user_id}")
def add_project_member(
    project_id: str,
    user_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    _require_project_admin(current_user)
    connection = _connect(request)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _get_active_project(connection, project_id)
            _get_active_user(connection, user_id)
            connection.execute(
                "INSERT OR IGNORE INTO project_members (project_id, user_id) VALUES (?, ?)",
                (project_id, user_id),
            )
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        return {"project_id": project_id, "user_id": user_id}
    finally:
        connection.close()


@router.delete("/{project_id}/members/{user_id}")
def remove_project_member(
    project_id: str,
    user_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    _require_project_admin(current_user)
    connection = _connect(request)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _get_active_project(connection, project_id)
            if not is_valid_prefixed_id(user_id, "usr"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
                )
            connection.execute(
                "DELETE FROM project_members WHERE project_id = ? AND user_id = ?",
                (project_id, user_id),
            )
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        return {"project_id": project_id, "user_id": user_id, "removed": True}
    finally:
        connection.close()
