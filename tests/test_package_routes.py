"""Package publish, listing, and file download route tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agh.server.app import create_app
from agh.server.db import connect_database, get_database_path
from agh.common.package_limits import (
    MAX_PACKAGE_FILE_BYTES,
    MAX_PACKAGE_PUBLISH_BODY_BYTES,
    MAX_PACKAGE_TOTAL_BYTES,
)


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


def _create_user(
    client: TestClient, token: str, email: str, role: str
) -> tuple[dict[str, Any], str]:
    response = client.post(
        "/api/v1/users", json={"email": email, "role": role}, headers=_auth(token)
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["user"], body["token"]


def _package_files(
    *,
    domain: str = "acme",
    name: str = "onboarding",
    version: str = "1.0.0",
    agents: str | None = "Use AGENTS.\n",
    claude: str | None = None,
    skill: bool = False,
) -> dict[str, str]:
    files = {
        "agh.package.toml": (
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
    return client.post("/api/v1/packages", json={"files": files}, headers=_auth(token))


def _publish_json_body(files: dict[str, str]) -> bytes:
    return json.dumps({"files": files}, separators=(",", ":")).encode("utf-8")


def _max_content_package_files_with_escaped_content() -> dict[str, str]:
    manifest = _package_files(agents=None)["agh.package.toml"]
    files = {"agh.package.toml": manifest}
    remaining_bytes = MAX_PACKAGE_TOTAL_BYTES - len(manifest.encode("utf-8"))
    payload_paths = [
        "instructions/AGENTS.md",
        "instructions/CLAUDE.md",
        "skills/skill-a/SKILL.md",
        "skills/skill-b/SKILL.md",
    ]

    for path in payload_paths:
        chunk_bytes = min(MAX_PACKAGE_FILE_BYTES, remaining_bytes)
        files[path] = "\u001f" * chunk_bytes
        remaining_bytes -= chunk_bytes

    assert remaining_bytes == 0
    assert sum(len(content.encode("utf-8")) for content in files.values()) == (
        MAX_PACKAGE_TOTAL_BYTES
    )
    return files


def _stored_agents_file(tmp_path: Path) -> Path:
    return (
        tmp_path
        / "packages"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    )


def test_owner_publishes_lists_and_downloads_package_files(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    response = _publish(client, owner_token, _package_files(skill=True))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] == "acme/onboarding@1.0.0"
    assert body["description"] == "Onboarding guidance"
    assert body["tags"] == ["team"]
    assert body["checksum"].startswith("sha256:")
    assert body["package_id"].startswith("pkg_")
    assert "version_id" not in body

    list_response = client.get("/api/v1/packages", headers=_auth(owner_token))
    assert list_response.status_code == 200
    assert list_response.json()["packages"] == [body]

    file_response = client.get(
        "/api/v1/packages/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )
    assert file_response.status_code == 200
    assert file_response.text == "Use AGENTS.\n"
    skill_response = client.get(
        "/api/v1/packages/acme/onboarding/versions/1.0.0/files/skills/lint/SKILL.md",
        headers=_auth(owner_token),
    )
    assert skill_response.status_code == 200
    assert skill_response.text == "# Lint skill\n"

    connection = connect_database(get_database_path(tmp_path))
    try:
        row = connection.execute(
            "SELECT storage_path, manifest_json FROM package_versions"
        ).fetchone()
        assert Path(row["storage_path"]).is_dir()
        assert '"description": "Onboarding guidance"' in row["manifest_json"]
    finally:
        connection.close()


def test_authenticated_member_without_project_membership_can_list_and_download_packages(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    _, member_token = _create_user(
        client, owner_token, "developer@example.com", "member"
    )
    published = _publish(client, owner_token, _package_files(skill=True)).json()

    list_response = client.get("/api/v1/packages", headers=_auth(member_token))
    file_response = client.get(
        "/api/v1/packages/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(member_token),
    )

    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["packages"] == [published]
    assert file_response.status_code == 200, file_response.text
    assert file_response.text == "Use AGENTS.\n"


def test_package_version_resolver_accepts_id_canonical_and_name_version(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    published = _publish(client, owner_token, _package_files()).json()

    by_canonical = client.get(
        "/api/v1/packages/versions:resolve?ref=acme/onboarding%401.0.0",
        headers=_auth(owner_token),
    )
    by_name_version = client.get(
        "/api/v1/packages/versions:resolve?ref=onboarding%401.0.0",
        headers=_auth(owner_token),
    )

    connection = connect_database(get_database_path(tmp_path))
    try:
        version_id = connection.execute("SELECT id FROM package_versions").fetchone()[
            "id"
        ]
    finally:
        connection.close()
    by_id = client.get(
        f"/api/v1/packages/versions:resolve?ref={version_id}",
        headers=_auth(owner_token),
    )

    expected = {
        "id": version_id,
        "package_ref": published["id"],
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


def test_package_version_resolver_requires_auth(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _package_files()).status_code == 201

    response = client.get(
        "/api/v1/packages/versions:resolve?ref=acme/onboarding%401.0.0"
    )

    assert response.status_code == 401


def test_package_version_resolver_reports_invalid_missing_and_ambiguous_refs(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _package_files()).status_code == 201
    assert (
        _publish(
            client,
            owner_token,
            _package_files(domain="other", name="onboarding", version="1.0.0"),
        ).status_code
        == 201
    )

    invalid = client.get(
        "/api/v1/packages/versions:resolve?ref=not-a-ref", headers=_auth(owner_token)
    )
    missing = client.get(
        "/api/v1/packages/versions:resolve?ref=acme/missing%401.0.0",
        headers=_auth(owner_token),
    )
    ambiguous = client.get(
        "/api/v1/packages/versions:resolve?ref=onboarding%401.0.0",
        headers=_auth(owner_token),
    )

    assert invalid.status_code == 400
    assert missing.status_code == 404
    assert ambiguous.status_code == 409
    assert "ambiguous" in ambiguous.json()["detail"]


def test_package_publish_works_with_relative_data_dir(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGH_DATA_DIR", ".agh-data-rel")
    monkeypatch.setenv("AGH_BOOTSTRAP_OWNER_EMAIL", "owner@example.com")
    client = TestClient(create_app())
    owner_token = (
        (tmp_path / ".agh-data-rel" / "secrets" / "initial_owner_token")
        .read_text(encoding="utf-8")
        .strip()
    )

    response = _publish(client, owner_token, _package_files())

    assert response.status_code == 201, response.text
    assert (
        tmp_path
        / ".agh-data-rel"
        / "packages"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "agh.package.toml"
    ).is_file()


def test_package_publish_ignores_request_time_data_dir_drift(
    tmp_path: Path, monkeypatch
) -> None:
    startup_root = tmp_path / "startup"
    drift_root = tmp_path / "drift"
    client, owner_token = _client_with_owner(startup_root, monkeypatch)
    monkeypatch.setenv("AGH_DATA_DIR", str(drift_root))

    response = _publish(client, owner_token, _package_files())

    assert response.status_code == 201, response.text
    startup_pack = startup_root / "packages" / "acme" / "onboarding" / "1.0.0"
    assert (startup_pack / "agh.package.toml").is_file()
    assert not (drift_root / "packages").exists()
    connection = connect_database(get_database_path(startup_root))
    try:
        row = connection.execute("SELECT storage_path FROM package_versions").fetchone()
        assert Path(row["storage_path"]) == startup_pack
    finally:
        connection.close()


def test_package_publish_cleans_proven_orphan_final_directory(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    orphan = tmp_path / "packages" / "acme" / "onboarding" / "1.0.0"
    orphan.mkdir(parents=True)
    (orphan / "stale.txt").write_text("leftover", encoding="utf-8")

    response = _publish(client, owner_token, _package_files(agents="Recovered.\n"))

    assert response.status_code == 201, response.text
    assert not (orphan / "stale.txt").exists()
    assert (orphan / "instructions" / "AGENTS.md").read_text(
        encoding="utf-8"
    ) == "Recovered.\n"


def test_package_publish_cleans_partial_final_directory_after_copy_failure(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(
        tmp_path, monkeypatch, raise_server_exceptions=False
    )
    target = tmp_path / "packages" / "acme" / "onboarding" / "1.0.0"

    def fail_after_partial_copy(
        src: Path, dst: Path, *, symlinks: bool = False
    ) -> None:
        dst.mkdir(parents=True)
        (dst / "partial.txt").write_text("partial", encoding="utf-8")
        raise OSError("simulated copy failure")

    monkeypatch.setattr(shutil, "copytree", fail_after_partial_copy)

    response = _publish(client, owner_token, _package_files())

    assert response.status_code == 500
    assert not target.exists()
    connection = connect_database(get_database_path(tmp_path))
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM package_versions").fetchone()[0]
            == 0
        )
    finally:
        connection.close()


def test_package_publish_preserves_db_referenced_final_directory(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    target = tmp_path / "packages" / "acme" / "onboarding" / "1.0.0"
    target.mkdir(parents=True)
    sentinel = target / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    connection = connect_database(get_database_path(tmp_path))
    try:
        owner_id = connection.execute(
            "SELECT id FROM users WHERE email = ?", ("owner@example.com",)
        ).fetchone()["id"]
        connection.execute(
            "INSERT INTO packages (id, domain, name, created_by) VALUES (?, ?, ?, ?)",
            ("pkg_other", "other", "baseline", owner_id),
        )
        connection.execute(
            """
            INSERT INTO package_versions
                (id, package_id, version, manifest_json, storage_path, checksum)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "pkgv_other",
                "pkg_other",
                "9.9.9",
                '{"description": "Other"}',
                str(target),
                "sha256:other",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    response = _publish(client, owner_token, _package_files())

    assert response.status_code == 400
    assert response.json() == {"detail": "package storage path already exists"}
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_package_publish_rejects_oversized_payload_before_filesystem_writes(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    payload = _package_files()
    payload["instructions/AGENTS.md"] = "x" * (MAX_PACKAGE_FILE_BYTES + 1)

    response = _publish(client, owner_token, payload)

    assert response.status_code == 400
    assert not (tmp_path / "packages").exists()


def test_package_publish_rejects_streamed_body_over_body_cap(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    oversized_chunk = b"x" * (MAX_PACKAGE_PUBLISH_BODY_BYTES + 1)

    def chunks():
        yield oversized_chunk

    response = client.post(
        "/api/v1/packages",
        content=chunks(),
        headers={**_auth(owner_token), "Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "package publish payload is too large"}
    assert not (tmp_path / "packages").exists()


def test_package_publish_body_cap_allows_max_content_with_json_escaping(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    files = _max_content_package_files_with_escaped_content()
    body = _publish_json_body(files)

    assert len(body) > MAX_PACKAGE_TOTAL_BYTES * 2

    response = client.post(
        "/api/v1/packages",
        content=body,
        headers={**_auth(owner_token), "Content-Type": "application/json"},
    )

    assert response.status_code == 201, response.text
    assert _stored_agents_file(tmp_path).read_text(encoding="utf-8") == (
        "\u001f" * MAX_PACKAGE_FILE_BYTES
    )


@pytest.mark.parametrize("content_length", ["abc", "1.2", "-1", "+1", ""])
def test_package_publish_rejects_invalid_content_length_with_json_400(
    tmp_path: Path, monkeypatch, content_length: str
) -> None:
    client, owner_token = _client_with_owner(
        tmp_path, monkeypatch, raise_server_exceptions=False
    )

    response = client.post(
        "/api/v1/packages",
        content=b"{}",
        headers={
            **_auth(owner_token),
            "Content-Type": "application/json",
            "Content-Length": content_length,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid content-length header"}


def test_package_publish_validation_and_immutability(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    missing_manifest = _publish(
        client, owner_token, {"instructions/AGENTS.md": "Use AGENTS.\n"}
    )
    assert missing_manifest.status_code == 400
    assert "agh.package.toml" in missing_manifest.text

    missing_description = _package_files()
    missing_description["agh.package.toml"] = (
        'domain = "acme"\nname = "onboarding"\nversion = "1.0.0"\n'
    )
    assert _publish(client, owner_token, missing_description).status_code == 400

    default_only = _package_files(agents=None)
    empty_pack = _publish(client, owner_token, default_only)
    assert empty_pack.status_code == 400
    assert (
        "package must include at least one instruction file or skill" in empty_pack.text
    )

    latest = _publish(client, owner_token, _package_files(version="latest"))
    assert latest.status_code == 400

    oversized_body = _package_files()
    oversized_body["instructions/AGENTS.md"] = "x" * (
        MAX_PACKAGE_PUBLISH_BODY_BYTES + 1
    )
    oversized_response = _publish(client, owner_token, oversized_body)
    assert oversized_response.status_code == 413

    first = _publish(client, owner_token, _package_files())
    assert first.status_code == 201, first.text
    duplicate = _publish(
        client,
        owner_token,
        _package_files(agents="Attempt overwrite.\n"),
    )
    assert duplicate.status_code == 409
    stored = (
        tmp_path
        / "packages"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert stored == "Use AGENTS.\n"


def test_owner_publishes_skill_only_package(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    response = _publish(client, owner_token, _package_files(agents=None, skill=True))

    assert response.status_code == 201, response.text
    stored_skill = (
        tmp_path
        / "packages"
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
        / "packages"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    ).exists()


def test_package_skill_directory_requires_skill_md(tmp_path: Path, monkeypatch) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    files = _package_files(agents=None)
    files["skills/lint/README.md"] = "missing SKILL\n"

    response = _publish(client, owner_token, files)

    assert response.status_code == 400
    assert "unexpected package file path: skills/lint/README.md" in response.text


def test_package_publish_rejects_unexpected_server_payload_paths(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)

    extra_root = _package_files(skill=True)
    extra_root["extra.txt"] = "unexpected\n"
    root_response = _publish(client, owner_token, extra_root)
    assert root_response.status_code == 400
    assert "unexpected package file path: extra.txt" in root_response.text

    extra_instruction = _package_files(agents=None, skill=True)
    extra_instruction["instructions/EXTRA.md"] = "unexpected\n"
    instruction_response = _publish(client, owner_token, extra_instruction)
    assert instruction_response.status_code == 400
    assert (
        "unexpected package file path: instructions/EXTRA.md"
        in instruction_response.text
    )

    skills_file = _package_files(agents=None)
    skills_file["skills"] = "not a directory\n"
    skills_response = _publish(client, owner_token, skills_file)
    assert skills_response.status_code == 400
    assert "skills must be a directory" in skills_response.text


def test_package_routes_require_auth_and_publish_requires_admin(
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

    assert client.get("/api/v1/packages").status_code == 401
    assert (
        client.post("/api/v1/packages", json={"files": _package_files()}).status_code
        == 401
    )
    forbidden = _publish(client, member_token, _package_files())
    assert forbidden.status_code == 403

    assert _publish(client, owner_token, _package_files()).status_code == 201
    list_as_member = client.get("/api/v1/packages", headers=_auth(member_token))
    assert list_as_member.status_code == 200
    download_as_member = client.get(
        "/api/v1/packages/acme/onboarding/versions/1.0.0/files/agh.package.toml",
        headers=_auth(member_token),
    )
    assert download_as_member.status_code == 200


def test_package_publish_rejects_path_traversal_and_symlinked_storage(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    traversal = _package_files()
    traversal["../evil.txt"] = "outside"

    response = _publish(client, owner_token, traversal)

    assert response.status_code == 400
    assert not (tmp_path / "evil.txt").exists()

    outside = tmp_path / "outside"
    outside.mkdir()
    packages_root = tmp_path / "packages"
    shutil.rmtree(packages_root)
    packages_root.symlink_to(outside, target_is_directory=True)
    root_symlink_response = _publish(client, owner_token, _package_files())
    assert root_symlink_response.status_code == 400
    assert not (outside / ".staging").exists()

    packages_root.unlink()
    packages_root.mkdir(exist_ok=True)
    (packages_root / "acme").symlink_to(outside, target_is_directory=True)
    symlink_response = _publish(client, owner_token, _package_files())
    assert symlink_response.status_code == 400
    assert not (outside / "onboarding").exists()


def test_package_file_download_rejects_traversal_and_symlinks(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _package_files()).status_code == 201

    traversal = client.get(
        "/api/v1/packages/acme/onboarding/versions/1.0.0/files/%2e%2e/agh.package.toml",
        headers=_auth(owner_token),
    )
    assert traversal.status_code == 404
    assert traversal.json() == {"detail": "package file not found"}

    outside = tmp_path / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    symlink = tmp_path / "packages" / "acme" / "onboarding" / "1.0.0" / "leak.md"
    symlink.symlink_to(outside)
    leak = client.get(
        "/api/v1/packages/acme/onboarding/versions/1.0.0/files/leak.md",
        headers=_auth(owner_token),
    )
    assert leak.status_code == 404
    assert leak.json() == {"detail": "package file not found"}


def test_package_file_download_missing_artifact_returns_json_404(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _package_files()).status_code == 201
    stored_file = _stored_agents_file(tmp_path)
    stored_file.unlink()

    response = client.get(
        "/api/v1/packages/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "package file not found"}


def test_package_file_download_unreadable_artifact_returns_json_503(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _package_files()).status_code == 201
    stored_file = _stored_agents_file(tmp_path)
    stored_file.write_bytes(b"\xff\xfe\x00")

    response = client.get(
        "/api/v1/packages/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "package artifact storage unavailable"}


def test_package_file_download_read_error_returns_json_503(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _package_files()).status_code == 201
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
        "/api/v1/packages/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "package artifact storage unavailable"}


def test_package_file_download_path_resolution_error_returns_json_503(
    tmp_path: Path, monkeypatch
) -> None:
    client, owner_token = _client_with_owner(tmp_path, monkeypatch)
    assert _publish(client, owner_token, _package_files()).status_code == 201
    stored_file = _stored_agents_file(tmp_path)
    original_resolve = Path.resolve

    def fail_candidate_resolve(self: Path, strict: bool = False) -> Path:
        if self == stored_file and strict:
            raise OSError("simulated path resolution failure")
        return original_resolve(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_candidate_resolve)

    response = client.get(
        "/api/v1/packages/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
        headers=_auth(owner_token),
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "package artifact storage unavailable"}
