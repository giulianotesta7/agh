from __future__ import annotations

import json
import threading
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

from typer.testing import CliRunner

from agh.cli.main import app as cli_app
from agh.cli.pull_markers import render_managed_block
from agh.common.checksums import managed_payload_checksum


class _PullHandler(BaseHTTPRequestHandler):
    manifest: ClassVar[dict[str, Any] | str] = {}
    artifact_content: ClassVar[str] = "Use AGH.\n"
    manifest_status: ClassVar[int] = 200
    artifact_status: ClassVar[int] = 200
    requests: ClassVar[list[dict[str, str | None]]] = []

    def do_GET(self) -> None:  # noqa: N802
        type(self).requests.append(
            {"path": self.path, "authorization": self.headers.get("Authorization")}
        )
        if self.path == "/api/v1/projects/prj_1/pull-manifest":
            self.send_response(type(self).manifest_status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(type(self).manifest).encode("utf-8"))
            return
        if self.path in {
            "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
            "/api/v1/packs/acme/onboarding/versions/1.0.0/files/skills/reviewer/SKILL.md",
        }:
            self.send_response(type(self).artifact_status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(type(self).artifact_content.encode("utf-8"))
            return
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"detail":"not found"}')

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def _serve_pull(
    *,
    content: str = "Use AGH.\n",
    manifest: dict[str, Any] | None = None,
    manifest_status: int = 200,
):
    class Handler(_PullHandler):
        pass

    Handler.artifact_content = content
    Handler.manifest = manifest if manifest is not None else _manifest(content=content)
    Handler.manifest_status = manifest_status
    Handler.artifact_status = 200
    Handler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, Handler, f"http://127.0.0.1:{server.server_port}"


def _manifest(*, content: str = "Use AGH.\n") -> dict[str, Any]:
    return {
        "project": {"id": "prj_1", "name": "Demo"},
        "packs": [
            {
                "id": "acme/onboarding@1.0.0",
                "assignment_id": "asn_1",
                "position": 0,
                "manifest": {
                    "domain": "acme",
                    "name": "onboarding",
                    "version": "1.0.0",
                },
                "artifacts": [
                    {
                        "kind": "instruction",
                        "path": "instructions/AGENTS.md",
                        "target_agent": "opencode",
                        "target_path": "AGENTS.md",
                        "checksum": managed_payload_checksum(content),
                        "download_url": "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
                    }
                ],
            }
        ],
    }


def _skill_manifest(*, content: str = "Review carefully.\n") -> dict[str, Any]:
    return {
        "project": {"id": "prj_1", "name": "Demo"},
        "packs": [
            {
                "id": "acme/onboarding@1.0.0",
                "assignment_id": "asn_1",
                "position": 0,
                "manifest": {
                    "domain": "acme",
                    "name": "onboarding",
                    "version": "1.0.0",
                },
                "artifacts": [
                    {
                        "kind": "skill",
                        "path": "skills/reviewer/SKILL.md",
                        "target_agent": "claude",
                        "target_path": ".claude/skills/reviewer/SKILL.md",
                        "checksum": managed_payload_checksum(content),
                        "download_url": "/api/v1/packs/acme/onboarding/versions/1.0.0/files/skills/reviewer/SKILL.md",
                    }
                ],
            }
        ],
    }


def _write_config(
    tmp_path: Path, url: str, token: str = "pull-secret-token"
) -> dict[str, str]:
    path = tmp_path / "config.toml"
    path.write_text(
        f'instance_url = "{url}"\nemail = "dev@example.com"\ntoken = "{token}"\n',
        encoding="utf-8",
    )
    return {"AGH_CONFIG_FILE": str(path)}


def _write_link(repo: Path, *, url: str = "http://127.0.0.1:1") -> None:
    agh_dir = repo / ".agh"
    agh_dir.mkdir()
    (agh_dir / "project.toml").write_text(
        f'instance_url = "{url}"\nproject_id = "prj_1"\nrepo_url_normalized = "github.com/acme/app"\nsynced_at = "2026-05-31T00:00:00Z"\n',
        encoding="utf-8",
    )


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def test_pull_dry_run_downloads_for_planning_without_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    server, handler, url = _serve_pull(content="Use AGH.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(
            cli_app, ["pull", "--dry-run"], env=_write_config(tmp_path, url)
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert '"status": "changed"' in result.stdout
    assert '"dry_run": true' in result.stdout
    assert not (repo / "AGENTS.md").exists()
    assert not (repo / ".agh" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()
    assert handler.requests == [
        {
            "path": "/api/v1/projects/prj_1/pull-manifest",
            "authorization": "Bearer pull-secret-token",
        },
        {
            "path": "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
            "authorization": "Bearer pull-secret-token",
        },
    ]


def test_pull_writes_target_cache_and_lock(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    server, _handler, url = _serve_pull(content="Use AGH.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    target = repo / "AGENTS.md"
    assert "<!-- AGH-BEGIN" in target.read_text(encoding="utf-8")
    cached = (
        repo
        / ".agh"
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    )
    assert cached.read_text(encoding="utf-8") == "Use AGH.\n"
    lock = tomllib.loads((repo / ".agh" / "lock.toml").read_text(encoding="utf-8"))
    assert lock["project"]["id"] == "prj_1"
    assert (
        lock["artifacts"][0]["source"]
        == ".agh/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"
    )


def test_pull_conflict_exits_3_without_writes(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    original = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "Original.\n"
    )
    conflicted = original.replace("Original.", "Edited by user.")
    (repo / "AGENTS.md").write_text(f"Manual\n\n{conflicted}", encoding="utf-8")
    before = (repo / "AGENTS.md").read_text(encoding="utf-8")
    server, _handler, url = _serve_pull(content="Use AGH.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 3, result.stdout
    assert '"status": "conflict"' in result.stdout
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == before
    assert not (repo / ".agh" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_force_overwrites_conflicted_block_only(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    original = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "Original.\n"
    )
    conflicted = original.replace("Original.", "Edited by user.")
    (repo / "AGENTS.md").write_text(
        f"Before\n\n{conflicted}\nAfter\n", encoding="utf-8"
    )
    server, _handler, url = _serve_pull(content="Forced.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(
            cli_app, ["pull", "--force"], env=_write_config(tmp_path, url)
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert text.startswith("Before\n\n")
    assert text.endswith("\nAfter\n")
    assert "Forced.\n" in text
    assert "Edited by user." not in text
    assert (repo / ".agh" / "lock.toml").exists()


def test_pull_missing_link_exits_5(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)

    result = CliRunner().invoke(
        cli_app, ["pull"], env={"AGH_CONFIG_FILE": str(tmp_path / "missing.toml")}
    )

    assert result.exit_code == 5
    assert "not linked" in result.stdout


def test_pull_auth_error_exits_4(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    server, _handler, url = _serve_pull(manifest_status=401)
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 4
    assert "HTTP 401" in result.stdout


def test_pull_invalid_manifest_path_exits_2_without_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    manifest = _manifest()
    manifest["packs"][0]["artifacts"][0]["target_path"] = "../AGENTS.md"
    server, _handler, url = _serve_pull(manifest=manifest)
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "invalid artifact path" in result.stdout
    assert not (repo / "AGENTS.md").exists()
    assert not (repo / ".agh" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_places_skill_as_relative_symlink_and_records_lock_mode(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    server, _handler, url = _serve_pull(
        content="Review carefully.\n", manifest=_skill_manifest()
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    target = repo / ".claude" / "skills" / "reviewer" / "SKILL.md"
    assert target.is_symlink()
    assert not target.read_text(encoding="utf-8").startswith("<!-- AGH-BEGIN")
    assert target.read_text(encoding="utf-8") == "Review carefully.\n"
    link_target = target.readlink()
    assert not link_target.is_absolute()
    lock = tomllib.loads((repo / ".agh" / "lock.toml").read_text(encoding="utf-8"))
    artifact = lock["artifacts"][0]
    assert artifact["mode"] == "symlink"
    assert (
        artifact["source"]
        == ".agh/packs/acme/onboarding/1.0.0/skills/reviewer/SKILL.md"
    )


def test_pull_skill_copy_fallback_when_symlink_fails(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    server, _handler, url = _serve_pull(
        content="Review carefully.\n", manifest=_skill_manifest()
    )
    monkeypatch.setattr(
        Path,
        "symlink_to",
        lambda self, target: (_ for _ in ()).throw(OSError("no symlink")),
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    target = repo / ".claude" / "skills" / "reviewer" / "SKILL.md"
    assert target.is_file()
    assert not target.is_symlink()
    assert target.read_text(encoding="utf-8") == "Review carefully.\n"
    lock = tomllib.loads((repo / ".agh" / "lock.toml").read_text(encoding="utf-8"))
    assert lock["artifacts"][0]["mode"] == "copy"


def test_pull_skill_conflict_exits_3_without_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    target = repo / ".claude" / "skills" / "reviewer" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("Local skill.\n", encoding="utf-8")
    before = target.read_text(encoding="utf-8")
    server, _handler, url = _serve_pull(
        content="Review carefully.\n", manifest=_skill_manifest()
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 3, result.stdout
    assert '"status": "conflict"' in result.stdout
    assert target.read_text(encoding="utf-8") == before
    assert not (repo / ".agh" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_skill_force_replaces_existing_target(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    target = repo / ".claude" / "skills" / "reviewer" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("Local skill.\n", encoding="utf-8")
    unrelated = repo / ".claude" / "skills" / "other.txt"
    unrelated.write_text("keep\n", encoding="utf-8")
    server, _handler, url = _serve_pull(
        content="Review carefully.\n", manifest=_skill_manifest()
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(
            cli_app, ["pull", "--force"], env=_write_config(tmp_path, url)
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert target.read_text(encoding="utf-8") == "Review carefully.\n"
    assert unrelated.read_text(encoding="utf-8") == "keep\n"


def test_pull_skill_dry_run_has_no_writes(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    server, _handler, url = _serve_pull(
        content="Review carefully.\n", manifest=_skill_manifest()
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(
            cli_app, ["pull", "--dry-run"], env=_write_config(tmp_path, url)
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert '"target_path": ".claude/skills/reviewer/SKILL.md"' in result.stdout
    assert not (repo / ".claude").exists()
    assert not (repo / ".agh" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_skill_rejects_unapproved_target_path_without_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    manifest = _skill_manifest()
    manifest["packs"][0]["artifacts"][0]["target_path"] = ".git/hooks/pre-commit"
    server, _handler, url = _serve_pull(
        content="Review carefully.\n", manifest=manifest
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 2, result.stdout
    assert "invalid claude skill target path" in result.stdout
    assert not (repo / ".git" / "hooks" / "pre-commit").exists()
    assert not (repo / ".agh" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_skill_rejects_target_agent_path_mismatch_without_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    manifest = _skill_manifest()
    manifest["packs"][0]["artifacts"][0]["target_agent"] = "opencode"
    server, _handler, url = _serve_pull(
        content="Review carefully.\n", manifest=manifest
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 2, result.stdout
    assert "invalid opencode skill target path" in result.stdout
    assert not (repo / ".claude").exists()
    assert not (repo / ".agh" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_skill_rejects_cursor_target_agent_without_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    manifest = _skill_manifest()
    manifest["packs"][0]["artifacts"][0]["target_agent"] = "cursor"
    manifest["packs"][0]["artifacts"][0]["target_path"] = ".cursor/rules/skill.md"
    server, _handler, url = _serve_pull(
        content="Review carefully.\n", manifest=manifest
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 2, result.stdout
    assert "unsupported pull manifest target_agent" in result.stdout
    assert not (repo / ".cursor").exists()
    assert not (repo / ".agh" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_skill_rejects_symlinked_target_parent_without_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    outside = tmp_path / "outside"
    outside.mkdir()
    claude = repo / ".claude"
    claude.mkdir()
    (claude / "skills").symlink_to(outside, target_is_directory=True)
    server, _handler, url = _serve_pull(
        content="Review carefully.\n", manifest=_skill_manifest()
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 2, result.stdout
    assert "symlinked directory" in result.stdout
    assert not (repo / ".agh" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()
