"""Pack publish, listing, and file download route tests."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from agh.server.app import create_app
from agh.server.db import connect_database, get_database_path
from agh.server.routes.packs import MAX_PACK_FILE_BYTES, MAX_PACK_PUBLISH_BODY_BYTES


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


def _pack_files(
    *,
    version: str = "1.0.0",
    agents: str | None = "Use AGENTS.\n",
    claude: str | None = None,
    skill: bool = False,
) -> dict[str, str]:
    files = {
        "agh.pack.toml": (
            'domain = "acme"\n'
            'name = "onboarding"\n'
            f'version = "{version}"\n'
            'description = "Onboarding guidance"\n'
            'tags = ["team"]\n'
        )
    }
    if agents is not None:
        files["instructions/AGENTS.md"] = agents
    if claude is not None:
        files["instructions/CLAUDE.md"] = claude
    if skill:
        files["skills/lint/SKILL.md"] = "# Lint skill\n"
    return files


def _publish(client: TestClient, token: str, files: dict[str, str]):
    return client.post("/api/v1/packs", json={"files": files}, headers=_auth(token))


def test_owner_publishes_lists_and_downloads_pack_files(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    response = _publish(client, owner_token, _pack_files(skill=True))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] == "acme/onboarding@1.0.0"
    assert body["description"] == "Onboarding guidance"
    assert body["tags"] == ["team"]
    assert body["checksum"].startswith("sha256:")
    assert body["pack_id"].startswith("pack_")
    assert "version_id" not in body

    list_response = client.get("/api/v1/packs", headers=_auth(owner_token))
    assert list_response.status_code == 200
    assert list_response.json()["packs"] == [body]

    file_response = client.get(
        "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )
    assert file_response.status_code == 200
    assert file_response.text == "Use AGENTS.\n"
    skill_response = client.get(
        "/api/v1/packs/acme/onboarding/versions/1.0.0/files/skills/lint/SKILL.md",
        headers=_auth(owner_token),
    )
    assert skill_response.status_code == 200
    assert skill_response.text == "# Lint skill\n"

    connection = connect_database(get_database_path(tmp_path))
    try:
        row = connection.execute(
            "SELECT storage_path, manifest_json FROM pack_versions"
        ).fetchone()
        assert Path(row["storage_path"]).is_dir()
        assert '"description": "Onboarding guidance"' in row["manifest_json"]
    finally:
        connection.close()


def test_pack_publish_works_with_relative_data_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGH_DATA_DIR", ".agh-data-rel")
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    client = TestClient(create_app())
    owner_token = (
        (tmp_path / ".agh-data-rel" / "secrets" / "initial_owner_token")
        .read_text(encoding="utf-8")
        .strip()
    )

    response = _publish(client, owner_token, _pack_files())

    assert response.status_code == 201, response.text
    assert (
        tmp_path
        / ".agh-data-rel"
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "agh.pack.toml"
    ).is_file()


def test_pack_publish_rejects_oversized_payload_before_filesystem_writes(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    payload = _pack_files()
    payload["instructions/AGENTS.md"] = "x" * (MAX_PACK_FILE_BYTES + 1)

    response = _publish(client, owner_token, payload)

    assert response.status_code == 400
    assert not (tmp_path / "packs").exists()


def test_pack_publish_rejects_streamed_body_over_body_cap(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    oversized_chunk = b"x" * (MAX_PACK_PUBLISH_BODY_BYTES + 1)

    def chunks():
        yield oversized_chunk

    response = client.post(
        "/api/v1/packs",
        content=chunks(),
        headers={**_auth(owner_token), "Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert not (tmp_path / "packs").exists()


def test_pack_publish_validation_and_immutability(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    missing_manifest = _publish(
        client, owner_token, {"instructions/AGENTS.md": "Use AGENTS.\n"}
    )
    assert missing_manifest.status_code == 400
    assert "agh.pack.toml" in missing_manifest.text

    missing_description = _pack_files()
    missing_description["agh.pack.toml"] = (
        'domain = "acme"\nname = "onboarding"\nversion = "1.0.0"\n'
    )
    assert _publish(client, owner_token, missing_description).status_code == 400

    default_only = _pack_files(agents=None)
    default_only["instructions/default.md"] = "No fallback.\n"
    no_instruction = _publish(client, owner_token, default_only)
    assert no_instruction.status_code == 400
    assert "instruction source AGENTS.md or CLAUDE.md required" in no_instruction.text

    latest = _publish(client, owner_token, _pack_files(version="latest"))
    assert latest.status_code == 400

    oversized_body = _pack_files()
    oversized_body["instructions/AGENTS.md"] = "x" * (MAX_PACK_PUBLISH_BODY_BYTES + 1)
    oversized_response = _publish(client, owner_token, oversized_body)
    assert oversized_response.status_code == 413

    first = _publish(client, owner_token, _pack_files())
    assert first.status_code == 201, first.text
    duplicate = _publish(
        client,
        owner_token,
        _pack_files(agents="Attempt overwrite.\n"),
    )
    assert duplicate.status_code == 409
    stored = (
        tmp_path
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert stored == "Use AGENTS.\n"


def test_pack_skill_directory_requires_skill_md(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    files = _pack_files()
    files["skills/lint/README.md"] = "missing SKILL\n"

    response = _publish(client, owner_token, files)

    assert response.status_code == 400
    assert "skills/lint/SKILL.md" in response.text


def test_pack_routes_require_auth_and_publish_requires_admin(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    member_response = client.post(
        "/api/v1/users",
        json={"email": "dev@example.com", "role": "member"},
        headers=_auth(owner_token),
    )
    assert member_response.status_code == 201
    member_token = member_response.json()["token"]

    assert client.get("/api/v1/packs").status_code == 401
    assert (
        client.post("/api/v1/packs", json={"files": _pack_files()}).status_code == 401
    )
    forbidden = _publish(client, member_token, _pack_files())
    assert forbidden.status_code == 403

    assert _publish(client, owner_token, _pack_files()).status_code == 201
    list_as_member = client.get("/api/v1/packs", headers=_auth(member_token))
    assert list_as_member.status_code == 200
    download_as_member = client.get(
        "/api/v1/packs/acme/onboarding/versions/1.0.0/files/agh.pack.toml",
        headers=_auth(member_token),
    )
    assert download_as_member.status_code == 200


def test_pack_publish_rejects_path_traversal_and_symlinked_storage(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    traversal = _pack_files()
    traversal["../evil.txt"] = "outside"

    response = _publish(client, owner_token, traversal)

    assert response.status_code == 400
    assert not (tmp_path / "evil.txt").exists()

    outside = tmp_path / "outside"
    outside.mkdir()
    packs_root = tmp_path / "packs"
    shutil.rmtree(packs_root)
    packs_root.symlink_to(outside, target_is_directory=True)
    root_symlink_response = _publish(client, owner_token, _pack_files())
    assert root_symlink_response.status_code == 400
    assert not (outside / ".staging").exists()

    packs_root.unlink()
    packs_root.mkdir(exist_ok=True)
    (packs_root / "acme").symlink_to(outside, target_is_directory=True)
    symlink_response = _publish(client, owner_token, _pack_files())
    assert symlink_response.status_code == 400
    assert not (outside / "onboarding").exists()


def test_pack_file_download_rejects_traversal_and_symlinks(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _pack_files()).status_code == 201

    traversal = client.get(
        "/api/v1/packs/acme/onboarding/versions/1.0.0/files/%2e%2e/agh.pack.toml",
        headers=_auth(owner_token),
    )
    assert traversal.status_code == 404

    outside = tmp_path / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    symlink = tmp_path / "packs" / "acme" / "onboarding" / "1.0.0" / "leak.md"
    symlink.symlink_to(outside)
    leak = client.get(
        "/api/v1/packs/acme/onboarding/versions/1.0.0/files/leak.md",
        headers=_auth(owner_token),
    )
    assert leak.status_code == 404
