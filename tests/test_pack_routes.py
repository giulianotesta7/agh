"""Pack publish, listing, and file download route tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agh.server.app import create_app
from agh.server.db import connect_database, get_database_path
from agh.server.routes.packs import MAX_PACK_FILE_BYTES, MAX_PACK_PUBLISH_BODY_BYTES


def _client_with_owner(
    tmp_path: Path, monkeypatch, *, raise_server_exceptions: bool = True
) -> tuple[TestClient, str]:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    client = TestClient(create_app(), raise_server_exceptions=raise_server_exceptions)
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
    domain: str = "acme",
    name: str = "onboarding",
    version: str = "1.0.0",
    agents: str | None = "Use AGENTS.\n",
    claude: str | None = None,
    skill: bool = False,
) -> dict[str, str]:
    files = {
        "agh.pack.toml": (
            f'domain = "{domain}"\n'
            f'name = "{name}"\n'
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


def _stored_agents_file(tmp_path: Path) -> Path:
    return (
        tmp_path
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    )


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


def test_pack_version_resolver_accepts_id_canonical_and_name_version(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    published = _publish(client, owner_token, _pack_files()).json()

    by_canonical = client.get(
        "/api/v1/packs/versions:resolve?ref=acme/onboarding%401.0.0",
        headers=_auth(owner_token),
    )
    by_name_version = client.get(
        "/api/v1/packs/versions:resolve?ref=onboarding%401.0.0",
        headers=_auth(owner_token),
    )

    connection = connect_database(get_database_path(tmp_path))
    try:
        version_id = connection.execute("SELECT id FROM pack_versions").fetchone()["id"]
    finally:
        connection.close()
    by_id = client.get(
        f"/api/v1/packs/versions:resolve?ref={version_id}",
        headers=_auth(owner_token),
    )

    expected = {
        "id": version_id,
        "pack_ref": published["id"],
        "domain": "acme",
        "name": "onboarding",
        "version": "1.0.0",
    }
    assert by_canonical.status_code == 200, by_canonical.text
    assert by_canonical.json() == expected
    assert by_name_version.status_code == 200, by_name_version.text
    assert by_name_version.json() == expected
    assert by_id.status_code == 200, by_id.text
    assert by_id.json() == expected


def test_pack_version_resolver_requires_auth(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _pack_files()).status_code == 201

    response = client.get("/api/v1/packs/versions:resolve?ref=acme/onboarding%401.0.0")

    assert response.status_code == 401


def test_pack_version_resolver_reports_invalid_missing_and_ambiguous_refs(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _pack_files()).status_code == 201
    assert (
        _publish(
            client,
            owner_token,
            _pack_files(domain="other", name="onboarding", version="1.0.0"),
        ).status_code
        == 201
    )

    invalid = client.get(
        "/api/v1/packs/versions:resolve?ref=not-a-ref", headers=_auth(owner_token)
    )
    missing = client.get(
        "/api/v1/packs/versions:resolve?ref=acme/missing%401.0.0",
        headers=_auth(owner_token),
    )
    ambiguous = client.get(
        "/api/v1/packs/versions:resolve?ref=onboarding%401.0.0",
        headers=_auth(owner_token),
    )

    assert invalid.status_code == 400
    assert missing.status_code == 404
    assert ambiguous.status_code == 409
    assert "ambiguous" in ambiguous.json()["detail"]


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


def test_pack_publish_ignores_request_time_data_dir_drift(
    tmp_path: Path, monkeypatch
) -> None:
    startup_root = tmp_path / "startup"
    drift_root = tmp_path / "drift"
    client, owner_token = _client_with_owner(startup_root, monkeypatch)
    monkeypatch.setenv("AGH_DATA_DIR", str(drift_root))

    response = _publish(client, owner_token, _pack_files())

    assert response.status_code == 201, response.text
    startup_pack = startup_root / "packs" / "acme" / "onboarding" / "1.0.0"
    assert (startup_pack / "agh.pack.toml").is_file()
    assert not (drift_root / "packs").exists()
    connection = connect_database(get_database_path(startup_root))
    try:
        row = connection.execute("SELECT storage_path FROM pack_versions").fetchone()
        assert Path(row["storage_path"]) == startup_pack
    finally:
        connection.close()


def test_pack_publish_cleans_proven_orphan_final_directory(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    orphan = tmp_path / "packs" / "acme" / "onboarding" / "1.0.0"
    orphan.mkdir(parents=True)
    (orphan / "stale.txt").write_text("leftover", encoding="utf-8")

    response = _publish(client, owner_token, _pack_files(agents="Recovered.\n"))

    assert response.status_code == 201, response.text
    assert not (orphan / "stale.txt").exists()
    assert (orphan / "instructions" / "AGENTS.md").read_text(
        encoding="utf-8"
    ) == "Recovered.\n"


def test_pack_publish_cleans_partial_final_directory_after_copy_failure(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(
        tmp_path, monkeypatch, raise_server_exceptions=False
    )
    target = tmp_path / "packs" / "acme" / "onboarding" / "1.0.0"

    def fail_after_partial_copy(
        src: Path, dst: Path, *, symlinks: bool = False
    ) -> None:
        dst.mkdir(parents=True)
        (dst / "partial.txt").write_text("partial", encoding="utf-8")
        raise OSError("simulated copy failure")

    monkeypatch.setattr(shutil, "copytree", fail_after_partial_copy)

    response = _publish(client, owner_token, _pack_files())

    assert response.status_code == 500
    assert not target.exists()
    connection = connect_database(get_database_path(tmp_path))
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM pack_versions").fetchone()[0] == 0
        )
    finally:
        connection.close()


def test_pack_publish_preserves_db_referenced_final_directory(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    target = tmp_path / "packs" / "acme" / "onboarding" / "1.0.0"
    target.mkdir(parents=True)
    sentinel = target / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    connection = connect_database(get_database_path(tmp_path))
    try:
        owner_id = connection.execute(
            "SELECT id FROM users WHERE email = ?", ("owner@example.com",)
        ).fetchone()["id"]
        connection.execute(
            "INSERT INTO packs (id, domain, name, created_by) VALUES (?, ?, ?, ?)",
            ("pack_other", "other", "baseline", owner_id),
        )
        connection.execute(
            """
            INSERT INTO pack_versions
                (id, pack_id, version, manifest_json, storage_path, checksum)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "packv_other",
                "pack_other",
                "9.9.9",
                '{"description": "Other"}',
                str(target),
                "sha256:other",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    response = _publish(client, owner_token, _pack_files())

    assert response.status_code == 400
    assert response.json() == {"detail": "pack storage path already exists"}
    assert sentinel.read_text(encoding="utf-8") == "keep"


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
    assert response.json() == {"detail": "pack publish payload is too large"}
    assert not (tmp_path / "packs").exists()


@pytest.mark.parametrize("content_length", ["abc", "1.2", "-1", "+1", ""])
def test_pack_publish_rejects_invalid_content_length_with_json_400(
    tmp_path: Path, monkeypatch, content_length: str
) -> None:
    client, owner_token = _client_with_owner(
        tmp_path, monkeypatch, raise_server_exceptions=False
    )

    response = client.post(
        "/api/v1/packs",
        content=b"{}",
        headers={
            **_auth(owner_token),
            "Content-Type": "application/json",
            "Content-Length": content_length,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid content-length header"}


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
    empty_pack = _publish(client, owner_token, default_only)
    assert empty_pack.status_code == 400
    assert "pack must include at least one instruction file or skill" in empty_pack.text

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


def test_owner_publishes_skill_only_pack(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    response = _publish(client, owner_token, _pack_files(agents=None, skill=True))

    assert response.status_code == 201, response.text
    stored_skill = (
        tmp_path
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "skills"
        / "lint"
        / "SKILL.md"
    )
    assert stored_skill.read_text(encoding="utf-8") == "# Lint skill\n"
    assert not (
        tmp_path
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    ).exists()


def test_pack_skill_directory_requires_skill_md(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    files = _pack_files(agents=None)
    files["skills/lint/README.md"] = "missing SKILL\n"

    response = _publish(client, owner_token, files)

    assert response.status_code == 400
    assert "unexpected pack file path: skills/lint/README.md" in response.text


def test_pack_publish_rejects_unexpected_server_payload_paths(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    extra_root = _pack_files(skill=True)
    extra_root["extra.txt"] = "unexpected\n"
    root_response = _publish(client, owner_token, extra_root)
    assert root_response.status_code == 400
    assert "unexpected pack file path: extra.txt" in root_response.text

    extra_instruction = _pack_files(agents=None, skill=True)
    extra_instruction["instructions/EXTRA.md"] = "unexpected\n"
    instruction_response = _publish(client, owner_token, extra_instruction)
    assert instruction_response.status_code == 400
    assert (
        "unexpected pack file path: instructions/EXTRA.md" in instruction_response.text
    )

    skills_file = _pack_files(agents=None)
    skills_file["skills"] = "not a directory\n"
    skills_response = _publish(client, owner_token, skills_file)
    assert skills_response.status_code == 400
    assert "skills must be a directory" in skills_response.text


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
    assert traversal.json() == {"detail": "pack file not found"}

    outside = tmp_path / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    symlink = tmp_path / "packs" / "acme" / "onboarding" / "1.0.0" / "leak.md"
    symlink.symlink_to(outside)
    leak = client.get(
        "/api/v1/packs/acme/onboarding/versions/1.0.0/files/leak.md",
        headers=_auth(owner_token),
    )
    assert leak.status_code == 404
    assert leak.json() == {"detail": "pack file not found"}


def test_pack_file_download_missing_artifact_returns_json_404(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _pack_files()).status_code == 201
    stored_file = _stored_agents_file(tmp_path)
    stored_file.unlink()

    response = client.get(
        "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "pack file not found"}


def test_pack_file_download_unreadable_artifact_returns_json_503(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _pack_files()).status_code == 201
    stored_file = _stored_agents_file(tmp_path)
    stored_file.write_bytes(b"\xff\xfe\x00")

    response = client.get(
        "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "pack artifact storage unavailable"}


def test_pack_file_download_read_error_returns_json_503(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _pack_files()).status_code == 201
    stored_file = _stored_agents_file(tmp_path)
    original_read_text = Path.read_text

    def fail_candidate_read_text(
        self: Path,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        if self == stored_file and encoding == "utf-8":
            raise OSError("simulated read failure")
        return original_read_text(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", fail_candidate_read_text)

    response = client.get(
        "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "pack artifact storage unavailable"}


def test_pack_file_download_path_resolution_error_returns_json_503(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _pack_files()).status_code == 201
    stored_file = _stored_agents_file(tmp_path)
    original_resolve = Path.resolve

    def fail_candidate_resolve(self: Path, strict: bool = False) -> Path:
        if self == stored_file and strict:
            raise OSError("simulated path resolution failure")
        return original_resolve(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_candidate_resolve)

    response = client.get(
        "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "pack artifact storage unavailable"}
