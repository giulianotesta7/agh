"""CLI workspace link tests."""

from __future__ import annotations

import json
import subprocess
import threading
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

from typer.testing import CliRunner

from agh.cli.main import app as cli_app


class _ProjectsHandler(BaseHTTPRequestHandler):
    projects: ClassVar[list[dict[str, Any]]] = []
    status_code: ClassVar[int] = 200
    requests: ClassVar[list[dict[str, str | None]]] = []

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        type(self).requests.append(
            {"path": self.path, "authorization": self.headers.get("Authorization")}
        )
        if self.path != "/api/v1/projects":
            self.send_response(404)
            payload: dict[str, Any] = {"detail": "not found"}
        else:
            self.send_response(type(self).status_code)
            payload = {"projects": type(self).projects}
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib API
        return


def _serve_projects(projects: list[dict[str, Any]], *, status_code: int = 200):
    class Handler(_ProjectsHandler):
        pass

    Handler.projects = projects
    Handler.status_code = status_code
    Handler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, Handler, f"http://127.0.0.1:{server.server_port}"


def _write_config(
    tmp_path: Path, url: str, token: str = "link-secret-token"
) -> dict[str, str]:
    path = tmp_path / "config.toml"
    path.write_text(
        f'instance_url = "{url}"\nemail = "dev@example.com"\ntoken = "{token}"\n',
        encoding="utf-8",
    )
    return {"AGH_CONFIG_FILE": str(path)}


def _git_repo(tmp_path: Path, *, remotes: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    for name, url in remotes.items():
        subprocess.run(["git", "remote", "add", name, url], cwd=repo, check=True)
    return repo


def _linked_project_toml(repo: Path) -> dict[str, Any]:
    return tomllib.loads((repo / ".agh" / "project.toml").read_text(encoding="utf-8"))


def test_link_links_default_remote_and_uses_saved_config_auth(
    tmp_path: Path, monkeypatch
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
    assert "Project file: .agh/project.toml" in result.stdout
    assert "Remote: github.com/org/app" in result.stdout
    assert f"Server: {url}" in result.stdout
    assert '"project_id"' not in result.stdout
    assert '"replaced"' not in result.stdout
    assert "link-secret-token" not in result.stdout
    assert handler.requests == [
        {"path": "/api/v1/projects", "authorization": "Bearer link-secret-token"}
    ]
    link = _linked_project_toml(repo)
    assert link["instance_url"] == url
    assert link["project_id"] == "prj_match"
    assert link["repo_url_normalized"] == "github.com/org/app"
    assert "synced_at" in link


def test_link_supports_non_default_remote(tmp_path: Path, monkeypatch) -> None:
    repo = _git_repo(
        tmp_path,
        remotes={
            "origin": "git@github.com:org/nope.git",
            "upstream": "https://gitlab.com/Acme/API.GIT",
        },
    )
    server, _handler, url = _serve_projects(
        [
            {
                "id": "prj_upstream",
                "name": "API",
                "repo_url_normalized": "gitlab.com/acme/api",
                "active": True,
            }
        ]
    )
    monkeypatch.chdir(repo)
    try:
        result = CliRunner().invoke(
            cli_app,
            ["link", "--remote", "upstream"],
            env=_write_config(tmp_path, url),
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert _linked_project_toml(repo)["project_id"] == "prj_upstream"


def test_link_refuses_symlinked_agh_directory(tmp_path: Path, monkeypatch) -> None:
    repo = _git_repo(tmp_path, remotes={"origin": "git@github.com:org/app.git"})
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / ".agh").symlink_to(outside, target_is_directory=True)
    server, _handler, url = _serve_projects(
        [
            {
                "id": "prj_match",
                "name": "App",
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

    assert result.exit_code == 5
    assert "symlinked AGH directory" in result.stdout
    assert not (outside / "project.toml").exists()


def test_link_refuses_existing_link_without_force_and_force_replaces_link_only(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _git_repo(tmp_path, remotes={"origin": "git@github.com:org/app.git"})
    agh_dir = repo / ".agh"
    agh_dir.mkdir()
    (agh_dir / "project.toml").write_text(
        'instance_url = "http://old"\nproject_id = "prj_old"\nrepo_url_normalized = "old/repo"\nsynced_at = "old"\n',
        encoding="utf-8",
    )
    (agh_dir / "lock.toml").write_text("version = 1\n", encoding="utf-8")
    server, _handler, url = _serve_projects(
        [
            {
                "id": "prj_new",
                "name": "App",
                "repo_url_normalized": "github.com/org/app",
                "active": True,
            }
        ]
    )
    monkeypatch.chdir(repo)
    try:
        first = CliRunner().invoke(cli_app, ["link"], env=_write_config(tmp_path, url))
        forced = CliRunner().invoke(
            cli_app, ["link", "--force"], env=_write_config(tmp_path, url)
        )
    finally:
        server.shutdown()

    assert first.exit_code == 5
    assert "already exists" in first.stdout
    assert forced.exit_code == 0, forced.stdout
    assert "Updated repo link to App (prj_new)." in forced.stdout
    assert '"project_id"' not in forced.stdout
    assert '"replaced"' not in forced.stdout
    assert _linked_project_toml(repo)["project_id"] == "prj_new"
    assert (agh_dir / "lock.toml").read_text(encoding="utf-8") == "version = 1\n"


def test_link_fails_for_missing_remote_and_no_matching_project(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _git_repo(tmp_path, remotes={"origin": "git@github.com:org/app.git"})
    server, _handler, url = _serve_projects(
        [
            {
                "id": "prj_other",
                "name": "Other",
                "repo_url_normalized": "github.com/org/other",
                "active": True,
            }
        ]
    )
    monkeypatch.chdir(repo)
    try:
        missing_remote = CliRunner().invoke(
            cli_app, ["link", "--remote", "missing"], env=_write_config(tmp_path, url)
        )
        no_match = CliRunner().invoke(
            cli_app, ["link"], env=_write_config(tmp_path, url)
        )
    finally:
        server.shutdown()

    assert missing_remote.exit_code == 5
    assert "failed to read git remote" in missing_remote.stdout
    assert no_match.exit_code == 5
    assert "no accessible active AGH project matches" in no_match.stdout
    assert not (repo / ".agh" / "project.toml").exists()


def test_link_remote_lookup_timeout_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    repo = _git_repo(tmp_path, remotes={"origin": "git@github.com:org/app.git"})
    server, handler, url = _serve_projects([])
    monkeypatch.chdir(repo)

    def timeout_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(
            cmd=["git", "remote", "get-url", "origin"], timeout=5
        )

    monkeypatch.setattr("agh.cli.workspace_sync.subprocess.run", timeout_run)
    try:
        result = CliRunner().invoke(cli_app, ["link"], env=_write_config(tmp_path, url))
    finally:
        server.shutdown()

    assert result.exit_code == 5
    assert "timed out after 5 seconds" in result.stdout
    assert "git remote 'origin'" in result.stdout
    assert handler.requests == []
    assert not (repo / ".agh" / "project.toml").exists()


def test_link_help_has_no_manual_project_override() -> None:
    result = CliRunner().invoke(cli_app, ["link", "--help"])

    assert result.exit_code == 0
    assert "--remote" in result.stdout
    assert "--force" in result.stdout
    assert "--project" not in result.stdout


def test_link_corrupt_config_shows_recovery_guidance(
    tmp_path: Path, monkeypatch
) -> None:
    """Corrupt config surfaces recovery guidance, not a raw error/traceback.

    Regression for the Judgment Day finding that link/pull failed without the
    shared corrupt-config recovery guidance. Config is loaded before the git
    remote lookup, so a git repo is not required to exercise this path.
    """
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        'instance_url = "http://agh.example\nkey = "oops\n', encoding="utf-8"
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    result = CliRunner().invoke(
        cli_app, ["link"], env={"AGH_CONFIG_FILE": str(config_path)}
    )

    assert result.exit_code != 0
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert str(config_path) in result.stdout
    assert "invalid" in result.stdout.lower()
    assert "config set" in result.stdout.lower()
    # corrupt file left intact (not overwritten)
    assert "oops" in config_path.read_text("utf-8")
