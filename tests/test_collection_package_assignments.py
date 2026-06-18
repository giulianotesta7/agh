"""Collection package assignment and skill discovery route tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import status
from fastapi.testclient import TestClient

from agh.common.ids import generate_prefixed_id, is_valid_prefixed_id
from agh.server.app import create_app
from agh.server.db import connect_database, get_database_path, run_migrations


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


def _skill_only_package_files(domain: str, name: str, version: str) -> dict[str, str]:
    return {
        "agh.package.toml": (
            f'domain = "{domain}"\n'
            f'name = "{name}"\n'
            f'version = "{version}"\n'
            f'description = "{domain}/{name} {version}"\n'
        ),
        "skills/comment-writer/SKILL.md": f"# {domain}/{name} {version}\n",
        "skills/reviewer/SKILL.md": f"# {domain}/{name} reviewer {version}\n",
    }


def _instruction_package_files(domain: str, name: str, version: str) -> dict[str, str]:
    return {
        "agh.package.toml": (
            f'domain = "{domain}"\n'
            f'name = "{name}"\n'
            f'version = "{version}"\n'
            f'description = "{domain}/{name} {version}"\n'
        ),
        "instructions/AGENTS.md": f"# {domain}/{name} {version}\n",
        "skills/comment-writer/SKILL.md": f"# {domain}/{name} {version}\n",
    }


def _claude_instruction_package_files(
    domain: str, name: str, version: str
) -> dict[str, str]:
    return {
        "agh.package.toml": (
            f'domain = "{domain}"\n'
            f'name = "{name}"\n'
            f'version = "{version}"\n'
            f'description = "{domain}/{name} {version}"\n'
        ),
        "instructions/CLAUDE.md": f"# {domain}/{name} {version}\n",
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


def test_owner_and_admin_can_assign_skill_only_packages(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    admin = _create_user(client, owner, "admin@example.com", "admin")[1]
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/onboarding@1.0.0",
        _skill_only_package_files("acme", "onboarding", "1.0.0"),
    )
    _publish_package(
        client,
        owner,
        "acme/onboarding@1.2.0",
        _skill_only_package_files("acme", "onboarding", "1.2.0"),
    )
    _publish_package(
        client,
        owner,
        "acme/baseline@1.0.0",
        _skill_only_package_files("acme", "baseline", "1.0.0"),
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
        _skill_only_package_files("acme", "onboarding", "1.0.0"),
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


def test_assignment_rejects_instruction_bearing_packages(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/agents@1.0.0",
        _instruction_package_files("acme", "agents", "1.0.0"),
    )
    _publish_package(
        client,
        owner,
        "acme/claude@1.0.0",
        _claude_instruction_package_files("acme", "claude", "1.0.0"),
    )
    _publish_package(
        client,
        owner,
        "acme/skill-only@1.0.0",
        _skill_only_package_files("acme", "skill-only", "1.0.0"),
    )

    agents = _assign_package(client, owner, collection["id"], "acme/agents@1.0.0")
    claude = _assign_package(client, owner, collection["id"], "acme/claude@1.0.0")
    skill_only = _assign_package(
        client, owner, collection["id"], "acme/skill-only@1.0.0"
    )

    assert agents.status_code == status.HTTP_400_BAD_REQUEST
    assert "instructions" in agents.json()["detail"].lower()
    assert claude.status_code == status.HTTP_400_BAD_REQUEST
    assert skill_only.status_code == status.HTTP_201_CREATED


def test_assignment_rejects_latest_resolving_to_instruction_package(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/mixed@1.0.0",
        _skill_only_package_files("acme", "mixed", "1.0.0"),
    )
    _publish_package(
        client,
        owner,
        "acme/mixed@1.1.0",
        _instruction_package_files("acme", "mixed", "1.1.0"),
    )

    response = _assign_package(client, owner, collection["id"], "acme/mixed@latest")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "instructions" in response.json()["detail"].lower()


def test_member_lists_only_active_collection_skills(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    member = _create_user(client, owner, "dev@example.com", "member")[1]
    active_collection = _collection(client, owner, name="Active Skills")
    inactive_collection = _collection(client, owner, name="Inactive Skills")
    _publish_package(
        client, owner, "acme/a@1.0.0", _skill_only_package_files("acme", "a", "1.0.0")
    )
    _publish_package(
        client, owner, "acme/b@1.0.0", _skill_only_package_files("acme", "b", "1.0.0")
    )

    a = _assign_package(client, owner, active_collection["id"], "acme/a@1.0.0")
    b = _assign_package(client, owner, inactive_collection["id"], "acme/b@1.0.0")
    assert a.status_code == 201 and b.status_code == 201

    client.delete(
        f"/api/v1/collections/{inactive_collection['id']}", headers=_auth(owner)
    )

    listed = client.get("/api/v1/skills", headers=_auth(member))
    assert listed.status_code == 200
    skill_names = {item["skill_name"] for item in listed.json()["skills"]}
    assert skill_names == {"comment-writer", "reviewer"}
    assert all(
        item["collection_id"] == active_collection["id"]
        for item in listed.json()["skills"]
    )


def test_skills_list_excludes_inactive_assignments(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    member = _create_user(client, owner, "dev@example.com", "member")[1]
    collection = _collection(client, owner)
    _publish_package(
        client, owner, "acme/a@1.0.0", _skill_only_package_files("acme", "a", "1.0.0")
    )
    _publish_package(
        client, owner, "acme/b@1.0.0", _skill_only_package_files("acme", "b", "1.0.0")
    )

    a = _assign_package(client, owner, collection["id"], "acme/a@1.0.0")
    b = _assign_package(client, owner, collection["id"], "acme/b@1.0.0")
    assert a.status_code == 201 and b.status_code == 201

    client.delete(
        f"/api/v1/collections/{collection['id']}/packages/{b.json()['id']}",
        headers=_auth(owner),
    )

    listed = client.get("/api/v1/skills", headers=_auth(member))
    assert listed.status_code == 200
    refs = {item["resolved_ref"] for item in listed.json()["skills"]}
    assert refs == {"acme/a@1.0.0"}


def test_skills_list_returns_resolved_refs_and_checksums(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    collection = _collection(client, owner)
    version_100 = _publish_package(
        client,
        owner,
        "acme/tool-concrete@1.0.0",
        _skill_only_package_files("acme", "tool-concrete", "1.0.0"),
    )
    version_120 = _publish_package(
        client,
        owner,
        "acme/tool-latest@1.2.0",
        _skill_only_package_files("acme", "tool-latest", "1.2.0"),
    )
    _assign_package(client, owner, collection["id"], "acme/tool-concrete@1.0.0")
    _assign_package(client, owner, collection["id"], "acme/tool-latest@latest")

    listed = client.get("/api/v1/skills", headers=_auth(owner))
    assert listed.status_code == 200
    skills = listed.json()["skills"]
    concrete_rows = [
        item for item in skills if item["package_ref"] == "acme/tool-concrete@1.0.0"
    ]
    latest_rows = [
        item for item in skills if item["package_ref"] == "acme/tool-latest@latest"
    ]
    assert len(concrete_rows) == 2
    assert len(latest_rows) == 2
    assert concrete_rows[0]["resolved_ref"] == "acme/tool-concrete@1.0.0"
    assert latest_rows[0]["resolved_ref"] == "acme/tool-latest@1.2.0"
    assert concrete_rows[0]["checksum"] == version_100["checksum"]
    assert latest_rows[0]["checksum"] == version_120["checksum"]
    assert concrete_rows[0]["description"] == "acme/tool-concrete 1.0.0"


def test_skills_list_filters_by_collection_id(tmp_path: Path, monkeypatch) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    first = _collection(client, owner, name="First")
    second = _collection(client, owner, name="Second")
    _publish_package(
        client, owner, "acme/a@1.0.0", _skill_only_package_files("acme", "a", "1.0.0")
    )
    _publish_package(
        client, owner, "acme/b@1.0.0", _skill_only_package_files("acme", "b", "1.0.0")
    )
    _assign_package(client, owner, first["id"], "acme/a@1.0.0")
    _assign_package(client, owner, second["id"], "acme/b@1.0.0")

    filtered = client.get(
        f"/api/v1/skills?collection_id={first['id']}", headers=_auth(owner)
    )
    assert filtered.status_code == 200
    skills = filtered.json()["skills"]
    assert len(skills) == 2
    assert {item["resolved_ref"] for item in skills} == {"acme/a@1.0.0"}


def test_skills_list_logs_suppressed_invalid_assignment(
    tmp_path: Path, monkeypatch
) -> None:
    from unittest.mock import patch

    client, owner = _client_with_owner(tmp_path, monkeypatch)
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/tool@1.0.0",
        _skill_only_package_files("acme", "tool", "1.0.0"),
    )
    _assign_package(client, owner, collection["id"], "acme/tool@latest")
    _publish_package(
        client,
        owner,
        "acme/tool@1.1.0",
        _instruction_package_files("acme", "tool", "1.1.0"),
    )

    with patch("agh.server.routes.collections.LOGGER.warning") as mock_warning:
        response = client.get("/api/v1/skills", headers=_auth(owner))
    assert response.status_code == 200
    assert response.json()["skills"] == []
    mock_warning.assert_called_once()
    args, _kwargs = mock_warning.call_args
    log_message = args[0]
    log_args = args[1:]
    assert "Suppressed active collection assignment" in log_message
    assert collection["id"] in log_args
    assert "instructions" in str(log_args).lower()


def test_skills_list_suppresses_toctou_oserror_during_iteration(
    tmp_path: Path, monkeypatch
) -> None:
    from unittest.mock import patch

    client, owner = _client_with_owner(tmp_path, monkeypatch)
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/tool@1.0.0",
        _skill_only_package_files("acme", "tool", "1.0.0"),
    )
    _assign_package(client, owner, collection["id"], "acme/tool@1.0.0")

    with (
        patch(
            "agh.server.routes.collections._skill_names",
            side_effect=[
                ["comment-writer", "reviewer"],
                OSError("simulated TOCTOU read failure"),
            ],
        ) as mock_skill_names,
        patch("agh.server.routes.collections.LOGGER.warning") as mock_warning,
    ):
        response = client.get("/api/v1/skills", headers=_auth(owner))

    assert response.status_code == 200
    assert response.json()["skills"] == []
    mock_skill_names.assert_called()
    mock_warning.assert_called_once()
    args, _kwargs = mock_warning.call_args
    log_message = args[0]
    log_args = args[1:]
    assert "Suppressed active collection assignment" in log_message
    assert collection["id"] in log_args
    assert "simulated TOCTOU read failure" in str(log_args)


def test_skills_list_suppresses_corrupt_manifest_json(
    tmp_path: Path, monkeypatch
) -> None:
    from unittest.mock import patch

    client, owner = _client_with_owner(tmp_path, monkeypatch)
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/tool@1.0.0",
        _skill_only_package_files("acme", "tool", "1.0.0"),
    )
    _assign_package(client, owner, collection["id"], "acme/tool@1.0.0")

    connection = connect_database(get_database_path(tmp_path))
    try:
        row = connection.execute("SELECT id FROM package_versions").fetchone()
        connection.execute(
            "UPDATE package_versions SET manifest_json = ? WHERE id = ?",
            ("not-valid-json", row["id"]),
        )
        connection.commit()
    finally:
        connection.close()

    with patch("agh.server.routes.collections.LOGGER.warning") as mock_warning:
        response = client.get("/api/v1/skills", headers=_auth(owner))

    assert response.status_code == 200
    assert response.json()["skills"] == []
    mock_warning.assert_called_once()
    args, _kwargs = mock_warning.call_args
    log_message = args[0]
    log_args = args[1:]
    assert "Suppressed active collection assignment" in log_message
    assert collection["id"] in log_args
    assert (
        "not-valid-json" in str(log_args).lower()
        or "expecting value" in str(log_args).lower()
    )


def test_skills_resolve_returns_concrete_version_and_download_url(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    member = _create_user(client, owner, "dev@example.com", "member")[1]
    collection = _collection(client, owner)
    version = _publish_package(
        client,
        owner,
        "acme/tool@1.2.0",
        _skill_only_package_files("acme", "tool", "1.2.0"),
    )
    _assign_package(client, owner, collection["id"], "acme/tool@latest")

    response = client.get(
        "/api/v1/skills:resolve?package_ref=acme/tool@latest&skill_name=comment-writer",
        headers=_auth(member),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["package_version_id"].startswith("pkgv_")
    assert body["package_ref"] == version["id"]
    assert body["checksum"] == version["checksum"]
    assert body["artifact_path"] == "skills/comment-writer/SKILL.md"
    assert body["download_url"].endswith(
        "/api/v1/packages/acme/tool/versions/1.2.0/files/skills/comment-writer/SKILL.md"
    )


def test_patch_rejects_active_assignment_when_latest_resolves_to_instruction_package(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/tool@1.0.0",
        _skill_only_package_files("acme", "tool", "1.0.0"),
    )
    assignment = _assign_package(client, owner, collection["id"], "acme/tool@latest")
    assert assignment.status_code == status.HTTP_201_CREATED

    _publish_package(
        client,
        owner,
        "acme/tool@1.1.0",
        _instruction_package_files("acme", "tool", "1.1.0"),
    )

    patch_position = client.patch(
        f"/api/v1/collections/{collection['id']}/packages/{assignment.json()['id']}",
        json={"position": 9},
        headers=_auth(owner),
    )
    assert patch_position.status_code == status.HTTP_400_BAD_REQUEST
    assert "instructions" in patch_position.json()["detail"].lower()

    patch_active = client.patch(
        f"/api/v1/collections/{collection['id']}/packages/{assignment.json()['id']}",
        json={"active": True},
        headers=_auth(owner),
    )
    assert patch_active.status_code == status.HTTP_400_BAD_REQUEST
    assert "instructions" in patch_active.json()["detail"].lower()

    listed = client.get(
        f"/api/v1/collections/{collection['id']}/packages", headers=_auth(owner)
    )
    assert listed.status_code == status.HTTP_200_OK
    item = listed.json()["collection_packages"][0]
    assert item["position"] == 0
    assert item["active"] is True

    skills = client.get("/api/v1/skills", headers=_auth(owner))
    assert skills.status_code == status.HTTP_200_OK
    assert skills.json()["skills"] == []


def test_skills_resolve_accepts_concrete_ref_from_skills_list(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    member = _create_user(client, owner, "dev@example.com", "member")[1]
    collection = _collection(client, owner)
    version = _publish_package(
        client,
        owner,
        "acme/tool@1.2.0",
        _skill_only_package_files("acme", "tool", "1.2.0"),
    )
    _assign_package(client, owner, collection["id"], "acme/tool@latest")

    listed = client.get("/api/v1/skills", headers=_auth(member))
    assert listed.status_code == status.HTTP_200_OK
    concrete_ref = listed.json()["skills"][0]["resolved_ref"]
    assert concrete_ref == "acme/tool@1.2.0"

    response = client.get(
        f"/api/v1/skills:resolve?package_ref={concrete_ref}&skill_name=comment-writer",
        headers=_auth(member),
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["package_version_id"].startswith("pkgv_")
    assert body["package_ref"] == version["id"]
    assert body["checksum"] == version["checksum"]
    assert body["download_url"].endswith(
        "/api/v1/packages/acme/tool/versions/1.2.0/files/skills/comment-writer/SKILL.md"
    )


def test_skills_resolve_fails_closed_when_latest_becomes_instruction_bearing(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/tool@1.0.0",
        _skill_only_package_files("acme", "tool", "1.0.0"),
    )
    _assign_package(client, owner, collection["id"], "acme/tool@latest")

    _publish_package(
        client,
        owner,
        "acme/tool@1.1.0",
        _instruction_package_files("acme", "tool", "1.1.0"),
    )

    resolve = client.get(
        "/api/v1/skills:resolve?package_ref=acme/tool@latest&skill_name=comment-writer",
        headers=_auth(owner),
    )
    assert resolve.status_code == status.HTTP_400_BAD_REQUEST
    assert "instructions" in resolve.json()["detail"].lower()

    listed = client.get("/api/v1/skills", headers=_auth(owner))
    assert listed.status_code == 200
    assert listed.json()["skills"] == []


def test_skills_resolve_rejects_unassigned_inactive_or_missing_skill(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/tool@1.0.0",
        _skill_only_package_files("acme", "tool", "1.0.0"),
    )
    assignment = _assign_package(client, owner, collection["id"], "acme/tool@1.0.0")
    assert assignment.status_code == 201

    unassigned = client.get(
        "/api/v1/skills:resolve?package_ref=acme/tool@1.0.0&skill_name=missing",
        headers=_auth(owner),
    )
    assert unassigned.status_code == status.HTTP_404_NOT_FOUND

    client.delete(
        f"/api/v1/collections/{collection['id']}/packages/{assignment.json()['id']}",
        headers=_auth(owner),
    )
    inactive = client.get(
        "/api/v1/skills:resolve?package_ref=acme/tool@1.0.0&skill_name=comment-writer",
        headers=_auth(owner),
    )
    assert inactive.status_code == status.HTTP_404_NOT_FOUND

    client.delete(f"/api/v1/collections/{collection['id']}", headers=_auth(owner))
    collection_inactive = client.get(
        "/api/v1/skills:resolve?package_ref=acme/tool@1.0.0&skill_name=comment-writer",
        headers=_auth(owner),
    )
    assert collection_inactive.status_code == status.HTTP_404_NOT_FOUND


def test_skills_resolve_rejects_when_collection_is_inactive(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/tool@1.0.0",
        _skill_only_package_files("acme", "tool", "1.0.0"),
    )
    assignment = _assign_package(client, owner, collection["id"], "acme/tool@1.0.0")
    assert assignment.status_code == 201

    client.delete(f"/api/v1/collections/{collection['id']}", headers=_auth(owner))

    response = client.get(
        "/api/v1/skills:resolve?package_ref=acme/tool@1.0.0&skill_name=comment-writer",
        headers=_auth(owner),
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_skills_list_suppresses_unreadable_storage_path(
    tmp_path: Path, monkeypatch
) -> None:
    from unittest.mock import patch

    client, owner = _client_with_owner(tmp_path, monkeypatch)
    member = _create_user(client, owner, "dev@example.com", "member")[1]
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/bad@1.0.0",
        _skill_only_package_files("acme", "bad", "1.0.0"),
    )
    _assign_package(client, owner, collection["id"], "acme/bad@1.0.0")
    _publish_package(
        client,
        owner,
        "acme/good@1.0.0",
        _skill_only_package_files("acme", "good", "1.0.0"),
    )
    _assign_package(client, owner, collection["id"], "acme/good@1.0.0", position=1)

    bad_skills_dir = tmp_path / "packages" / "acme" / "bad" / "1.0.0" / "skills"
    original_mode = bad_skills_dir.stat().st_mode
    bad_skills_dir.chmod(0o000)
    try:
        with patch("agh.server.routes.collections.LOGGER.warning") as mock_warning:
            response = client.get("/api/v1/skills", headers=_auth(member))
    finally:
        bad_skills_dir.chmod(original_mode)

    assert response.status_code == status.HTTP_200_OK
    refs = {item["resolved_ref"] for item in response.json()["skills"]}
    assert refs == {"acme/good@1.0.0"}
    mock_warning.assert_called_once()
    args, _ = mock_warning.call_args
    assert "Suppressed active collection assignment" in args[0]
    assert collection["id"] in args[1:]


def test_skills_resolve_fails_closed_on_unreadable_storage_path(
    tmp_path: Path, monkeypatch
) -> None:
    from unittest.mock import patch

    client, owner = _client_with_owner(tmp_path, monkeypatch)
    member = _create_user(client, owner, "dev@example.com", "member")[1]
    collection = _collection(client, owner)
    _publish_package(
        client,
        owner,
        "acme/tool@1.0.0",
        _skill_only_package_files("acme", "tool", "1.0.0"),
    )
    _assign_package(client, owner, collection["id"], "acme/tool@1.0.0")

    skills_dir = tmp_path / "packages" / "acme" / "tool" / "1.0.0" / "skills"
    original_mode = skills_dir.stat().st_mode
    skills_dir.chmod(0o000)
    try:
        with patch("agh.server.routes.collections.LOGGER.warning") as mock_warning:
            response = client.get(
                "/api/v1/skills:resolve?package_ref=acme/tool@1.0.0&skill_name=comment-writer",
                headers=_auth(member),
            )
    finally:
        skills_dir.chmod(original_mode)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "skill not found"
    mock_warning.assert_called_once()


def test_collection_package_assignment_update_and_deactivation(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner = _client_with_owner(tmp_path, monkeypatch)
    member = _create_user(client, owner, "dev@example.com", "member")[1]
    collection = _collection(client, owner)
    _publish_package(
        client, owner, "acme/a@1.0.0", _skill_only_package_files("acme", "a", "1.0.0")
    )
    _publish_package(
        client, owner, "acme/a@1.2.0", _skill_only_package_files("acme", "a", "1.2.0")
    )
    _publish_package(
        client, owner, "acme/b@1.0.0", _instruction_package_files("acme", "b", "1.0.0")
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
        json={"package_ref": "acme/b@1.0.0"},
        headers=_auth(owner),
    )
    assert bad_update.status_code == status.HTTP_400_BAD_REQUEST

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
