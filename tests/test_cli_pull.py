from __future__ import annotations

import json
import subprocess
import threading
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest
from typer.testing import CliRunner

from agh.cli.main import app as cli_app
from agh.cli.pull_markers import render_managed_block
from agh.cli.workspace_pull import WorkspacePullError, pull_workspace
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
            "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/CLAUDE.md",
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


def _dual_agent_manifest(*, content: str = "Use AGH.\n") -> dict[str, Any]:
    checksum = managed_payload_checksum(content)
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
                        "checksum": checksum,
                        "download_url": "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
                    },
                    {
                        "kind": "instruction",
                        "path": "instructions/CLAUDE.md",
                        "target_agent": "claude",
                        "target_path": "CLAUDE.md",
                        "checksum": checksum,
                        "download_url": "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/CLAUDE.md",
                    },
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


def _instruction_and_skill_manifest(*, content: str = "Use AGH.\n") -> dict[str, Any]:
    checksum = managed_payload_checksum(content)
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
                        "checksum": checksum,
                        "download_url": "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
                    },
                    {
                        "kind": "skill",
                        "path": "skills/reviewer/SKILL.md",
                        "target_agent": "opencode",
                        "target_path": ".opencode/skills/reviewer/SKILL.md",
                        "checksum": checksum,
                        "download_url": "/api/v1/packs/acme/onboarding/versions/1.0.0/files/skills/reviewer/SKILL.md",
                    },
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


def _write_link(
    repo: Path,
    *,
    url: str = "http://127.0.0.1:1",
    agent_target: str | None = "opencode",
) -> None:
    agh_dir = repo / ".agh"
    agh_dir.mkdir()
    (agh_dir / "project.toml").write_text(
        f'instance_url = "{url}"\nproject_id = "prj_1"\nrepo_url_normalized = "github.com/acme/app"\nsynced_at = "2026-05-31T00:00:00Z"\n',
        encoding="utf-8",
    )
    if agent_target is not None:
        preferences = repo / ".agh-cache" / "preferences.toml"
        preferences.parent.mkdir()
        preferences.write_text(
            f'[agents]\ntarget = "{agent_target}"\nselected_at = "2026-06-03T00:00:00Z"\n',
            encoding="utf-8",
        )


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def _init_git(repo: Path) -> None:
    subprocess.run(
        ["git", "init"], cwd=repo, check=True, capture_output=True, text=True
    )


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
    assert "Dry run complete: 1 change planned, 0 conflicts." in result.stdout
    assert "Planned:\n  AGENTS.md" in result.stdout
    assert "No files were written." in result.stdout
    assert '"dry_run"' not in result.stdout
    assert not (repo / "AGENTS.md").exists()
    assert not (repo / ".agh-cache" / "packs").exists()
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


def test_pull_dry_run_preserves_previous_public_state(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    previous_target = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "Previous.\n"
    )
    (repo / "AGENTS.md").write_text(previous_target, encoding="utf-8")
    previous_cache = (
        repo / ".agh-cache/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"
    )
    previous_cache.parent.mkdir(parents=True)
    previous_cache.write_text("Previous.\n", encoding="utf-8")
    lock = repo / ".agh" / "lock.toml"
    lock.write_text("previous lock\n", encoding="utf-8")
    server, _handler, url = _serve_pull(content="New.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(
            cli_app, ["pull", "--dry-run"], env=_write_config(tmp_path, url)
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Dry run complete: 1 change planned, 0 conflicts." in result.stdout
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == previous_target
    assert previous_cache.read_text(encoding="utf-8") == "Previous.\n"
    assert lock.read_text(encoding="utf-8") == "previous lock\n"
    assert not list((repo / ".agh-cache" / "packs").rglob(".agh-pull-stage-*"))


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
    assert "Pull complete: 1 changed, 0 conflicts." in result.stdout
    assert "Updated:\n  AGENTS.md" in result.stdout
    assert "Lockfile: .agh/lock.toml" in result.stdout
    assert '"status"' not in result.stdout
    target = repo / "AGENTS.md"
    assert "<!-- AGH-BEGIN" in target.read_text(encoding="utf-8")
    cached = (
        repo
        / ".agh-cache"
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
        == ".agh-cache/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"
    )
    assert lock["artifacts"][0]["checksum"] == managed_payload_checksum(
        cached.read_text(encoding="utf-8")
    )
    assert not list((repo / ".agh-cache" / "packs").rglob(".agh-pull-stage-*"))


def test_successful_pull_removes_pre_existing_stale_cache_stages(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    pack_parent = repo / ".agh-cache" / "packs" / "acme" / "onboarding"
    stale_stage = pack_parent / ".agh-pull-stage-1.0.0-stale"
    stale_stage.mkdir(parents=True)
    (stale_stage / "orphan.txt").write_text("stale\n", encoding="utf-8")
    previous_cache = pack_parent / "0.9.0" / "instructions" / "AGENTS.md"
    previous_cache.parent.mkdir(parents=True)
    previous_cache.write_text("previous\n", encoding="utf-8")
    unrelated_dir = pack_parent / "manual-stage"
    unrelated_dir.mkdir()

    server, _handler, url = _serve_pull(
        content="Use AGH.\n", manifest=_instruction_and_skill_manifest()
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Pull complete: 2 changed, 0 conflicts." in result.stdout
    assert "Use AGH." in (repo / "AGENTS.md").read_text(encoding="utf-8")
    skill_target = repo / ".opencode" / "skills" / "reviewer" / "SKILL.md"
    assert skill_target.read_text(encoding="utf-8") == "Use AGH.\n"
    instruction_cache = pack_parent / "1.0.0" / "instructions" / "AGENTS.md"
    skill_cache = pack_parent / "1.0.0" / "skills" / "reviewer" / "SKILL.md"
    assert instruction_cache.read_text(encoding="utf-8") == "Use AGH.\n"
    assert skill_cache.read_text(encoding="utf-8") == "Use AGH.\n"
    lock = tomllib.loads((repo / ".agh" / "lock.toml").read_text(encoding="utf-8"))
    artifacts_by_target = {
        artifact["target_path"]: artifact for artifact in lock["artifacts"]
    }
    assert set(artifacts_by_target) == {
        "AGENTS.md",
        ".opencode/skills/reviewer/SKILL.md",
    }
    assert artifacts_by_target["AGENTS.md"]["source"] == (
        ".agh-cache/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"
    )
    assert artifacts_by_target["AGENTS.md"]["checksum"] == managed_payload_checksum(
        instruction_cache.read_text(encoding="utf-8")
    )
    assert artifacts_by_target[".opencode/skills/reviewer/SKILL.md"]["source"] == (
        ".agh-cache/packs/acme/onboarding/1.0.0/skills/reviewer/SKILL.md"
    )
    assert artifacts_by_target[".opencode/skills/reviewer/SKILL.md"]["checksum"] == (
        managed_payload_checksum(skill_cache.read_text(encoding="utf-8"))
    )
    assert (
        artifacts_by_target[".opencode/skills/reviewer/SKILL.md"]["mode"] == "symlink"
    )
    assert previous_cache.read_text(encoding="utf-8") == "previous\n"
    assert unrelated_dir.exists()
    assert not list((repo / ".agh-cache" / "packs").rglob(".agh-pull-stage-*"))


def test_pull_filters_manifest_to_selected_agent(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target="claude")
    server, handler, url = _serve_pull(
        content="Use AGH.\n", manifest=_dual_agent_manifest()
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Updated:\n  CLAUDE.md" in result.stdout
    assert (repo / "CLAUDE.md").exists()
    assert not (repo / "AGENTS.md").exists()
    assert not (
        repo
        / ".agh-cache"
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    ).exists()
    lock = tomllib.loads((repo / ".agh" / "lock.toml").read_text(encoding="utf-8"))
    assert [artifact["target_path"] for artifact in lock["artifacts"]] == ["CLAUDE.md"]
    assert handler.requests == [
        {
            "path": "/api/v1/projects/prj_1/pull-manifest",
            "authorization": "Bearer pull-secret-token",
        },
        {
            "path": "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/CLAUDE.md",
            "authorization": "Bearer pull-secret-token",
        },
    ]


def test_pull_missing_agent_preference_non_tty_exits_2_without_server_call(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target=None)
    server, handler, url = _serve_pull(content="Use AGH.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 2, result.stdout
    assert "no local agent selected" in result.stdout
    assert "agh agent select claude" in result.stdout
    assert "agh agent select opencode" in result.stdout
    assert handler.requests == []
    assert not (repo / "AGENTS.md").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_prompt_skip_exits_2_without_selection(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target=None)
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "3")

    with pytest.raises(WorkspacePullError) as exc_info:
        pull_workspace(cwd=repo)

    assert exc_info.value.code == 2
    assert "agent selection skipped" in str(exc_info.value)
    assert not (repo / ".agh-cache" / "preferences.toml").exists()


def test_pull_prompt_selects_agent_and_continues(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target=None)
    server, _handler, url = _serve_pull(
        content="Use AGH.\n", manifest=_dual_agent_manifest()
    )
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "2")
    monkeypatch.setenv("AGH_CONFIG_FILE", str(tmp_path / "config.toml"))
    _write_config(tmp_path, url)
    try:
        result = pull_workspace(cwd=repo)
    finally:
        server.shutdown()

    assert result.exit_code == 0
    preferences = tomllib.loads(
        (repo / ".agh-cache" / "preferences.toml").read_text(encoding="utf-8")
    )
    assert preferences["agents"]["target"] == "opencode"
    assert (repo / "AGENTS.md").exists()
    assert not (repo / "CLAUDE.md").exists()


def test_pull_dry_run_prompt_does_not_write_preferences(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target=None)
    server, _handler, url = _serve_pull(
        content="Use AGH.\n", manifest=_dual_agent_manifest()
    )
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "2")
    monkeypatch.setenv("AGH_CONFIG_FILE", str(tmp_path / "config.toml"))
    _write_config(tmp_path, url)
    try:
        result = pull_workspace(cwd=repo, dry_run=True)
    finally:
        server.shutdown()

    assert result.exit_code == 0
    assert not (repo / ".agh-cache" / "preferences.toml").exists()
    assert not (repo / "AGENTS.md").exists()
    assert not (repo / ".agh-cache" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_clears_stale_cache_entries_when_agent_selection_changes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target="opencode")
    server, _handler, url = _serve_pull(
        content="Use AGH.\n", manifest=_dual_agent_manifest()
    )
    monkeypatch.chdir(repo)
    try:
        first = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
        (repo / ".agh-cache" / "preferences.toml").write_text(
            '[agents]\ntarget = "claude"\nselected_at = "2026-06-03T00:00:00Z"\n',
            encoding="utf-8",
        )
        second = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    assert not (
        repo
        / ".agh-cache"
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    ).exists()
    assert (
        repo
        / ".agh-cache"
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "CLAUDE.md"
    ).exists()
    lock = tomllib.loads((repo / ".agh" / "lock.toml").read_text(encoding="utf-8"))
    assert [artifact["target_path"] for artifact in lock["artifacts"]] == ["CLAUDE.md"]


def test_pull_success_in_git_repo_prints_vcs_hint_when_cache_not_ignored(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _init_git(repo)
    _write_link(repo)
    server, _handler, url = _serve_pull(content="Use AGH.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Hint: add .agh-cache/ to .gitignore" in result.stdout
    assert "Commit .agh/project.toml and .agh/lock.toml" in result.stdout


def test_pull_success_in_git_repo_suppresses_vcs_hint_when_cache_ignored(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _init_git(repo)
    (repo / ".gitignore").write_text(".agh-cache/\n", encoding="utf-8")
    _write_link(repo)
    server, _handler, url = _serve_pull(content="Use AGH.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Hint: add .agh-cache/ to .gitignore" not in result.stdout


def test_pull_vcs_hint_timeout_skips_hint_and_keeps_pull_success(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _init_git(repo)
    _write_link(repo)
    server, _handler, url = _serve_pull(content="Use AGH.\n")
    monkeypatch.chdir(repo)

    def timeout_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["git", "rev-parse"], timeout=5)

    monkeypatch.setattr("agh.cli.workspace_pull.subprocess.run", timeout_run)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Pull complete: 1 changed, 0 conflicts." in result.stdout
    assert "Lockfile: .agh/lock.toml" in result.stdout
    assert "Hint: add .agh-cache/ to .gitignore" not in result.stdout
    assert (repo / "AGENTS.md").exists()
    assert (repo / ".agh" / "lock.toml").exists()


def test_pull_vcs_check_ignore_timeout_skips_hint_and_keeps_pull_success(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _init_git(repo)
    _write_link(repo)
    server, _handler, url = _serve_pull(content="Use AGH.\n")
    monkeypatch.chdir(repo)

    def check_ignore_timeout_run(
        cmd: list[str], *args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if cmd[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="true\n", stderr="")
        if cmd[:2] == ["git", "check-ignore"]:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=5)
        raise AssertionError(f"unexpected command: {cmd!r}")

    monkeypatch.setattr(
        "agh.cli.workspace_pull.subprocess.run", check_ignore_timeout_run
    )
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Pull complete: 1 changed, 0 conflicts." in result.stdout
    assert "Lockfile: .agh/lock.toml" in result.stdout
    assert "Hint: add .agh-cache/ to .gitignore" not in result.stdout
    assert (repo / "AGENTS.md").exists()
    assert (repo / ".agh" / "lock.toml").exists()


def test_pull_suppresses_vcs_hint_for_empty_manifest_when_cache_ignored(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _init_git(repo)
    (repo / ".gitignore").write_text(".agh-cache/\n", encoding="utf-8")
    _write_link(repo)
    manifest = _manifest()
    manifest["packs"][0]["artifacts"] = []
    server, _handler, url = _serve_pull(manifest=manifest)
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Pull complete: no changes." in result.stdout
    assert "Lockfile: .agh/lock.toml" in result.stdout
    assert "Hint: add .agh-cache/ to .gitignore" not in result.stdout
    assert not (repo / ".agh-cache" / "packs").exists()


def test_pull_dry_run_in_git_repo_does_not_print_vcs_hint(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _init_git(repo)
    _write_link(repo)
    server, _handler, url = _serve_pull(content="Use AGH.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(
            cli_app, ["pull", "--dry-run"], env=_write_config(tmp_path, url)
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Hint: add .agh-cache/ to .gitignore" not in result.stdout
    assert not (repo / ".agh-cache" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


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
    assert "Pull blocked: 1 conflict." in result.stdout
    assert "Conflicts:\n  AGENTS.md" in result.stdout
    assert "Run with --force to replace AGH-managed blocks." in result.stdout
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == before
    assert not (repo / ".agh-cache" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_conflict_preserves_previous_cache_and_lock(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    original = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "Original.\n"
    )
    conflicted = original.replace("Original.", "Edited by user.")
    (repo / "AGENTS.md").write_text(f"Manual\n\n{conflicted}", encoding="utf-8")
    before = (repo / "AGENTS.md").read_text(encoding="utf-8")
    previous_cache = (
        repo / ".agh-cache/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"
    )
    previous_cache.parent.mkdir(parents=True)
    previous_cache.write_text("Previous.\n", encoding="utf-8")
    lock = repo / ".agh" / "lock.toml"
    lock.write_text("previous lock\n", encoding="utf-8")
    server, _handler, url = _serve_pull(content="New.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 3, result.stdout
    assert "Pull blocked: 1 conflict." in result.stdout
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == before
    assert previous_cache.read_text(encoding="utf-8") == "Previous.\n"
    assert lock.read_text(encoding="utf-8") == "previous lock\n"
    assert not list((repo / ".agh-cache" / "packs").rglob(".agh-pull-stage-*"))


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
    assert not (repo / ".agh-cache" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_places_skill_as_relative_symlink_and_records_lock_mode(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target="claude")
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
        == ".agh-cache/packs/acme/onboarding/1.0.0/skills/reviewer/SKILL.md"
    )


def test_pull_rejects_file_at_cache_root_before_target_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target=None)
    (repo / ".agh-cache").write_text("not a directory\n", encoding="utf-8")
    server, _handler, url = _serve_pull(content="Use AGH.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 2, result.stdout
    assert "non-directory AGH cache path" in result.stdout
    assert not (repo / "AGENTS.md").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_rejects_file_at_cache_packs_before_target_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    (repo / ".agh-cache" / "packs").write_text("not a directory\n", encoding="utf-8")
    server, _handler, url = _serve_pull(content="Use AGH.\n")
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 2, result.stdout
    assert "non-directory AGH cache path" in result.stdout
    assert not (repo / "AGENTS.md").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_replaces_old_pre_release_skill_cache_symlink(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target="claude")
    old_source = (
        repo
        / ".agh"
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "skills"
        / "reviewer"
        / "SKILL.md"
    )
    old_source.parent.mkdir(parents=True)
    old_source.write_text("Old cache.\n", encoding="utf-8")
    target = repo / ".claude" / "skills" / "reviewer" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.symlink_to(
        Path("../../../.agh/packs/acme/onboarding/1.0.0/skills/reviewer/SKILL.md")
    )
    server, _handler, url = _serve_pull(
        content="Review carefully.\n", manifest=_skill_manifest()
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["pull"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Pull complete: 1 changed, 0 conflicts." in result.stdout
    assert target.is_symlink()
    assert ".agh-cache" in target.readlink().as_posix()
    assert target.read_text(encoding="utf-8") == "Review carefully.\n"
    lock = tomllib.loads((repo / ".agh" / "lock.toml").read_text(encoding="utf-8"))
    assert (
        lock["artifacts"][0]["source"]
        == ".agh-cache/packs/acme/onboarding/1.0.0/skills/reviewer/SKILL.md"
    )


def test_pull_workspace_lock_failure_preserves_previous_public_state(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    previous_target = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "Previous.\n"
    )
    (repo / "AGENTS.md").write_text(previous_target, encoding="utf-8")
    previous_cache = (
        repo / ".agh-cache/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"
    )
    previous_cache.parent.mkdir(parents=True)
    previous_cache.write_text("Previous.\n", encoding="utf-8")
    lock = repo / ".agh" / "lock.toml"
    lock.write_text("previous lock\n", encoding="utf-8")
    server, _handler, url = _serve_pull(content="New.\n")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGH_CONFIG_FILE", str(tmp_path / "config.toml"))
    _write_config(tmp_path, url)

    def fail_lock_write(_path: Path, *, manifest: dict, artifacts: list) -> None:
        raise OSError("lock failed")

    monkeypatch.setattr("agh.cli.workspace_pull._write_lockfile", fail_lock_write)
    try:
        with pytest.raises(WorkspacePullError, match="failed to write pull results"):
            pull_workspace(cwd=repo)
    finally:
        server.shutdown()

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == previous_target
    assert previous_cache.read_text(encoding="utf-8") == "Previous.\n"
    assert lock.read_text(encoding="utf-8") == "previous lock\n"


def test_pull_workspace_stale_cleanup_failure_preserves_previous_public_state(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo)
    previous_target = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "Previous.\n"
    )
    (repo / "AGENTS.md").write_text(previous_target, encoding="utf-8")
    previous_cache = (
        repo / ".agh-cache/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"
    )
    previous_cache.parent.mkdir(parents=True)
    previous_cache.write_text("Previous.\n", encoding="utf-8")
    lock = repo / ".agh" / "lock.toml"
    lock.write_text("previous lock\n", encoding="utf-8")
    server, _handler, url = _serve_pull(content="New.\n")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGH_CONFIG_FILE", str(tmp_path / "config.toml"))
    _write_config(tmp_path, url)

    def fail_stale_cleanup(_workspace: Path, *, manifest: object) -> None:
        raise OSError("stale cleanup failed")

    monkeypatch.setattr(
        "agh.cli.workspace_pull._cleanup_stale_cache_staging_dirs",
        fail_stale_cleanup,
    )
    try:
        with pytest.raises(WorkspacePullError, match="failed to write pull results"):
            pull_workspace(cwd=repo)
    finally:
        server.shutdown()

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == previous_target
    assert previous_cache.read_text(encoding="utf-8") == "Previous.\n"
    assert lock.read_text(encoding="utf-8") == "previous lock\n"
    assert not list((repo / ".agh-cache" / "packs").rglob(".agh-pull-stage-*"))


def test_pull_skill_copy_fallback_when_symlink_fails(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target="claude")
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
    _write_link(repo, agent_target="claude")
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
    assert "Pull blocked: 1 conflict." in result.stdout
    assert "Conflicts:\n  .claude/skills/reviewer/SKILL.md" in result.stdout
    assert "Run with --force to replace AGH-managed blocks." in result.stdout
    assert target.read_text(encoding="utf-8") == before
    assert not (repo / ".agh-cache" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_skill_force_replaces_existing_target(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target="claude")
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
    _write_link(repo, agent_target="claude")
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
    assert "Dry run complete: 1 change planned, 0 conflicts." in result.stdout
    assert "Planned:\n  .claude/skills/reviewer/SKILL.md" in result.stdout
    assert "No files were written." in result.stdout
    assert not (repo / ".claude").exists()
    assert not (repo / ".agh-cache" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_skill_rejects_unapproved_target_path_without_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target="claude")
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
    assert not (repo / ".agh-cache" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_skill_rejects_target_agent_path_mismatch_without_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target="claude")
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
    assert not (repo / ".agh-cache" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_skill_rejects_cursor_target_agent_without_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target="claude")
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
    assert not (repo / ".agh-cache" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()


def test_pull_skill_rejects_symlinked_target_parent_without_writes(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _write_link(repo, agent_target="claude")
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
    assert not (repo / ".agh-cache" / "packs").exists()
    assert not (repo / ".agh" / "lock.toml").exists()
