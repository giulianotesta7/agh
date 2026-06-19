"""Collection route tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import status
from fastapi.testclient import TestClient

from agh.server.app import create_app


def _by_name_url(name: str) -> str:
    """Build a by-name resolver URL with the exact collection name encoded."""
    return f"/api/v1/collections/by-name/{quote(name, safe='')}"


MAX_COLLECTION_NAME_LENGTH = 80
MAX_COLLECTION_DESCRIPTION_LENGTH = 1000


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
    assert client.delete(f"/api/v1/collections/{collection['id']}").status_code == 401


def test_owner_and_admin_can_manage_collections(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    admin = _user(client, owner, "admin@example.com", "admin")
    created = _collection(client, owner)
    admin_created = _collection(client, admin, name="Admin Skills")

    patched = client.patch(
        f"/api/v1/collections/{created['id']}",
        json={"name": "Platform Skills", "description": "Updated"},
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
    assert admin_created["name"] == "Admin Skills"
    assert patched.status_code == 200, patched.text
    assert patched.json()["name"] == "Platform Skills"
    assert fetched.json()["description"] == "Updated"


def test_admin_can_reactivate_collection(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    admin = _user(client, owner, "admin@example.com", "admin")
    collection = _collection(client, owner)

    deactivated = client.delete(
        f"/api/v1/collections/{collection['id']}", headers=_auth(owner)
    )
    reactivated = client.patch(
        f"/api/v1/collections/{collection['id']}",
        json={"active": True},
        headers=_auth(admin),
    )

    assert deactivated.status_code == status.HTTP_200_OK
    assert reactivated.status_code == status.HTTP_200_OK, reactivated.text
    assert reactivated.json()["active"] is True


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


def test_update_rejects_invalid_and_duplicate_collection_names(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    first = _collection(client, owner, name="First Skills")
    second = _collection(client, owner, name="Second Skills")

    blank = client.patch(
        f"/api/v1/collections/{first['id']}",
        json={"name": "   "},
        headers=_auth(owner),
    )
    too_long = client.patch(
        f"/api/v1/collections/{first['id']}",
        json={"name": "x" * (MAX_COLLECTION_NAME_LENGTH + 1)},
        headers=_auth(owner),
    )
    duplicate = client.patch(
        f"/api/v1/collections/{first['id']}",
        json={"name": second["name"]},
        headers=_auth(owner),
    )

    assert blank.status_code == status.HTTP_400_BAD_REQUEST
    assert too_long.status_code == status.HTTP_400_BAD_REQUEST
    assert duplicate.status_code == status.HTTP_409_CONFLICT


def test_create_rejects_oversized_description(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    oversized_description = "x" * (MAX_COLLECTION_DESCRIPTION_LENGTH + 1)

    response = client.post(
        "/api/v1/collections",
        json={"name": "Valid Name", "description": oversized_description},
        headers=_auth(owner),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_collection_payload_lengths_are_bounded(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    collection = _collection(client, owner)
    oversized_description = "x" * (MAX_COLLECTION_DESCRIPTION_LENGTH + 1)

    create_response = client.post(
        "/api/v1/collections",
        json={"name": "x" * (MAX_COLLECTION_NAME_LENGTH + 1)},
        headers=_auth(owner),
    )
    update_response = client.patch(
        f"/api/v1/collections/{collection['id']}",
        json={"description": oversized_description},
        headers=_auth(owner),
    )

    assert create_response.status_code == status.HTTP_400_BAD_REQUEST
    assert update_response.status_code == status.HTTP_400_BAD_REQUEST


def test_collection_payload_exact_length_boundaries_are_accepted(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    exact_name = "x" * MAX_COLLECTION_NAME_LENGTH
    exact_description = "y" * MAX_COLLECTION_DESCRIPTION_LENGTH

    create_response = client.post(
        "/api/v1/collections",
        json={"name": exact_name, "description": exact_description},
        headers=_auth(owner),
    )
    assert create_response.status_code == status.HTTP_201_CREATED, create_response.text
    created = create_response.json()
    assert created["name"] == exact_name
    assert created["description"] == exact_description

    update_name = "a" * MAX_COLLECTION_NAME_LENGTH
    update_description = "b" * MAX_COLLECTION_DESCRIPTION_LENGTH
    update_response = client.patch(
        f"/api/v1/collections/{created['id']}",
        json={"name": update_name, "description": update_description},
        headers=_auth(owner),
    )
    assert update_response.status_code == status.HTTP_200_OK, update_response.text
    updated = update_response.json()
    assert updated["name"] == update_name
    assert updated["description"] == update_description


def test_resolve_active_collection_by_exact_name(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    collection = _collection(client, owner, name="Team Skills")

    resolved = client.get(_by_name_url("Team Skills"), headers=_auth(owner))

    assert resolved.status_code == status.HTTP_200_OK, resolved.text
    assert resolved.json() == {"id": collection["id"], "name": "Team Skills"}


def test_resolve_collection_by_name_requires_authentication(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    _collection(client, owner, name="Team Skills")

    assert (
        client.get(_by_name_url("Team Skills")).status_code
        == status.HTTP_401_UNAUTHORIZED
    )


def test_resolve_collection_by_name_404_for_inactive(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    collection = _collection(client, owner, name="Team Skills")
    client.delete(f"/api/v1/collections/{collection['id']}", headers=_auth(owner))

    owner_lookup = client.get(_by_name_url("Team Skills"), headers=_auth(owner))
    admin = _user(client, owner, "admin@example.com", "admin")
    admin_lookup = client.get(_by_name_url("Team Skills"), headers=_auth(admin))

    assert owner_lookup.status_code == status.HTTP_404_NOT_FOUND
    assert admin_lookup.status_code == status.HTTP_404_NOT_FOUND


def test_resolve_collection_by_name_is_case_sensitive(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    _collection(client, owner, name="Team Skills")

    lower = client.get(_by_name_url("team skills"), headers=_auth(owner))
    alternate = client.get(_by_name_url("TEAM SKILLS"), headers=_auth(owner))

    assert lower.status_code == status.HTTP_404_NOT_FOUND
    assert alternate.status_code == status.HTTP_404_NOT_FOUND


def test_resolve_collection_by_name_requires_active_collection_for_authenticated_users(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client(tmp_path, monkeypatch)
    member = _user(client, owner, "dev@example.com", "member")
    active = _collection(client, owner, name="Visible Skills")
    inactive = _collection(client, owner, name="Hidden Skills")
    client.delete(f"/api/v1/collections/{inactive['id']}", headers=_auth(owner))

    active_member = client.get(_by_name_url("Visible Skills"), headers=_auth(member))
    inactive_member = client.get(_by_name_url("Hidden Skills"), headers=_auth(member))

    assert active_member.status_code == status.HTTP_200_OK, active_member.text
    assert active_member.json() == {"id": active["id"], "name": "Visible Skills"}
    assert inactive_member.status_code == status.HTTP_404_NOT_FOUND
