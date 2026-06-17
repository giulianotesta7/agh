"""Collection route tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from agh.server.app import create_app


def _client(tmp_path: Path, monkeypatch) -> tuple[TestClient, str]:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    client = TestClient(create_app())
    token = (tmp_path / "secrets" / "initial_owner_token").read_text().strip()
    return client, token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _user(client: TestClient, token: str, email: str, role: str) -> str:
    response = client.post(
        "/api/v1/users", json={"email": email, "role": role}, headers=_auth(token)
    )
    assert response.status_code == 201, response.text
    return str(response.json()["token"])


def _collection(
    client: TestClient,
    token: str,
    name: str = "Team Skills",
    description: str = "Curated",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/collections",
        json={"name": name, "description": description},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_collection_routes_require_authentication(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    collection = _collection(client, owner)

    assert client.get("/api/v1/collections").status_code == 401
    assert (
        client.post("/api/v1/collections", json={"name": "No Auth"}).status_code == 401
    )
    assert client.get(f"/api/v1/collections/{collection['id']}").status_code == 401
    assert (
        client.patch(
            f"/api/v1/collections/{collection['id']}", json={"description": "No Auth"}
        ).status_code
        == 401
    )


def test_owner_and_admin_can_manage_collections(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    admin = _user(client, owner, "admin@example.com", "admin")
    created = _collection(client, owner)

    patched = client.patch(
        f"/api/v1/collections/{created['id']}",
        json={"description": "Updated"},
        headers=_auth(admin),
    )
    fetched = client.get(f"/api/v1/collections/{created['id']}", headers=_auth(owner))

    assert created == {
        "id": created["id"],
        "name": "Team Skills",
        "description": "Curated",
        "active": True,
    }
    assert created["id"].startswith("col_")
    assert patched.status_code == 200, patched.text
    assert fetched.json()["description"] == "Updated"


def test_members_read_and_list_active_collections_only(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    member = _user(client, owner, "dev@example.com", "member")
    active = _collection(client, owner, name="Active Skills")
    inactive = _collection(client, owner, name="Inactive Skills")

    deleted = client.delete(
        f"/api/v1/collections/{inactive['id']}", headers=_auth(owner)
    )
    listed = client.get("/api/v1/collections", headers=_auth(member))
    active_get = client.get(
        f"/api/v1/collections/{active['id']}", headers=_auth(member)
    )
    inactive_get = client.get(
        f"/api/v1/collections/{inactive['id']}", headers=_auth(member)
    )

    assert deleted.status_code == 200
    assert deleted.json()["active"] is False
    assert listed.json() == {"collections": [active]}
    assert active_get.json() == active
    assert inactive_get.status_code == 404


def test_admins_can_list_inactive_collections(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    admin = _user(client, owner, "admin@example.com", "admin")
    active = _collection(client, owner, name="Active Skills")
    inactive = _collection(client, owner, name="Inactive Skills")
    client.delete(f"/api/v1/collections/{inactive['id']}", headers=_auth(owner))

    expected = {"collections": [active, {**inactive, "active": False}]}

    assert client.get("/api/v1/collections", headers=_auth(owner)).json() == expected
    assert client.get("/api/v1/collections", headers=_auth(admin)).json() == expected


def test_owner_and_admin_can_fetch_inactive_collection_directly(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    admin = _user(client, owner, "admin@example.com", "admin")
    inactive = _collection(client, owner, name="Inactive Skills")

    deleted = client.delete(
        f"/api/v1/collections/{inactive['id']}", headers=_auth(owner)
    )
    expected = {**inactive, "active": False}

    assert deleted.status_code == 200
    assert (
        client.get(f"/api/v1/collections/{inactive['id']}", headers=_auth(owner)).json()
        == expected
    )
    assert (
        client.get(f"/api/v1/collections/{inactive['id']}", headers=_auth(admin)).json()
        == expected
    )


def test_member_mutations_and_invalid_input_are_rejected(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    member = _user(client, owner, "dev@example.com", "member")
    collection = _collection(client, owner)

    assert (
        client.post(
            "/api/v1/collections", json={"name": "Member"}, headers=_auth(member)
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/collections/{collection['id']}",
            json={"description": "No"},
            headers=_auth(member),
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/collections/{collection['id']}", headers=_auth(member)
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/collections", json={"name": "   "}, headers=_auth(owner)
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/collections", json={"name": "Team Skills"}, headers=_auth(owner)
        ).status_code
        == 409
    )
    assert (
        client.get("/api/v1/collections/not-a-col", headers=_auth(owner)).status_code
        == 404
    )
