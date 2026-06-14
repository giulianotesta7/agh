"""Project pull-manifest route tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agh.common.checksums import managed_payload_checksum
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
    client: TestClient, token: str, email: str, role: str = "member"
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


def _pack_files(
    domain: str,
    name: str,
    version: str,
    *,
    agents: str | None = None,
    claude: str | None = None,
    skill: str | None = None,
) -> dict[str, str]:
    files = {
        "agh.pack.toml": (
            f'domain = "{domain}"\n'
            f'name = "{name}"\n'
            f'version = "{version}"\n'
            f'description = "{domain}/{name} {version}"\n'
            'tags = ["team"]\n'
        )
    }
    if agents is not None:
        files["instructions/AGENTS.md"] = agents
    if claude is not None:
        files["instructions/CLAUDE.md"] = claude
    if skill is not None:
        files["skills/lint/SKILL.md"] = skill
    return files


def _publish_pack(
    client: TestClient,
    token: str,
    ref: str,
    *,
    agents: str | None = None,
    claude: str | None = None,
    skill: str | None = None,
) -> dict[str, Any]:
    pair, version = ref.split("@", 1)
    domain, name = pair.split("/", 1)
    response = client.post(
        "/api/v1/packs",
        json={
            "files": _pack_files(
                domain, name, version, agents=agents, claude=claude, skill=skill
            )
        },
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _assign_pack(
    client: TestClient,
    token: str,
    project_id: str,
    pack_ref: str,
    *,
    position: int = 0,
):
    response = client.post(
        f"/api/v1/projects/{project_id}/packs",
        json={"pack_ref": pack_ref, "position": position},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _publish_and_assign(
    tmp_path: Path, monkeypatch, ref: str, **files: str | None
) -> tuple[TestClient, str, dict[str, Any]]:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    project = _create_project(client, owner_token)
    _publish_pack(client, owner_token, ref, **files)
    _assign_pack(client, owner_token, project["id"], ref)
    return client, owner_token, project


def _pull_manifest(client: TestClient, token: str, project: dict[str, Any]) -> Any:
    return client.get(
        f"/api/v1/projects/{project['id']}/pull-manifest",
        headers=_auth(token),
    )


def _assert_skill_artifacts(artifacts: list[dict[str, Any]], content: str) -> None:
    assert {artifact["target_path"] for artifact in artifacts} == {
        ".opencode/skills/lint/SKILL.md",
        ".claude/skills/lint/SKILL.md",
    }
    assert all(
        artifact["checksum"] == managed_payload_checksum(content)
        for artifact in artifacts
    )


def _store_manifest_artifact_paths(tmp_path: Path, artifact_paths: Any) -> None:
    connection = connect_database(get_database_path(tmp_path))
    try:
        row = connection.execute(
            "SELECT id, manifest_json FROM pack_versions"
        ).fetchone()
        manifest = json.loads(row["manifest_json"])
        manifest["artifact_paths"] = artifact_paths
        connection.execute(
            "UPDATE pack_versions SET manifest_json = ? WHERE id = ?",
            (json.dumps(manifest, sort_keys=True), row["id"]),
        )
        connection.commit()
    finally:
        connection.close()


def _stored_pack_path(tmp_path: Path, ref: str, relative_path: str) -> Path:
    pair, version = ref.split("@", 1)
    domain, name = pair.split("/", 1)
    return tmp_path / "packs" / domain / name / version / relative_path


def test_pull_manifest_resolves_latest_orders_assignments_and_builds_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    project = _create_project(client, owner_token)
    baseline_agents = "# Baseline\r\nUse baseline.\r\n"
    onboarding_agents = "# Onboarding\nUse onboarding.\n"
    onboarding_claude = "# Claude\nUse Claude.\n"
    skill_content = "# Lint\nRun lint.\n"
    _publish_pack(
        client,
        owner_token,
        "acme/onboarding@1.0.0",
        agents="# Old\n",
    )
    _publish_pack(
        client,
        owner_token,
        "acme/onboarding@1.2.0",
        agents=onboarding_agents,
        claude=onboarding_claude,
        skill=skill_content,
    )
    _publish_pack(
        client,
        owner_token,
        "acme/baseline@1.0.0",
        agents=baseline_agents,
    )
    _assign_pack(
        client, owner_token, project["id"], "acme/onboarding@latest", position=20
    )
    _assign_pack(client, owner_token, project["id"], "acme/baseline@1.0.0", position=20)

    response = client.get(
        f"/api/v1/projects/{project['id']}/pull-manifest", headers=_auth(owner_token)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["project"] == {
        "id": project["id"],
        "name": "App",
        "repo_url_normalized": "github.com/org/app",
    }
    assert [pack["id"] for pack in body["packs"]] == [
        "acme/baseline@1.0.0",
        "acme/onboarding@1.2.0",
    ]
    assert [pack["position"] for pack in body["packs"]] == [20, 20]
    baseline, onboarding = body["packs"]
    assert baseline["manifest"]["description"] == "acme/baseline 1.0.0"
    assert onboarding["assignment_id"].startswith("asn_")
    assert onboarding["manifest"]["version"] == "1.2.0"
    artifact_by_target = {
        (artifact["target_agent"], artifact["target_path"]): artifact
        for artifact in onboarding["artifacts"]
    }
    agents_artifact = artifact_by_target[("opencode", "AGENTS.md")]
    claude_artifact = artifact_by_target[("claude", "CLAUDE.md")]
    opencode_skill = artifact_by_target[("opencode", ".opencode/skills/lint/SKILL.md")]
    claude_skill = artifact_by_target[("claude", ".claude/skills/lint/SKILL.md")]
    assert agents_artifact["kind"] == "instruction"
    assert agents_artifact["path"] == "instructions/AGENTS.md"
    assert agents_artifact["checksum"] == managed_payload_checksum(onboarding_agents)
    assert agents_artifact["download_url"].endswith(
        "/api/v1/packs/acme/onboarding/versions/1.2.0/files/instructions/AGENTS.md"
    )
    assert claude_artifact["checksum"] == managed_payload_checksum(onboarding_claude)
    assert opencode_skill["kind"] == "skill"
    assert opencode_skill["checksum"] == managed_payload_checksum(skill_content)
    assert claude_skill["download_url"] == opencode_skill["download_url"]
    baseline_artifact = baseline["artifacts"][0]
    assert baseline_artifact["checksum"] == managed_payload_checksum(baseline_agents)


def test_pull_manifest_includes_skill_only_pack_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    project = _create_project(client, owner_token)
    skill_content = "# Lint\nUse lint skill.\n"
    _publish_pack(client, owner_token, "acme/skills@1.0.0", skill=skill_content)
    _assign_pack(client, owner_token, project["id"], "acme/skills@1.0.0")

    response = client.get(
        f"/api/v1/projects/{project['id']}/pull-manifest", headers=_auth(owner_token)
    )

    assert response.status_code == 200, response.text
    artifacts = response.json()["packs"][0]["artifacts"]
    assert {artifact["kind"] for artifact in artifacts} == {"skill"}
    assert {artifact["target_path"] for artifact in artifacts} == {
        ".opencode/skills/lint/SKILL.md",
        ".claude/skills/lint/SKILL.md",
    }
    assert all(artifact["path"] == "skills/lint/SKILL.md" for artifact in artifacts)
    assert all(
        artifact["checksum"] == managed_payload_checksum(skill_content)
        for artifact in artifacts
    )


def test_pull_manifest_legacy_missing_discovered_skill_file_is_skipped(
    tmp_path: Path, monkeypatch
) -> None:
    agents = "# Guide\n"
    client, owner_token, project = _publish_and_assign(
        tmp_path,
        monkeypatch,
        "acme/legacy@1.0.0",
        agents=agents,
        skill="# Lint\n",
    )
    stored_skill = _stored_pack_path(
        tmp_path, "acme/legacy@1.0.0", "skills/lint/SKILL.md"
    )
    stored_skill.unlink()

    response = _pull_manifest(client, owner_token, project)

    assert response.status_code == 200, response.text
    artifacts = response.json()["packs"][0]["artifacts"]
    assert [artifact["path"] for artifact in artifacts] == ["instructions/AGENTS.md"]
    assert artifacts[0]["checksum"] == managed_payload_checksum(agents)


@pytest.mark.parametrize("artifact_paths", ["skills/lint/SKILL.md", ["not/a/thing"]])
def test_pull_manifest_malformed_artifact_paths_uses_legacy_discovery(
    tmp_path: Path, monkeypatch, artifact_paths: Any
) -> None:
    skill_content = "# Lint\nUse lint skill.\n"
    client, owner_token, project = _publish_and_assign(
        tmp_path, monkeypatch, "acme/legacy@1.0.0", skill=skill_content
    )
    _store_manifest_artifact_paths(tmp_path, artifact_paths)

    response = _pull_manifest(client, owner_token, project)

    assert response.status_code == 200, response.text
    _assert_skill_artifacts(response.json()["packs"][0]["artifacts"], skill_content)


@pytest.mark.parametrize(
    ("ref", "files", "artifact_paths", "missing_path", "remove_tree"),
    [
        (
            "acme/guide@1.0.0",
            {"agents": "# Guide\n"},
            ["instructions/AGENTS.md"],
            "instructions/AGENTS.md",
            False,
        ),
        (
            "acme/mixed@1.0.0",
            {"agents": "# Guide\n", "skill": "# Lint\n"},
            ["instructions/AGENTS.md", "skills/lint/SKILL.md"],
            "skills",
            True,
        ),
    ],
)
def test_pull_manifest_expected_missing_storage_returns_json_404(
    tmp_path: Path,
    monkeypatch,
    ref: str,
    files: dict[str, str],
    artifact_paths: list[str],
    missing_path: str,
    remove_tree: bool,
) -> None:
    client, owner_token, project = _publish_and_assign(
        tmp_path, monkeypatch, ref, **files
    )
    _store_manifest_artifact_paths(tmp_path, artifact_paths)
    stored_path = _stored_pack_path(tmp_path, ref, missing_path)
    shutil.rmtree(stored_path) if remove_tree else stored_path.unlink()

    response = _pull_manifest(client, owner_token, project)

    assert response.status_code == 404
    assert response.json() == {"detail": "pack file not found"}


def test_pull_manifest_expected_symlink_artifact_returns_json_404(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token, project = _publish_and_assign(
        tmp_path, monkeypatch, "acme/skills@1.0.0", skill="# Lint\n"
    )
    _store_manifest_artifact_paths(tmp_path, ["skills/lint/SKILL.md"])
    stored_skill = _stored_pack_path(
        tmp_path, "acme/skills@1.0.0", "skills/lint/SKILL.md"
    )
    stored_skill.unlink()
    stored_skill.symlink_to(
        _stored_pack_path(tmp_path, "acme/skills@1.0.0", "agh.pack.toml")
    )

    response = _pull_manifest(client, owner_token, project)

    assert response.status_code == 404
    assert response.json() == {"detail": "pack file not found"}


def test_pull_manifest_unreadable_expected_artifact_returns_json_503(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token, project = _publish_and_assign(
        tmp_path, monkeypatch, "acme/skills@1.0.0", skill="# Lint\n"
    )
    _store_manifest_artifact_paths(tmp_path, ["skills/lint/SKILL.md"])
    stored_skill = _stored_pack_path(
        tmp_path, "acme/skills@1.0.0", "skills/lint/SKILL.md"
    )
    stored_skill.write_bytes(b"\xff\xfe\x00")

    response = _pull_manifest(client, owner_token, project)

    assert response.status_code == 503
    assert response.json() == {"detail": "pack artifact storage unavailable"}


def test_pull_manifest_developer_access_and_non_member_denial(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    developer, developer_token = _create_user(client, owner_token, "dev@example.com")
    _other, other_token = _create_user(client, owner_token, "other@example.com")
    project = _create_project(client, owner_token)
    _publish_pack(client, owner_token, "acme/onboarding@1.0.0", agents="# Guide\n")
    _assign_pack(client, owner_token, project["id"], "acme/onboarding@1.0.0")

    non_member = client.get(
        f"/api/v1/projects/{project['id']}/pull-manifest", headers=_auth(other_token)
    )
    assert non_member.status_code == 404

    added = client.put(
        f"/api/v1/projects/{project['id']}/members/{developer['id']}",
        headers=_auth(owner_token),
    )
    assert added.status_code == 200
    developer_response = client.get(
        f"/api/v1/projects/{project['id']}/pull-manifest",
        headers=_auth(developer_token),
    )
    assert developer_response.status_code == 200
    assert developer_response.json()["packs"][0]["id"] == "acme/onboarding@1.0.0"


def test_pull_manifest_rejects_inactive_project_and_omits_inactive_assignments(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    project = _create_project(client, owner_token)
    _publish_pack(client, owner_token, "acme/active@1.0.0", agents="# Active\n")
    _publish_pack(client, owner_token, "acme/inactive@1.0.0", agents="# Inactive\n")
    active = _assign_pack(client, owner_token, project["id"], "acme/active@1.0.0")
    inactive = _assign_pack(client, owner_token, project["id"], "acme/inactive@1.0.0")
    removed = client.delete(
        f"/api/v1/projects/{project['id']}/packs/{inactive['id']}",
        headers=_auth(owner_token),
    )
    assert removed.status_code == 200

    response = client.get(
        f"/api/v1/projects/{project['id']}/pull-manifest", headers=_auth(owner_token)
    )
    assert response.status_code == 200
    assert [pack["assignment_id"] for pack in response.json()["packs"]] == [
        active["id"]
    ]

    deactivated = client.delete(
        f"/api/v1/projects/{project['id']}", headers=_auth(owner_token)
    )
    assert deactivated.status_code == 200
    inactive_project = client.get(
        f"/api/v1/projects/{project['id']}/pull-manifest", headers=_auth(owner_token)
    )
    assert inactive_project.status_code == 404
