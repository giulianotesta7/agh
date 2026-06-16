"""Project package assignment route tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from agh.server.app import create_app


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


def _create_project(
    client: TestClient, token: str, name: str = "App"
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/projects",
        json={"name": name, "repo_url": f"git@github.com:org/{name.lower()}.git"},
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
        "instructions/AGENTS.md": f"# {domain}/{name} {version}\n",
    }


def _publish_package(client: TestClient, token: str, ref: str) -> dict[str, Any]:
    pair, version = ref.split("@", 1)
    domain, name = pair.split("/", 1)
    response = client.post(
        "/api/v1/packages",
        json={"files": _package_files(domain, name, version)},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _assign_package(
    client: TestClient,
    token: str,
    project_id: str,
    package_ref: str,
    *,
    position: int = 0,
):
    return client.post(
        f"/api/v1/projects/{project_id}/packages",
        json={"package_ref": package_ref, "position": position},
        headers=_auth(token),
    )


def test_admin_assigns_concrete_and_latest_package_versions_with_ordering(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    project = _create_project(client, owner_token)
    _publish_package(client, owner_token, "acme/onboarding@1.0.0")
    _publish_package(client, owner_token, "acme/onboarding@1.2.0")
    _publish_package(client, owner_token, "acme/baseline@1.0.0")

    latest = _assign_package(
        client, owner_token, project["id"], "acme/onboarding@latest", position=20
    )
    concrete = _assign_package(
        client, owner_token, project["id"], "acme/baseline@1.0.0", position=20
    )

    assert latest.status_code == 201, latest.text
    assert latest.json() == {
        "id": latest.json()["id"],
        "project_id": project["id"],
        "package_id": latest.json()["package_id"],
        "package_ref": "acme/onboarding@latest",
        "resolved_ref": "acme/onboarding@1.2.0",
        "domain": "acme",
        "name": "onboarding",
        "version_ref": "latest",
        "resolved_version": "1.2.0",
        "position": 20,
        "active": True,
    }
    assert latest.json()["id"].startswith("asn_")
    assert concrete.status_code == 201, concrete.text

    listed = client.get(
        f"/api/v1/projects/{project['id']}/packages", headers=_auth(owner_token)
    )
    assert listed.status_code == 200
    assert [item["package_ref"] for item in listed.json()["project_packages"]] == [
        "acme/baseline@1.0.0",
        "acme/onboarding@latest",
    ]


def test_available_packages_returns_unassigned_latest_stable_refs(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    project = _create_project(client, owner_token)
    _publish_package(client, owner_token, "acme/onboarding@1.0.0")
    _publish_package(client, owner_token, "acme/onboarding@1.2.0")
    _publish_package(client, owner_token, "acme/baseline@2.0.0")
    _assign_package(client, owner_token, project["id"], "acme/baseline@latest")

    response = client.get(
        f"/api/v1/projects/{project['id']}/packages:available",
        headers=_auth(owner_token),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "packages": [
            {
                "package_ref": "acme/onboarding@1.2.0",
                "domain": "acme",
                "name": "onboarding",
                "version": "1.2.0",
                "description": "acme/onboarding 1.2.0",
            }
        ]
    }


def test_project_developer_lists_only_active_assignments(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    member, member_token = _create_user(
        client, owner_token, "dev@example.com", "member"
    )
    project = _create_project(client, owner_token)
    _publish_package(client, owner_token, "acme/onboarding@1.0.0")
    assignment = _assign_package(
        client, owner_token, project["id"], "acme/onboarding@1.0.0"
    )
    assert assignment.status_code == 201, assignment.text

    before_membership = client.get(
        f"/api/v1/projects/{project['id']}/packages", headers=_auth(member_token)
    )
    assert before_membership.status_code == 404

    assert (
        client.put(
            f"/api/v1/projects/{project['id']}/members/{member['id']}",
            headers=_auth(owner_token),
        ).status_code
        == 200
    )
    visible = client.get(
        f"/api/v1/projects/{project['id']}/packages", headers=_auth(member_token)
    )
    assert visible.status_code == 200
    assert [item["id"] for item in visible.json()["project_packages"]] == [
        assignment.json()["id"]
    ]

    removed = client.delete(
        f"/api/v1/projects/{project['id']}/packages/{assignment.json()['id']}",
        headers=_auth(owner_token),
    )
    assert removed.status_code == 200
    assert removed.json()["active"] is False
    hidden = client.get(
        f"/api/v1/projects/{project['id']}/packages", headers=_auth(member_token)
    )
    assert hidden.status_code == 200
    assert hidden.json() == {"project_packages": []}


def test_assignment_update_position_version_and_deactivation(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    project = _create_project(client, owner_token)
    _publish_package(client, owner_token, "acme/onboarding@1.0.0")
    _publish_package(client, owner_token, "acme/onboarding@1.2.0")
    assignment = _assign_package(
        client, owner_token, project["id"], "acme/onboarding@1.0.0"
    )
    assert assignment.status_code == 201, assignment.text

    patched = client.patch(
        f"/api/v1/projects/{project['id']}/packages/{assignment.json()['id']}",
        json={"package_ref": "acme/onboarding@latest", "position": 7},
        headers=_auth(owner_token),
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["version_ref"] == "latest"
    assert patched.json()["resolved_version"] == "1.2.0"
    assert patched.json()["position"] == 7

    deactivated = client.patch(
        f"/api/v1/projects/{project['id']}/packages/{assignment.json()['id']}",
        json={"active": False},
        headers=_auth(owner_token),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False

    reactivated = _assign_package(
        client, owner_token, project["id"], "acme/onboarding@1.0.0"
    )
    assert reactivated.status_code == 201
    assert reactivated.json()["id"] == assignment.json()["id"]
    assert reactivated.json()["active"] is True


def test_assignment_validation_and_authorization(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    member, member_token = _create_user(
        client, owner_token, "dev@example.com", "member"
    )
    project = _create_project(client, owner_token)
    _publish_package(client, owner_token, "acme/onboarding@1.0.0")

    forbidden = _assign_package(
        client, member_token, project["id"], "acme/onboarding@1.0.0"
    )
    assert forbidden.status_code == 403

    missing_pack = _assign_package(
        client, owner_token, project["id"], "acme/missing@latest"
    )
    assert missing_pack.status_code == 404
    missing_version = _assign_package(
        client, owner_token, project["id"], "acme/onboarding@9.9.9"
    )
    assert missing_version.status_code == 404
    invalid_ref = _assign_package(client, owner_token, project["id"], "not a ref")
    assert invalid_ref.status_code == 400

    assignment = _assign_package(
        client, owner_token, project["id"], "acme/onboarding@1.0.0"
    )
    assert assignment.status_code == 201
    duplicate = _assign_package(
        client, owner_token, project["id"], "acme/onboarding@1.0.0"
    )
    assert duplicate.status_code == 409

    deactivated_project = client.delete(
        f"/api/v1/projects/{project['id']}", headers=_auth(owner_token)
    )
    assert deactivated_project.status_code == 200
    inactive_create = _assign_package(
        client, owner_token, project["id"], "acme/onboarding@1.0.0"
    )
    assert inactive_create.status_code == 404
    inactive_update = client.patch(
        f"/api/v1/projects/{project['id']}/packages/{assignment.json()['id']}",
        json={"position": 5},
        headers=_auth(owner_token),
    )
    assert inactive_update.status_code == 404

    member_mutations = [
        client.patch(
            f"/api/v1/projects/{project['id']}/packages/{assignment.json()['id']}",
            json={"position": 2},
            headers=_auth(member_token),
        ),
        client.delete(
            f"/api/v1/projects/{project['id']}/packages/{assignment.json()['id']}",
            headers=_auth(member_token),
        ),
    ]
    assert [response.status_code for response in member_mutations] == [403, 403]
