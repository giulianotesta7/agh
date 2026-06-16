"""Representative API JSON error contract tests.

These tests document the current FastAPI-style error payloads. They are not an
AGH-specific error envelope design.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient  # pyright: ignore[reportMissingImports]

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
    client: TestClient, owner_token: str, email: str, role: str = "member"
) -> tuple[dict[str, Any], str]:
    response = client.post(
        "/api/v1/users", json={"email": email, "role": role}, headers=_auth(owner_token)
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["user"], body["token"]


def _create_project(client: TestClient, owner_token: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/projects",
        json={"name": "App", "repo_url": "git@github.com:acme/app.git"},
        headers=_auth(owner_token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _package_files(*, agents: str = "# Guide\n") -> dict[str, str]:
    return {
        "agh.package.toml": (
            'domain = "acme"\n'
            'name = "onboarding"\n'
            'version = "1.0.0"\n'
            'description = "Team onboarding"\n'
        ),
        "instructions/AGENTS.md": agents,
    }


def _publish_package(
    client: TestClient, owner_token: str, *, agents: str = "# Guide\n"
):
    return client.post(
        "/api/v1/packages",
        json={"files": _package_files(agents=agents)},
        headers=_auth(owner_token),
    )


def test_api_errors_are_json_for_auth_failures(tmp_path: Path, monkeypatch) -> None:
    client, _owner_token = _client_with_owner(tmp_path, monkeypatch)

    missing = client.get("/api/v1/me")
    invalid = client.get("/api/v1/me", headers=_auth("not-a-real-token"))

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert missing.json() == {"detail": "missing bearer token"}
    assert invalid.status_code == 401
    assert invalid.headers["www-authenticate"] == "Bearer"
    assert invalid.json() == {"detail": "invalid bearer token"}


def test_api_errors_are_json_for_forbidden_role(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    _member, member_token = _create_user(
        client, owner_token, "member@example.com", role="member"
    )

    response = client.post(
        "/api/v1/packages",
        json={"files": _package_files()},
        headers=_auth(member_token),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


def test_api_errors_are_json_for_missing_resources(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    project = client.get("/api/v1/projects/prj_missing", headers=_auth(owner_token))
    package_file = client.get(
        "/api/v1/packages/acme/missing/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )

    assert project.status_code == 404
    assert project.json() == {"detail": "project not found"}
    assert package_file.status_code == 404
    assert package_file.json() == {"detail": "package file not found"}


def test_api_errors_are_json_for_validation_failures(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    schema_validation = client.post(
        "/api/v1/projects",
        json={"name": "Missing repo URL"},
        headers=_auth(owner_token),
    )
    package_ref_validation = client.get(
        "/api/v1/packages/acme/onboarding/versions/latest/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )
    manifest_validation = client.post(
        "/api/v1/packages",
        json={"files": {"instructions/AGENTS.md": "# Missing manifest\n"}},
        headers=_auth(owner_token),
    )

    assert schema_validation.status_code == 422
    assert isinstance(schema_validation.json()["detail"], list)
    assert schema_validation.json()["detail"][0]["type"] == "missing"
    assert package_ref_validation.status_code == 404
    assert package_ref_validation.json() == {"detail": "package not found"}
    assert manifest_validation.status_code == 400
    assert "agh.package.toml" in manifest_validation.json()["detail"]


def test_api_errors_are_json_for_duplicate_and_conflict_cases(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    project = _create_project(client, owner_token)
    first_pack = _publish_package(client, owner_token)
    duplicate_pack = _publish_package(client, owner_token, agents="# Replacement\n")
    duplicate_project = client.post(
        "/api/v1/projects",
        json={"name": "Duplicate", "repo_url": "https://github.com/acme/app.git"},
        headers=_auth(owner_token),
    )
    missing_assignment_pack = client.post(
        f"/api/v1/projects/{project['id']}/packages",
        json={"package_ref": "acme/missing@1.0.0", "position": 0},
        headers=_auth(owner_token),
    )

    assert first_pack.status_code == 201, first_pack.text
    assert duplicate_pack.status_code == 409
    assert duplicate_pack.json() == {"detail": "package version already exists"}
    assert duplicate_project.status_code == 409
    assert duplicate_project.json() == {
        "detail": "active project repo URL already exists"
    }
    assert missing_assignment_pack.status_code == 404
    assert missing_assignment_pack.json() == {"detail": "package not found"}
