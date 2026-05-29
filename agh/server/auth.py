"""Authentication and first-start bootstrap helpers for AGH server."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agh.common.ids import generate_prefixed_id
from agh.common.validation import is_valid_email
from agh.server.db import connect_database, get_data_dir, get_database_path

_BOOTSTRAP_TOKEN_BYTES = 32
_bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger("agh")


@dataclass(frozen=True)
class CurrentUser:
    """Authenticated AGH user context."""

    id: str
    email: str
    role: str


def generate_api_token() -> str:
    """Generate a URL-safe plaintext API token for one-time presentation."""
    return secrets.token_urlsafe(_BOOTSTRAP_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Return the persisted hash for an API token."""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def bootstrap_initial_owner(
    *, data_dir: Path | str | None = None, db_path: Path | str | None = None
) -> None:
    """Create the initial owner and token when the user store is empty.

    The plaintext token is written only to ``<AGH_DATA_DIR>/secrets``. If any
    user already exists, bootstrap is skipped and the existing secret file is not
    touched.
    """
    root = Path(data_dir) if data_dir is not None else get_data_dir()
    database_path = Path(db_path) if db_path is not None else get_database_path(root)
    email = os.environ.get("AGH_BOOTSTRAP_OWNER_EMAIL", "").strip()

    connection = connect_database(database_path)
    try:
        if not email:
            logger.info("AGH bootstrap skipped; AGH_BOOTSTRAP_OWNER_EMAIL is unset")
            return
        if not is_valid_email(email):
            raise RuntimeError("AGH_BOOTSTRAP_OWNER_EMAIL must be a valid email")

        connection.execute("BEGIN IMMEDIATE")
        try:
            user_count = connection.execute(
                "SELECT COUNT(*) AS count FROM users"
            ).fetchone()["count"]
            if user_count:
                connection.rollback()
                logger.info("AGH bootstrap skipped; user store is not empty")
                return

            token = generate_api_token()
            user_id = generate_prefixed_id("usr")
            token_id = generate_prefixed_id("tok")
            token_digest = hash_token(token)
            secret_path = root / "secrets" / "initial_owner_token"

            connection.execute(
                "INSERT INTO users (id, email, role, active) VALUES (?, ?, ?, 1)",
                (user_id, email, "owner"),
            )
            connection.execute(
                "INSERT INTO tokens (id, user_id, token_hash) VALUES (?, ?, ?)",
                (token_id, user_id, token_digest),
            )
            _write_secret_file(secret_path, token)
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()

        logger.info("AGH bootstrap owner token written to %s", secret_path)
    finally:
        connection.close()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """FastAPI dependency that authenticates a Bearer token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    presented_hash = hash_token(credentials.credentials)
    db_path = getattr(request.app.state, "db_path", None)
    connection = connect_database(db_path)
    try:
        row = connection.execute(
            """
            SELECT users.id, users.email, users.role, users.active, tokens.token_hash
            FROM tokens
            JOIN users ON users.id = tokens.user_id
            WHERE tokens.token_hash = ? AND tokens.revoked_at IS NULL
            """,
            (presented_hash,),
        ).fetchone()
        if row is not None and hmac.compare_digest(row["token_hash"], presented_hash):
            if row["active"] != 1:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="user is inactive",
                )
            return CurrentUser(
                id=row["id"],
                email=row["email"],
                role=row["role"],
            )
    finally:
        connection.close()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _write_secret_file(secret_path: Path, token: str) -> None:
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(secret_path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"{token}\n")
    except Exception:
        os.close(fd)
        raise
    with suppress(OSError):  # pragma: no cover - best effort on non-POSIX platforms
        os.chmod(secret_path, 0o600)
