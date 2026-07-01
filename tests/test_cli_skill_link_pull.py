"""CLI skill/link/pull cleanup tests (Phase 5).

* `link` replaces `sync` with identical workspace-link behavior.
* `sync` is removed and is not a hidden alias.
* `pull` help points users to `link`.
* `skill` exposes only `list` and `install`.
* `skill install` uses `--target` and resolves: explicit > workspace > global >
  interactive prompt > non-interactive error.
* `skill remove`, `skill installed`, and `skill agent` are removed.
"""

from __future__ import annotations

import json
import subprocess
import threading
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

from pytest import MonkeyPatch
from typer.testing import CliRunner

from agh.cli import global_skills as gs
from agh.cli.agent_integrations import (
    read_global_skill_default_agent,
    write_agent_preference,
    write_global_skill_default_agent,
)
from agh.cli.main import app as cli_app


# --- link command behavior -------------------------------------------------


class _ProjectsHandler(BaseHTTPRequestHandler):
    projects: ClassVar[list[dict[str, Any]]] = []
    requests: ClassVar[list[dict[str, str | None]]] = []

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        type(self).requests.append(
            {"path": self.path, "authorization": self.headers.get("Authorization")}
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"projects": type(self).projects}).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib API
        return


def _serve_projects(projects: list[dict[str, Any]]):
    class Handler(_ProjectsHandler):
        pass

    Handler.projects = projects
    Handler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, Handler, f"http://127.0.0.1:{server.server_port}"


def _git_repo(tmp_path: Path, *, remotes: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    for name, url in remotes.items():
        subprocess.run(["git", "remote", "add", name, url], cwd=repo, check=True)
    return repo


def _write_config(
    tmp_path: Path, url: str, token: str = "link-secret-token"
) -> dict[str, str]:
    path = tmp_path / "config.toml"
    path.write_text(
        f'instance_url = "{url}"\nemail = "dev@example.com"\ntoken = "{token}"\n',
        encoding="utf-8",
    )
    return {"AGH_CONFIG_FILE": str(path)}


def test_link_matches_git_remote_and_writes_project_toml(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    repo = _git_repo(tmp_path, remotes={"origin": "git@github.com:Org/App.GIT"})
    server, handler, url = _serve_projects(
        [
            {
                "id": "prj_match",
                "name": "App",
                "repo_url": "https://github.com/org/app.git",
                "repo_url_normalized": "github.com/org/app",
                "active": True,
            }
        ]
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(cli_app, ["link"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Linked this repo to App (prj_match)." in result.stdout
    link = tomllib.loads((repo / ".agh" / "project.toml").read_text(encoding="utf-8"))
    assert link["project_id"] == "prj_match"
    assert handler.requests == [
        {"path": "/api/v1/projects", "authorization": "Bearer link-secret-token"}
    ]


def test_sync_command_is_not_supported(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root_help = CliRunner().invoke(cli_app, ["--help"]).stdout
    result = CliRunner().invoke(cli_app, ["sync"])

    assert result.exit_code == 2
    assert result.stdout == root_help


def test_link_help_has_no_manual_project_override() -> None:
    result = CliRunner().invoke(cli_app, ["link", "--help"])

    assert result.exit_code == 0, result.stdout
    assert "--remote" in result.stdout
    assert "--force" in result.stdout
    assert "--project" not in result.stdout


# --- pull help -------------------------------------------------------------


def test_pull_help_points_to_link_command() -> None:
    result = CliRunner().invoke(cli_app, ["pull", "--help"])

    assert result.exit_code == 0, result.stdout
    assert "link" in result.stdout.lower()


# --- skill install target resolution ---------------------------------------


def test_skill_install_help_uses_target_option() -> None:
    result = CliRunner().invoke(cli_app, ["skill", "install", "--help"])

    assert result.exit_code == 0, result.stdout
    assert "--target" in result.stdout
    assert "--agent" not in result.stdout


def _fake_install_target(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> list[tuple[str, str, str, bool]]:
    calls: list[tuple[str, str, str, bool]] = []

    def fake_install(
        agent: str, ref: str, name: str, *, force: bool
    ) -> gs.InstallResult:
        calls.append((agent, ref, name, force))
        target = (
            tmp_path / "home" / ".config" / "opencode" / "skills" / name / "SKILL.md"
        )
        return gs.InstallResult(target_path=target, changed=True)

    monkeypatch.setattr(
        "agh.cli.main.global_skills_module.install_skill_global",
        fake_install,
    )
    return calls


def test_skill_install_uses_explicit_target(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    calls = _fake_install_target(monkeypatch, tmp_path)

    result = CliRunner().invoke(
        cli_app,
        [
            "skill",
            "install",
            "acme/commenting@latest",
            "reviewer",
            "--target",
            "opencode",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls == [("opencode", "acme/commenting@latest", "reviewer", False)]
    assert "Installed reviewer" in result.stdout
    assert "OpenCode" in result.stdout


def test_skill_install_resolves_workspace_target_before_global(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.chdir(tmp_path)
    write_agent_preference("claude")
    write_global_skill_default_agent("opencode")

    calls: list[str] = []

    def fake_install(
        agent: str, ref: str, name: str, *, force: bool
    ) -> gs.InstallResult:
        calls.append(agent)
        target = home / ".config" / "opencode" / "skills" / name / "SKILL.md"
        return gs.InstallResult(target_path=target, changed=True)

    monkeypatch.setattr(
        "agh.cli.main.global_skills_module.install_skill_global",
        fake_install,
    )

    result = CliRunner().invoke(
        cli_app, ["skill", "install", "acme/commenting@latest", "reviewer"]
    )

    assert result.exit_code == 0, result.stdout
    assert calls == ["claude"]
    assert "Claude Code" in result.stdout


def test_skill_install_resolves_global_target_when_no_workspace_target(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.chdir(tmp_path)
    write_global_skill_default_agent("opencode")

    calls: list[str] = []

    def fake_install(
        agent: str, ref: str, name: str, *, force: bool
    ) -> gs.InstallResult:
        calls.append(agent)
        target = home / ".config" / "opencode" / "skills" / name / "SKILL.md"
        return gs.InstallResult(target_path=target, changed=True)

    monkeypatch.setattr(
        "agh.cli.main.global_skills_module.install_skill_global",
        fake_install,
    )

    result = CliRunner().invoke(
        cli_app, ["skill", "install", "acme/commenting@latest", "reviewer"]
    )

    assert result.exit_code == 0, result.stdout
    assert calls == ["opencode"]


def test_skill_install_prompt_saves_global_target(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("agh.cli.main._stdin_is_interactive", lambda: True)

    calls: list[str] = []

    def fake_install(
        agent: str, ref: str, name: str, *, force: bool
    ) -> gs.InstallResult:
        calls.append(agent)
        target = home / ".config" / "opencode" / "skills" / name / "SKILL.md"
        return gs.InstallResult(target_path=target, changed=True)

    monkeypatch.setattr(
        "agh.cli.main.global_skills_module.install_skill_global",
        fake_install,
    )

    result = CliRunner().invoke(
        cli_app,
        ["skill", "install", "acme/commenting@latest", "reviewer"],
        input="2\ny\n",
    )

    assert result.exit_code == 0, result.stdout
    assert calls == ["opencode"]
    assert read_global_skill_default_agent() == "opencode"


def test_skill_install_fails_in_non_tty_without_target(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("agh.cli.main._stdin_is_interactive", lambda: False)

    result = CliRunner().invoke(
        cli_app, ["skill", "install", "acme/commenting@latest", "reviewer"]
    )

    assert result.exit_code == 2, result.stdout
    assert "no target selected" in result.stdout.lower()
    assert "--target" in result.stdout


# --- skill command cleanup -------------------------------------------------


def test_skill_list_still_works(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agh.cli.main._api_request",
        lambda _method, _path: {
            "skills": [
                {
                    "skill_name": "reviewer",
                    "collection_name": "Acme",
                    "package_ref": "acme/commenting@latest",
                    "resolved_ref": "acme/commenting@1.2.0",
                    "description": "Review",
                }
            ]
        },
    )

    result = CliRunner().invoke(cli_app, ["skill", "list"])

    assert result.exit_code == 0, result.stdout
    assert "reviewer" in result.stdout


def test_skill_remove_is_not_supported() -> None:
    result = CliRunner().invoke(cli_app, ["skill", "remove", "reviewer"])
    assert result.exit_code == 2


def test_skill_installed_is_not_supported() -> None:
    result = CliRunner().invoke(cli_app, ["skill", "installed"])
    assert result.exit_code == 2


def test_skill_agent_is_not_supported() -> None:
    result = CliRunner().invoke(cli_app, ["skill", "agent"])
    assert result.exit_code == 2
