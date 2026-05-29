"""User administration and token lifecycle route tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient  # pyright: ignore[reportMissingImports]

from agh.server.app import create_app
from agh.server.auth import hash_token
from agh.server.db import connect_database, get_database_path


def _client_with_owner(tmp_path: Path, monkeypatch) -> tuple[TestClient, str]:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    client = TestClient(create_app())
    token = (
        (tmp_path / "secrets" / "initial_owner_token")
        .read_text(encoding="utf-8")
        .strip()
    )
    return client, token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_user_response(
    client: TestClient, token: str, email: str, role: str
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/users", json={"email": email, "role": role}, headers=_auth(token)
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"user", "token"}
    assert body["token"]
    assert "token_hash" not in response.text
    return body


def _create_user(
    client: TestClient, token: str, email: str, role: str
) -> dict[str, Any]:
    return _create_user_response(client, token, email, role)["user"]


def _rotate_token(client: TestClient, actor_token: str, user_id: str) -> str:
    response = client.post(
        f"/api/v1/users/{user_id}/token:rotate", headers=_auth(actor_token)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"token"}
    assert body["token"]
    return body["token"]


def test_owner_user_crud_lists_no_token_hashes(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    create_response = client.post(
        "/api/v1/users",
        json={"email": "admin@example.com", "role": "admin"},
        headers=_auth(owner_token),
    )
    assert create_response.status_code == 201
    create_body = create_response.json()
    created = create_body["user"]
    initial_token = create_body["token"]

    created_id = cast(str, created["id"])
    assert created_id.startswith("usr_")
    assert created == {
        "id": created["id"],
        "email": "admin@example.com",
        "role": "admin",
        "active": True,
    }
    assert "token" not in created
    assert "token_hash" not in created
    assert (
        client.get("/api/v1/me", headers=_auth(initial_token)).json()["email"]
        == "admin@example.com"
    )

    listed = client.get("/api/v1/users", headers=_auth(owner_token))
    assert listed.status_code == 200
    assert {user["email"] for user in listed.json()["users"]} == {
        "owner@example.com",
        "admin@example.com",
    }
    assert "token" not in listed.text
    assert "token_hash" not in listed.text

    patched = client.patch(
        f"/api/v1/users/{created['id']}",
        json={"email": "admin2@example.com", "role": "member"},
        headers=_auth(owner_token),
    )
    assert patched.status_code == 200
    assert patched.json()["email"] == "admin2@example.com"
    assert patched.json()["role"] == "member"

    deleted = client.delete(
        f"/api/v1/users/{created['id']}", headers=_auth(owner_token)
    )
    assert deleted.status_code == 200
    assert deleted.json()["active"] is False

    connection = connect_database(get_database_path(tmp_path))
    try:
        row = connection.execute(
            "SELECT active FROM users WHERE id = ?", (created["id"],)
        ).fetchone()
        assert row["active"] == 0
    finally:
        connection.close()


def test_admin_can_manage_members_but_not_admins_or_owners(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    admin = _create_user(client, owner_token, "admin@example.com", "admin")
    admin_token = _rotate_token(client, owner_token, str(admin["id"]))

    member = _create_user(client, admin_token, "member@example.com", "member")
    assert member["role"] == "member"

    create_admin = client.post(
        "/api/v1/users",
        json={"email": "other-admin@example.com", "role": "admin"},
        headers=_auth(admin_token),
    )
    assert create_admin.status_code == 403

    promote_member = client.patch(
        f"/api/v1/users/{member['id']}",
        json={"role": "admin"},
        headers=_auth(admin_token),
    )
    assert promote_member.status_code == 403

    change_admin = client.patch(
        f"/api/v1/users/{admin['id']}",
        json={"email": "renamed-admin@example.com"},
        headers=_auth(admin_token),
    )
    assert change_admin.status_code == 403

    deactivate_owner = client.delete(
        "/api/v1/users/"
        + client.get("/api/v1/me", headers=_auth(owner_token)).json()["id"],
        headers=_auth(admin_token),
    )
    assert deactivate_owner.status_code == 403

    deactivate_member = client.patch(
        f"/api/v1/users/{member['id']}",
        json={"active": False},
        headers=_auth(admin_token),
    )
    assert deactivate_member.status_code == 200
    assert deactivate_member.json()["active"] is False


def test_member_cannot_administer_users(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    member = _create_user(client, owner_token, "member@example.com", "member")
    member_token = _rotate_token(client, owner_token, str(member["id"]))

    forbidden_requests = [
        ("GET", "/api/v1/users", None),
        ("POST", "/api/v1/users", {"email": "new@example.com", "role": "member"}),
        ("PATCH", f"/api/v1/users/{member['id']}", {"email": "new@example.com"}),
        ("DELETE", f"/api/v1/users/{member['id']}", None),
        ("POST", f"/api/v1/users/{member['id']}/token:reset", None),
    ]
    for method, path, body in forbidden_requests:
        response = client.request(method, path, json=body, headers=_auth(member_token))
        assert response.status_code == 403


def test_member_cannot_probe_user_existence_from_target_routes(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    member = _create_user(client, owner_token, "member@example.com", "member")
    member_token = _rotate_token(client, owner_token, str(member["id"]))

    for path in (f"/api/v1/users/{member['id']}", "/api/v1/users/usr_missing0000000"):
        patch = client.patch(
            path, json={"email": "probe@example.com"}, headers=_auth(member_token)
        )
        delete = client.delete(path, headers=_auth(member_token))
        rotate = client.post(f"{path}/token:rotate", headers=_auth(member_token))
        reset = client.post(f"{path}/token:reset", headers=_auth(member_token))

        assert patch.status_code == 403
        assert delete.status_code == 403
        assert rotate.status_code == 403
        assert reset.status_code == 403


def test_invalid_and_duplicate_email_are_rejected(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    invalid = client.post(
        "/api/v1/users",
        json={"email": "not-an-email", "role": "member"},
        headers=_auth(owner_token),
    )
    assert invalid.status_code == 400

    create_response = client.post(
        "/api/v1/users",
        json={"email": "Member@Example.com", "role": "member"},
        headers=_auth(owner_token),
    )
    assert create_response.status_code == 201
    create_body = create_response.json()
    created = create_body["user"]
    initial_token = create_body["token"]
    assert created["email"] == "member@example.com"
    assert (
        client.get("/api/v1/me", headers=_auth(initial_token)).json()["email"]
        == "member@example.com"
    )
    connection = connect_database(get_database_path(tmp_path))
    try:
        rows = connection.execute(
            "SELECT token_hash FROM tokens WHERE user_id = ?", (created["id"],)
        ).fetchall()
        assert [row["token_hash"] for row in rows] == [hash_token(initial_token)]
        assert initial_token not in rows[0]["token_hash"]
    finally:
        connection.close()
    duplicate = client.post(
        "/api/v1/users",
        json={"email": "member@example.com", "role": "member"},
        headers=_auth(owner_token),
    )
    assert duplicate.status_code == 409


def test_token_rotate_and_reset_revoke_previous_tokens_and_store_hash_only(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    created = _create_user_response(client, owner_token, "member@example.com", "member")
    member = created["user"]
    initial = created["token"]

    first = _rotate_token(client, owner_token, str(member["id"]))
    assert client.get("/api/v1/me", headers=_auth(first)).status_code == 200

    reset = client.post(
        f"/api/v1/users/{member['id']}/token:reset", headers=_auth(owner_token)
    )
    assert reset.status_code == 200
    second = reset.json()["token"]
    assert second != first
    assert client.get("/api/v1/me", headers=_auth(first)).status_code == 401
    assert (
        client.get("/api/v1/me", headers=_auth(second)).json()["email"]
        == "member@example.com"
    )

    connection = connect_database(get_database_path(tmp_path))
    try:
        rows = connection.execute(
            "SELECT token_hash, revoked_at FROM tokens WHERE user_id = ?",
            (member["id"],),
        ).fetchall()
        rows_by_hash = {row["token_hash"]: row for row in rows}
        assert set(rows_by_hash) == {
            hash_token(initial),
            hash_token(first),
            hash_token(second),
        }
        assert rows_by_hash[hash_token(initial)]["revoked_at"] is not None
        assert rows_by_hash[hash_token(first)]["revoked_at"] is not None
        assert rows_by_hash[hash_token(second)]["revoked_at"] is None
        assert initial not in rows_by_hash
        assert first not in rows_by_hash
        assert second not in rows_by_hash
    finally:
        connection.close()


def test_admin_can_rotate_member_token_only(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    admin = _create_user(client, owner_token, "admin@example.com", "admin")
    member = _create_user(client, owner_token, "member@example.com", "member")
    admin_token = _rotate_token(client, owner_token, str(admin["id"]))

    member_rotation = client.post(
        f"/api/v1/users/{member['id']}/token:rotate", headers=_auth(admin_token)
    )
    assert member_rotation.status_code == 200
    assert set(member_rotation.json()) == {"token"}

    admin_rotation = client.post(
        f"/api/v1/users/{admin['id']}/token:rotate", headers=_auth(admin_token)
    )
    assert admin_rotation.status_code == 403


def test_concurrent_owner_demotions_preserve_at_least_one_active_owner(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    first_owner_id = client.get("/api/v1/me", headers=_auth(owner_token)).json()["id"]
    second_owner = _create_user(client, owner_token, "owner2@example.com", "owner")

    def demote(user_id: str):
        return client.patch(
            f"/api/v1/users/{user_id}",
            json={"role": "member"},
            headers=_auth(owner_token),
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(demote, [first_owner_id, str(second_owner["id"])]))

    assert statuses.count(200) == 1
    assert statuses.count(403) == 1
    connection = connect_database(get_database_path(tmp_path))
    try:
        active_owner_count = connection.execute(
            "SELECT COUNT(*) AS count FROM users WHERE role = 'owner' AND active = 1"
        ).fetchone()["count"]
        assert active_owner_count == 1
    finally:
        connection.close()


def test_cannot_deactivate_delete_or_demote_sole_owner(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    owner_id = client.get("/api/v1/me", headers=_auth(owner_token)).json()["id"]

    demote = client.patch(
        f"/api/v1/users/{owner_id}", json={"role": "member"}, headers=_auth(owner_token)
    )
    assert demote.status_code == 403

    deactivate = client.patch(
        f"/api/v1/users/{owner_id}", json={"active": False}, headers=_auth(owner_token)
    )
    assert deactivate.status_code == 403

    delete = client.delete(f"/api/v1/users/{owner_id}", headers=_auth(owner_token))
    assert delete.status_code == 403

    another_owner = _create_user(client, owner_token, "owner2@example.com", "owner")
    demote_after_second_owner = client.patch(
        f"/api/v1/users/{owner_id}", json={"role": "admin"}, headers=_auth(owner_token)
    )
    assert demote_after_second_owner.status_code == 200
    assert demote_after_second_owner.json()["role"] == "admin"
    assert another_owner["role"] == "owner"
