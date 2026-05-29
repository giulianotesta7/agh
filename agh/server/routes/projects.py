"""Project CRUD, developer membership, and project access routes."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import (  # pyright: ignore[reportMissingImports]
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from pydantic import BaseModel  # pyright: ignore[reportMissingImports]

from agh.common.ids import generate_prefixed_id, is_valid_prefixed_id
from agh.common.repo_url import normalize_repo_url
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
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="project name is required"
        )
    return cleaned


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


def _raise_duplicate_repo(exc: sqlite3.IntegrityError) -> None:
    if "ux_projects_active_repo_url_normalized" in str(exc) or "UNIQUE" in str(exc):
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
            _raise_duplicate_repo(exc)
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
            _raise_duplicate_repo(exc)
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
