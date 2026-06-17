"""Collection package assignment route tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import status
from fastapi.testclient import TestClient

from agh.common.ids import generate_prefixed_id, is_valid_prefixed_id
from agh.server.app import create_app
from agh.server.db import connect_database, run_migrations


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


def _create_user(
    client: TestClient, token: str, email: str, role: str
) -> tuple[dict[str, Any], str]:
    response = client.post(
        "/api/v1/users", json={"email": email, "role": role}, headers=_auth(token)
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["user"], body["token"]


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
    return response.json()


def _package_files(domain: str, name: str, version: str) -> dict[str, str]:
    return {
        "agh.package.toml": (
            f'domain = "{domain}"\n'
            f'name = "{name}"\n'
            f'version = "{version}"\n'
            f'description = "{domain}/{name} {version}"\n'
        ),
        "skills/comment-writer/SKILL.md": f"# {domain}/{name} {version}\n",
    }


def _publish_package(
    client: TestClient, token: str, ref: str, files: dict[str, str]
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/packages",
        json={"files": files},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _assign_package(
    client: TestClient,
    token: str,
    collection_id: str,
    package_ref: str,
    *,
    position: int = 0,
) -> Any:
    return client.post(
        f"/api/v1/collections/{collection_id}/packages",
        json={"package_ref": package_ref, "position": position},
        headers=_auth(token),
    )


def test_collection_assignment_id_prefix_is_supported() -> None:
    assignment_id = generate_prefixed_id("casn")

    assert is_valid_prefixed_id(assignment_id, "casn")


def test_collection_packages_table_is_migrated(tmp_path: Path) -> None:
    db_path = tmp_path / "agh.sqlite3"
    run_migrations(db_path)
    connection = connect_database(db_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "collection_packages" in tables
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(collection_packages)"
            ).fetchall()
        }
        assert {
            "id",
            "collection_id",
            "package_id",
            "version_ref",
            "position",
            "active",
        } <= columns
        applied = [
            row[0]
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        ]
        assert "006_collection_packages" in applied
    finally:
        connection.close()


def test_owner_and_admin_can_assign_packages(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    admin = _create_user(client, owner, "admin@example.com", "admin")[1]
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/onboarding@1.0.0",
        _package_files("acme", "onboarding", "1.0.0"),
    )
    _publish_package(
        client,
        owner,
        "acme/onboarding@1.2.0",
        _package_files("acme", "onboarding", "1.2.0"),
    )
    _publish_package(
        client,
        owner,
        "acme/baseline@1.0.0",
        _package_files("acme", "baseline", "1.0.0"),
    )

    latest = _assign_package(
        client, owner, collection["id"], "acme/onboarding@latest", position=10
    )
    concrete = _assign_package(
        client, admin, collection["id"], "acme/baseline@1.0.0", position=20
    )

    assert latest.status_code == status.HTTP_201_CREATED, latest.text
    assert latest.json()["id"].startswith("casn_")
    assert latest.json()["collection_id"] == collection["id"]
    assert latest.json()["package_ref"] == "acme/onboarding@latest"
    assert latest.json()["resolved_ref"] == "acme/onboarding@1.2.0"
    assert latest.json()["resolved_version"] == "1.2.0"
    assert latest.json()["position"] == 10
    assert latest.json()["active"] is True

    assert concrete.status_code == status.HTTP_201_CREATED, concrete.text
    assert concrete.json()["resolved_ref"] == "acme/baseline@1.0.0"

    listed = client.get(
        f"/api/v1/collections/{collection['id']}/packages", headers=_auth(owner)
    )
    assert listed.status_code == 200
    assert [item["package_ref"] for item in listed.json()["collection_packages"]] == [
        "acme/onboarding@latest",
        "acme/baseline@1.0.0",
    ]


def test_assignment_authorization_and_validation(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    member = _create_user(client, owner, "dev@example.com", "member")[1]
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/onboarding@1.0.0",
        _package_files("acme", "onboarding", "1.0.0"),
    )

    assert (
        _assign_package(
            client, member, collection["id"], "acme/onboarding@1.0.0"
        ).status_code
        == 403
    )
    assert (
        _assign_package(client, owner, collection["id"], "not a ref").status_code == 400
    )
    assert (
        _assign_package(
            client, owner, collection["id"], "acme/missing@1.0.0"
        ).status_code
        == 404
    )
    assert (
        _assign_package(
            client, owner, collection["id"], "acme/onboarding@9.9.9"
        ).status_code
        == 404
    )

    assignment = _assign_package(
        client, owner, collection["id"], "acme/onboarding@1.0.0"
    )
    assert assignment.status_code == 201
    duplicate = _assign_package(
        client, owner, collection["id"], "acme/onboarding@1.0.0"
    )
    assert duplicate.status_code == 409

    deactivated = client.delete(
        f"/api/v1/collections/{collection['id']}", headers=_auth(owner)
    )
    assert deactivated.status_code == 200
    assert (
        _assign_package(
            client, owner, collection["id"], "acme/onboarding@1.0.0"
        ).status_code
        == 404
    )


def test_collection_package_assignment_update_and_deactivation(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    member = _create_user(client, owner, "dev@example.com", "member")[1]
    collection = _collection(client, owner)
    _publish_package(
        client, owner, "acme/a@1.0.0", _package_files("acme", "a", "1.0.0")
    )
    _publish_package(
        client, owner, "acme/a@1.2.0", _package_files("acme", "a", "1.2.0")
    )
    _publish_package(
        client, owner, "acme/b@1.0.0", _package_files("acme", "b", "1.0.0")
    )
    assignment = _assign_package(client, owner, collection["id"], "acme/a@1.0.0")
    assert assignment.status_code == 201

    patched = client.patch(
        f"/api/v1/collections/{collection['id']}/packages/{assignment.json()['id']}",
        json={"package_ref": "acme/a@latest", "position": 5},
        headers=_auth(owner),
    )
    assert patched.status_code == 200
    assert patched.json()["resolved_ref"] == "acme/a@1.2.0"
    assert patched.json()["position"] == 5

    bad_update = client.patch(
        f"/api/v1/collections/{collection['id']}/packages/{assignment.json()['id']}",
        json={"package_ref": "acme/missing@1.0.0"},
        headers=_auth(owner),
    )
    assert bad_update.status_code == status.HTTP_404_NOT_FOUND

    deactivated = client.delete(
        f"/api/v1/collections/{collection['id']}/packages/{assignment.json()['id']}",
        headers=_auth(owner),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False

    member_mutations = [
        client.patch(
            f"/api/v1/collections/{collection['id']}/packages/{assignment.json()['id']}",
            json={"position": 2},
            headers=_auth(member),
        ),
        client.delete(
            f"/api/v1/collections/{collection['id']}/packages/{assignment.json()['id']}",
            headers=_auth(member),
        ),
    ]
    assert [response.status_code for response in member_mutations] == [403, 403]
