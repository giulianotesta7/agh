"""Project CRUD, membership, and access-control route tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient  # pyright: ignore[reportMissingImports]

from agh.server.app import create_app
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
    client: TestClient,
    token: str,
    name: str = "Platform",
    repo_url: str = "git@github.com:org/app.git",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/projects",
        json={"name": name, "repo_url": repo_url},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_project_crud_and_duplicate_active_repo_conflicts(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    created = _create_project(client, owner_token)
    assert created == {
        "id": created["id"],
        "name": "Platform",
        "repo_url": "git@github.com:org/app.git",
        "repo_url_normalized": "github.com/org/app",
        "active": True,
    }
    assert created["id"].startswith("prj_")

    duplicate_name = client.post(
        "/api/v1/projects",
        json={"name": "Platform", "repo_url": "https://github.com/org/platform.git"},
        headers=_auth(owner_token),
    )
    assert duplicate_name.status_code == 409
    assert duplicate_name.json()["detail"] == "project name already exists"

    digit_only_name = client.post(
        "/api/v1/projects",
        json={"name": "12345", "repo_url": "https://github.com/org/numeric.git"},
        headers=_auth(owner_token),
    )
    assert digit_only_name.status_code == 400
    assert "cannot contain only digits" in digit_only_name.json()["detail"]

    duplicate = client.post(
        "/api/v1/projects",
        json={"name": "Duplicate", "repo_url": "https://github.com/org/app.git"},
        headers=_auth(owner_token),
    )
    assert duplicate.status_code == 409
    mixed_case_duplicate = client.post(
        "/api/v1/projects",
        json={"name": "Mixed Case", "repo_url": "git@github.com:Org/App.GIT"},
        headers=_auth(owner_token),
    )
    assert mixed_case_duplicate.status_code == 409
    encoded_host_duplicate = client.post(
        "/api/v1/projects",
        json={"name": "Encoded Host", "repo_url": "https://github%2ecom/org/app.git"},
        headers=_auth(owner_token),
    )
    assert encoded_host_duplicate.status_code == 409
    host_dot_https_duplicate = client.post(
        "/api/v1/projects",
        json={"name": "Host Dot HTTPS", "repo_url": "https://github.com./Org/App.GIT/"},
        headers=_auth(owner_token),
    )
    assert host_dot_https_duplicate.status_code == 409
    host_dot_ssh_url_duplicate = client.post(
        "/api/v1/projects",
        json={
            "name": "Host Dot SSH URL",
            "repo_url": "ssh://git@github.com./Org/App.GIT/",
        },
        headers=_auth(owner_token),
    )
    assert host_dot_ssh_url_duplicate.status_code == 409
    host_dot_scp_duplicate = client.post(
        "/api/v1/projects",
        json={"name": "Host Dot SCP", "repo_url": "git@github.com.:Org/App.GIT"},
        headers=_auth(owner_token),
    )
    assert host_dot_scp_duplicate.status_code == 409
    duplicate_variants = [
        ("Percent Encoded", "https://github.com/org/app%2Egit"),
        ("Encoded Slash", "https://github.com/org/app.git%2F"),
        ("Dot Segment", "https://github.com/org/./app.git"),
        ("Encoded Dot Segment", "https://github.com/org/%2e/app.git"),
        ("Parent Segment", "https://github.com/org/../org/app.git"),
        ("SCP Dot Segment", "git@github.com:org/./app.git"),
        ("Git Suffix Dot", "https://github.com/org/app.git/."),
    ]
    for name, repo_url in duplicate_variants:
        response = client.post(
            "/api/v1/projects",
            json={"name": name, "repo_url": repo_url},
            headers=_auth(owner_token),
        )
        assert response.status_code == 409, (name, response.text)

    connection = connect_database(get_database_path(tmp_path))
    try:
        rows = connection.execute(
            "SELECT name, repo_url FROM projects WHERE repo_url_normalized = ?",
            ("github.com/org/app",),
        ).fetchall()
        assert [(row["name"], row["repo_url"]) for row in rows] == [
            ("Platform", "git@github.com:org/app.git")
        ]
    finally:
        connection.close()

    patched = client.patch(
        f"/api/v1/projects/{created['id']}",
        json={"name": "Platform API", "repo_url": "https://github.com/org/api.git"},
        headers=_auth(owner_token),
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["name"] == "Platform API"
    assert patched.json()["repo_url_normalized"] == "github.com/org/api"

    digit_only_rename = client.patch(
        f"/api/v1/projects/{created['id']}",
        json={"name": "12345"},
        headers=_auth(owner_token),
    )
    assert digit_only_rename.status_code == 400
    assert "cannot contain only digits" in digit_only_rename.json()["detail"]

    second = _create_project(
        client, owner_token, name="Other", repo_url="git@github.com:org/other.git"
    )
    conflict = client.patch(
        f"/api/v1/projects/{second['id']}",
        json={"repo_url": "git@github.com:Org/API.git"},
        headers=_auth(owner_token),
    )
    assert conflict.status_code == 409
    assert (
        client.get(
            f"/api/v1/projects/{second['id']}", headers=_auth(owner_token)
        ).json()["repo_url_normalized"]
        == "github.com/org/other"
    )

    deleted = client.delete(
        f"/api/v1/projects/{created['id']}", headers=_auth(owner_token)
    )
    assert deleted.status_code == 200
    assert deleted.json()["active"] is False

    reuse = client.post(
        "/api/v1/projects",
        json={"name": "Replacement", "repo_url": "git@github.com:org/api.git"},
        headers=_auth(owner_token),
    )
    assert reuse.status_code == 201, reuse.text

    listed = client.get("/api/v1/projects", headers=_auth(owner_token))
    assert listed.status_code == 200
    assert {project["id"] for project in listed.json()["projects"]} >= {
        created["id"],
        second["id"],
        reuse.json()["id"],
    }


def test_member_reads_only_active_developer_projects_and_membership_removal_revokes_access(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    member, member_token = _create_user(
        client, owner_token, "dev@example.com", "member"
    )
    accessible = _create_project(
        client,
        owner_token,
        name="Accessible",
        repo_url="git@github.com:org/accessible.git",
    )
    hidden = _create_project(
        client, owner_token, name="Hidden", repo_url="git@github.com:org/hidden.git"
    )

    before = client.get("/api/v1/projects", headers=_auth(member_token))
    assert before.status_code == 200
    assert before.json() == {"projects": []}
    assert (
        client.get(
            f"/api/v1/projects/{hidden['id']}", headers=_auth(member_token)
        ).status_code
        == 404
    )

    added = client.put(
        f"/api/v1/projects/{accessible['id']}/members/{member['id']}",
        headers=_auth(owner_token),
    )
    assert added.status_code == 200, added.text
    assert added.json() == {"project_id": accessible["id"], "user_id": member["id"]}

    member_listing = client.get(
        f"/api/v1/projects/{accessible['id']}/members", headers=_auth(owner_token)
    )
    assert member_listing.status_code == 200, member_listing.text
    assert member_listing.json() == {
        "members": [
            {
                "id": member["id"],
                "email": "dev@example.com",
                "active": True,
            }
        ]
    }

    listed = client.get("/api/v1/projects", headers=_auth(member_token))
    assert listed.status_code == 200
    assert listed.json() == {"projects": [accessible]}
    direct = client.get(
        f"/api/v1/projects/{accessible['id']}", headers=_auth(member_token)
    )
    assert direct.status_code == 200
    assert direct.json() == accessible

    removed = client.delete(
        f"/api/v1/projects/{accessible['id']}/members/{member['id']}",
        headers=_auth(owner_token),
    )
    assert removed.status_code == 200
    assert removed.json() == {
        "project_id": accessible["id"],
        "user_id": member["id"],
        "removed": True,
    }
    assert (
        client.get(
            f"/api/v1/projects/{accessible['id']}", headers=_auth(member_token)
        ).status_code
        == 404
    )
    assert client.get("/api/v1/projects", headers=_auth(member_token)).json() == {
        "projects": []
    }

    empty_listing = client.get(
        f"/api/v1/projects/{accessible['id']}/members", headers=_auth(owner_token)
    )
    assert empty_listing.status_code == 200, empty_listing.text
    assert empty_listing.json() == {"members": []}


def test_deactivated_member_user_still_listed_with_inactive_status(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    member, _member_token = _create_user(
        client, owner_token, "dev@example.com", "member"
    )
    project = _create_project(client, owner_token)

    assert (
        client.put(
            f"/api/v1/projects/{project['id']}/members/{member['id']}",
            headers=_auth(owner_token),
        ).status_code
        == 200
    )

    before = client.get(
        f"/api/v1/projects/{project['id']}/members", headers=_auth(owner_token)
    )
    assert before.status_code == 200, before.text
    assert before.json() == {
        "members": [{"id": member["id"], "email": "dev@example.com", "active": True}]
    }

    deactivated = client.delete(
        f"/api/v1/users/{member['id']}", headers=_auth(owner_token)
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False

    after = client.get(
        f"/api/v1/projects/{project['id']}/members", headers=_auth(owner_token)
    )
    assert after.status_code == 200, after.text
    assert after.json() == {
        "members": [{"id": member["id"], "email": "dev@example.com", "active": False}]
    }


def test_project_name_resolver_is_exact_active_and_visibility_scoped(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    member, member_token = _create_user(
        client, owner_token, "dev@example.com", "member"
    )
    visible = _create_project(
        client, owner_token, name="Visible", repo_url="git@github.com:org/visible.git"
    )
    _create_project(
        client, owner_token, name="Hidden", repo_url="git@github.com:org/hidden.git"
    )
    assert (
        client.put(
            f"/api/v1/projects/{visible['id']}/members/{member['id']}",
            headers=_auth(owner_token),
        ).status_code
        == 200
    )

    resolved = client.get(
        "/api/v1/projects/by-name/Visible", headers=_auth(owner_token)
    )
    assert resolved.status_code == 200
    assert resolved.json() == {"id": visible["id"], "name": "Visible"}

    member_resolved = client.get(
        "/api/v1/projects/by-name/Visible", headers=_auth(member_token)
    )
    assert member_resolved.status_code == 200
    assert member_resolved.json()["id"] == visible["id"]

    assert (
        client.get(
            "/api/v1/projects/by-name/visible", headers=_auth(owner_token)
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/api/v1/projects/by-name/Hidden", headers=_auth(member_token)
        ).status_code
        == 404
    )
    assert client.get("/api/v1/projects/by-name/Visible").status_code == 401


def test_inactive_projects_are_denied_to_members_and_membership_changes(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    member, member_token = _create_user(
        client, owner_token, "dev@example.com", "member"
    )
    project = _create_project(client, owner_token)

    assert (
        client.put(
            f"/api/v1/projects/{project['id']}/members/{member['id']}",
            headers=_auth(owner_token),
        ).status_code
        == 200
    )
    deactivated = client.delete(
        f"/api/v1/projects/{project['id']}", headers=_auth(owner_token)
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False

    admin_read = client.get(
        f"/api/v1/projects/{project['id']}", headers=_auth(owner_token)
    )
    assert admin_read.status_code == 200
    assert admin_read.json()["active"] is False
    assert (
        client.get(
            f"/api/v1/projects/{project['id']}", headers=_auth(member_token)
        ).status_code
        == 404
    )
    assert client.get("/api/v1/projects", headers=_auth(member_token)).json() == {
        "projects": []
    }

    add_again = client.put(
        f"/api/v1/projects/{project['id']}/members/{member['id']}",
        headers=_auth(owner_token),
    )
    assert add_again.status_code == 404
    remove = client.delete(
        f"/api/v1/projects/{project['id']}/members/{member['id']}",
        headers=_auth(owner_token),
    )
    assert remove.status_code == 404


def test_project_routes_require_bearer_and_admin_for_mutations(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    member, member_token = _create_user(
        client, owner_token, "dev@example.com", "member"
    )
    inactive, _ = _create_user(client, owner_token, "inactive@example.com", "member")
    client.patch(
        f"/api/v1/users/{inactive['id']}",
        json={"active": False},
        headers=_auth(owner_token),
    )
    project = _create_project(client, owner_token)

    assert client.get("/api/v1/projects").status_code == 401

    forbidden_requests = [
        (
            "POST",
            "/api/v1/projects",
            {"name": "X", "repo_url": "git@github.com:org/x.git"},
        ),
        ("PATCH", f"/api/v1/projects/{project['id']}", {"name": "X"}),
        ("DELETE", f"/api/v1/projects/{project['id']}", None),
        ("PUT", f"/api/v1/projects/{project['id']}/members/{member['id']}", None),
        ("DELETE", f"/api/v1/projects/{project['id']}/members/{member['id']}", None),
        ("GET", f"/api/v1/projects/{project['id']}/members", None),
    ]
    for method, path, body in forbidden_requests:
        response = client.request(method, path, json=body, headers=_auth(member_token))
        assert response.status_code == 403

    inactive_user = client.put(
        f"/api/v1/projects/{project['id']}/members/{inactive['id']}",
        headers=_auth(owner_token),
    )
    assert inactive_user.status_code == 404
    missing_user = client.put(
        f"/api/v1/projects/{project['id']}/members/usr_missing0000000",
        headers=_auth(owner_token),
    )
    assert missing_user.status_code == 404
