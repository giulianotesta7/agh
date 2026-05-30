"""Project pull-manifest route tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from agh.common.checksums import managed_payload_checksum
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
