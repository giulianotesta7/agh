"""Collection CRUD routes."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from agh.common.ids import generate_prefixed_id, is_valid_prefixed_id
from agh.server.auth import CurrentUser, get_current_user
from agh.server.db import connect_database

router = APIRouter(tags=["collections"])


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
    if user.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="collection name is required")
    return cleaned


def _row_to_response(row: sqlite3.Row) -> dict[str, str | bool]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "active": bool(row["active"]),
    }


def _collection(conn: sqlite3.Connection, collection_id: str) -> sqlite3.Row:
    if not is_valid_prefixed_id(collection_id, "col"):
        raise HTTPException(status_code=404, detail="collection not found")
    row = conn.execute(
        "SELECT id, name, description, active FROM collections WHERE id = ?",
        (collection_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="collection not found")
    return row


def _visible_collection(
    conn: sqlite3.Connection, collection_id: str, user: CurrentUser
) -> sqlite3.Row:
    row = _collection(conn, collection_id)
    if user.role not in {"owner", "admin"} and row["active"] != 1:
        raise HTTPException(status_code=404, detail="collection not found")
    return row


@router.get("/collections")
def list_collections(
    request: Request, current_user: CurrentUser = Depends(get_current_user)
) -> dict[str, list[dict[str, str | bool]]]:
    conn = _connect(request)
    try:
        where = "" if current_user.role in {"owner", "admin"} else "WHERE active = 1"
        rows = conn.execute(
            f"SELECT id, name, description, active FROM collections {where} ORDER BY name ASC"
        ).fetchall()
        return {"collections": [_row_to_response(row) for row in rows]}
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
                    payload.description,
                    current_user.id,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(
                status_code=409, detail="collection name already exists"
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
        fields["description"] = payload.description
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
                status_code=409, detail="collection name already exists"
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
