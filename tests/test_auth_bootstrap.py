"""Auth bootstrap and current-user endpoint tests."""

from __future__ import annotations

import logging
import os
import stat
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from agh.server.app import create_app
from agh.server.auth import bootstrap_initial_owner, hash_token
from agh.server.db import connect_database, get_database_path, run_migrations


def _token_file(data_dir: Path) -> Path:
    return data_dir / "secrets" / "initial_owner_token"


def test_bootstrap_creates_owner_token_hash_and_secret_file(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    caplog.set_level(logging.INFO, logger="agh")

    create_app()

    secret_path = _token_file(tmp_path)
    assert secret_path.is_file()
    plaintext_token = secret_path.read_text(encoding="utf-8").strip()
    assert plaintext_token

    connection = connect_database(get_database_path(tmp_path))
    try:
        users = connection.execute(
            "SELECT id, email, role, active FROM users"
        ).fetchall()
        assert len(users) == 1
        assert users[0]["email"] == "owner@example.com"
        assert users[0]["role"] == "owner"
        assert users[0]["active"] == 1

        tokens = connection.execute("SELECT token_hash FROM tokens").fetchall()
        assert len(tokens) == 1
        assert tokens[0]["token_hash"] == hash_token(plaintext_token)
        assert tokens[0]["token_hash"] != plaintext_token
    finally:
        connection.close()

    assert plaintext_token not in (tmp_path / "logs" / "agh.log").read_text(
        encoding="utf-8"
    )
    assert plaintext_token not in caplog.text
    if os.name == "posix":
        assert stat.S_IMODE(secret_path.stat().st_mode) == 0o600


def test_bootstrap_does_not_overwrite_secret_or_create_user_when_user_exists(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    create_app()
    secret_path = _token_file(tmp_path)
    first_token = secret_path.read_text(encoding="utf-8")

    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "other@example.com")
    create_app()

    assert secret_path.read_text(encoding="utf-8") == first_token
    connection = connect_database(get_database_path(tmp_path))
    try:
        rows = connection.execute("SELECT email FROM users ORDER BY email").fetchall()
        assert [row["email"] for row in rows] == ["owner@example.com"]
        token_count = connection.execute(
            "SELECT COUNT(*) AS count FROM tokens"
        ).fetchone()
        assert token_count["count"] == 1
    finally:
        connection.close()


def test_concurrent_bootstrap_creates_exactly_one_owner(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    db_path = get_database_path(tmp_path)
    run_migrations(db_path)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(bootstrap_initial_owner, data_dir=tmp_path, db_path=db_path)
            for _ in range(2)
        ]
        for future in futures:
            future.result()

    connection = connect_database(db_path)
    try:
        user_count = connection.execute(
            "SELECT COUNT(*) AS count FROM users"
        ).fetchone()["count"]
        token_count = connection.execute(
            "SELECT COUNT(*) AS count FROM tokens"
        ).fetchone()["count"]
        assert user_count == 1
        assert token_count == 1
    finally:
        connection.close()
    assert _token_file(tmp_path).is_file()


def test_no_bootstrap_owner_without_env_email(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("AGH_BOOTSTRAP_OWNER_EMAIL", raising=False)

    create_app()

    assert not _token_file(tmp_path).exists()
    connection = connect_database(get_database_path(tmp_path))
    try:
        assert (
            connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()[
                "count"
            ]
            == 0
        )
        assert (
            connection.execute("SELECT COUNT(*) AS count FROM tokens").fetchone()[
                "count"
            ]
            == 0
        )
    finally:
        connection.close()


def test_me_requires_bearer_and_returns_current_user(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    application = create_app()
    client = TestClient(application)
    token = _token_file(tmp_path).read_text(encoding="utf-8").strip()

    missing = client.get("/api/v1/me")
    assert missing.status_code == 401

    malformed = client.get("/api/v1/me", headers={"Authorization": "Token nope"})
    assert malformed.status_code == 401

    invalid = client.get("/api/v1/me", headers={"Authorization": "Bearer nope"})
    assert invalid.status_code == 401

    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {
        "id": response.json()["id"],
        "email": "owner@example.com",
        "role": "owner",
    }
    assert response.json()["id"].startswith("usr_")
    assert "token" not in response.text


def test_revoked_token_returns_unauthorized(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    application = create_app()
    token = _token_file(tmp_path).read_text(encoding="utf-8").strip()

    connection = connect_database(get_database_path(tmp_path))
    try:
        connection.execute(
            "UPDATE tokens SET revoked_at = datetime('now') WHERE token_hash = ?",
            (hash_token(token),),
        )
        connection.commit()
    finally:
        connection.close()

    response = TestClient(application).get(
        "/api/v1/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_inactive_user_token_returns_forbidden(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    application = create_app()
    token = _token_file(tmp_path).read_text(encoding="utf-8").strip()

    connection = connect_database(get_database_path(tmp_path))
    try:
        connection.execute(
            "UPDATE users SET active = 0 WHERE email = ?", ("owner@example.com",)
        )
        connection.commit()
    finally:
        connection.close()

    response = TestClient(application).get(
        "/api/v1/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_health_remains_public_when_auth_enabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
