"""User administration and token lifecycle routes."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from agh.common.ids import generate_prefixed_id, is_valid_prefixed_id
from agh.common.validation import is_valid_email
from agh.server.auth import (
    CurrentUser,
    generate_api_token,
    get_current_user,
    hash_token,
)
from agh.server.db import connect_database

ROLES = {"owner", "admin", "member"}

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    email: str
    role: str


class UserUpdate(BaseModel):
    email: str | None = None
    role: str | None = None
    active: bool | None = None


def _user_response(row: sqlite3.Row) -> dict[str, str | bool]:
    return {
        "id": row["id"],
        "email": row["email"],
        "role": row["role"],
        "active": bool(row["active"]),
    }


def _require_user_admin(current_user: CurrentUser) -> None:
    if current_user.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _clean_email(email: str) -> str:
    cleaned = email.strip().lower()
    if not is_valid_email(cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid email"
        )
    return cleaned


def _clean_role(role: str) -> str:
    if role not in ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid role"
        )
    return role


def _connect(request: Request) -> sqlite3.Connection:
    return connect_database(getattr(request.app.state, "db_path", None))


def _get_user(connection: sqlite3.Connection, user_id: str) -> sqlite3.Row:
    if not is_valid_prefixed_id(user_id, "usr"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    row = connection.execute(
        "SELECT id, email, role, active FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    return row


def _ensure_actor_can_create(actor: CurrentUser, role: str) -> None:
    _require_user_admin(actor)
    if actor.role == "admin" and role != "member":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _ensure_actor_can_manage_target(
    actor: CurrentUser, target: sqlite3.Row, *, requested_role: str | None = None
) -> None:
    _require_user_admin(actor)
    if actor.role == "owner":
        return
    if target["role"] != "member" or (
        requested_role is not None and requested_role != "member"
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _active_owner_count(connection: sqlite3.Connection) -> int:
    return int(
        connection.execute(
            "SELECT COUNT(*) AS count FROM users WHERE role = 'owner' AND active = 1"
        ).fetchone()["count"]
    )


def _ensure_not_removing_last_owner(
    connection: sqlite3.Connection,
    target: sqlite3.Row,
    *,
    new_role: str | None = None,
    new_active: bool | None = None,
) -> None:
    role_after = target["role"] if new_role is None else new_role
    active_after = bool(target["active"]) if new_active is None else new_active
    removes_owner = (
        target["role"] == "owner"
        and bool(target["active"])
        and (role_after != "owner" or not active_after)
    )
    if removes_owner and _active_owner_count(connection) <= 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cannot remove last active owner",
        )


@router.get("")
def list_users(
    request: Request, current_user: CurrentUser = Depends(get_current_user)
) -> dict[str, list[dict[str, str | bool]]]:
    _require_user_admin(current_user)
    connection = _connect(request)
    try:
        rows = connection.execute(
            "SELECT id, email, role, active FROM users ORDER BY email ASC"
        ).fetchall()
        return {"users": [_user_response(row) for row in rows]}
    finally:
        connection.close()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    email = _clean_email(payload.email)
    role = _clean_role(payload.role)
    _ensure_actor_can_create(current_user, role)

    connection = _connect(request)
    try:
        user_id = generate_prefixed_id("usr")
        token = generate_api_token()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO users (id, email, role, active) VALUES (?, ?, ?, 1)",
                (user_id, email, role),
            )
            connection.execute(
                "INSERT INTO tokens (id, user_id, token_hash) VALUES (?, ?, ?)",
                (generate_prefixed_id("tok"), user_id, hash_token(token)),
            )
            created = _get_user(connection, user_id)
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            if "users.email" in str(exc) or "UNIQUE" in str(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="email already exists"
                ) from exc
            raise
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        return {"user": _user_response(created), "token": token}
    finally:
        connection.close()


@router.patch("/{user_id}")
def update_user(
    user_id: str,
    payload: UserUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    fields: dict[str, Any] = {}
    if payload.email is not None:
        fields["email"] = _clean_email(payload.email)
    if payload.role is not None:
        fields["role"] = _clean_role(payload.role)
    if payload.active is not None:
        fields["active"] = 1 if payload.active else 0

    _require_user_admin(current_user)
    connection = _connect(request)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            target = _get_user(connection, user_id)
            requested_role = fields.get("role")
            _ensure_actor_can_manage_target(
                current_user,
                target,
                requested_role=requested_role
                if isinstance(requested_role, str)
                else None,
            )
            _ensure_not_removing_last_owner(
                connection,
                target,
                new_role=fields.get("role")
                if isinstance(fields.get("role"), str)
                else None,
                new_active=bool(fields["active"]) if "active" in fields else None,
            )

            if fields:
                assignments = ", ".join(f"{field} = ?" for field in fields)
                values = list(fields.values()) + [user_id]
                connection.execute(
                    f"UPDATE users SET {assignments}, updated_at = datetime('now') WHERE id = ?",
                    values,
                )
            updated = _get_user(connection, user_id)
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            if "users.email" in str(exc) or "UNIQUE" in str(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="email already exists",
                ) from exc
            raise
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        return _user_response(updated)
    finally:
        connection.close()


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str | bool]:
    _require_user_admin(current_user)
    connection = _connect(request)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            target = _get_user(connection, user_id)
            _ensure_actor_can_manage_target(current_user, target)
            _ensure_not_removing_last_owner(connection, target, new_active=False)
            connection.execute(
                "UPDATE users SET active = 0, updated_at = datetime('now') WHERE id = ?",
                (user_id,),
            )
            updated = _get_user(connection, user_id)
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        return _user_response(updated)
    finally:
        connection.close()


def _rotate_or_reset_token(
    user_id: str,
    request: Request,
    current_user: CurrentUser,
) -> dict[str, str]:
    _require_user_admin(current_user)
    connection = _connect(request)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            target = _get_user(connection, user_id)
            _ensure_actor_can_manage_target(current_user, target)
            token = generate_api_token()
            connection.execute(
                "UPDATE tokens SET revoked_at = datetime('now') WHERE user_id = ? AND revoked_at IS NULL",
                (user_id,),
            )
            connection.execute(
                "INSERT INTO tokens (id, user_id, token_hash) VALUES (?, ?, ?)",
                (generate_prefixed_id("tok"), user_id, hash_token(token)),
            )
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        return {"token": token}
    finally:
        connection.close()


@router.post("/{user_id}/token:rotate")
def rotate_user_token(
    user_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    return _rotate_or_reset_token(user_id, request, current_user)


@router.post("/{user_id}/token:reset")
def reset_user_token(
    user_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    return _rotate_or_reset_token(user_id, request, current_user)
