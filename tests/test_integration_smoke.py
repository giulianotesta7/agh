"""End-to-end integration smoke coverage for AGH server and CLI flows."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from agh.cli.main import app as cli_app


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _request_json(
    base_url: str,
    method: str,
    path: str,
    *,
    token: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {**_auth(token), "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base_url}{path}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 - local test server
        return response.status, json.loads(response.read().decode("utf-8"))


def _pack_files() -> dict[str, str]:
    return {
        "agh.pack.toml": (
            'domain = "acme"\n'
            'name = "onboarding"\n'
            'version = "1.0.0"\n'
            'description = "Team onboarding"\n'
            'tags = ["team"]\n'
        ),
        "instructions/AGENTS.md": "# OpenCode\nUse AGH guidance.\n",
        "instructions/CLAUDE.md": "# Claude\nUse AGH guidance.\n",
        "skills/reviewer/SKILL.md": "# Reviewer\nReview carefully.\n",
    }


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def _live_agh_server(tmp_path: Path, monkeypatch) -> Iterator[tuple[str, str]]:
    data_dir = tmp_path / "server-data"
    port = _free_port()
    env = os.environ.copy()
    env.update(
        {
            "AGH_DATA_DIR": str(data_dir),
            "AGH_BOOTSTRAP_OWNER_EMAIL": "owner@example.com",
        }
    )
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "agh.server.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "critical",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_health(base_url, process)
        token = (
            (data_dir / "secrets" / "initial_owner_token")
            .read_text(encoding="utf-8")
            .strip()
        )
        yield base_url, token
    finally:
        process.terminate()
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=10)


def _wait_for_health(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"AGH test server exited before startup\nstdout={stdout}\nstderr={stderr}"
            )
        try:
            with urllib.request.urlopen(  # noqa: S310 - local test server
                f"{base_url}/api/v1/health", timeout=0.2
            ) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.05)
    raise RuntimeError("AGH test server did not start")


def _write_cli_config(tmp_path: Path, *, base_url: str, token: str) -> dict[str, str]:
    config_path = tmp_path / "cli-config.toml"
    config_path.write_text(
        f'instance_url = "{base_url}"\nemail = "owner@example.com"\ntoken = "{token}"\n',
        encoding="utf-8",
    )
    return {"AGH_CONFIG_FILE": str(config_path)}


def _git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "workspace"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:acme/app.git"],
        cwd=repo,
        check=True,
    )
    return repo


def test_server_to_cli_sync_and_pull_smoke(tmp_path: Path, monkeypatch) -> None:
    with _live_agh_server(tmp_path, monkeypatch) as (base_url, owner_token):
        status, project = _request_json(
            base_url,
            "POST",
            "/api/v1/projects",
            token=owner_token,
            body={"name": "App", "repo_url": "git@github.com:acme/app.git"},
        )
        assert status == 201
        assert project["repo_url_normalized"] == "github.com/acme/app"

        status, pack = _request_json(
            base_url,
            "POST",
            "/api/v1/packs",
            token=owner_token,
            body={"files": _pack_files()},
        )
        assert status == 201
        assert pack["id"] == "acme/onboarding@1.0.0"

        status, assignment = _request_json(
            base_url,
            "POST",
            f"/api/v1/projects/{project['id']}/packs",
            token=owner_token,
            body={"pack_ref": "acme/onboarding@latest", "position": 0},
        )
        assert status == 201
        assert assignment["resolved_ref"] == "acme/onboarding@1.0.0"

        status, manifest = _request_json(
            base_url,
            "GET",
            f"/api/v1/projects/{project['id']}/pull-manifest",
            token=owner_token,
        )
        assert status == 200
        assert manifest["project"]["id"] == project["id"]
        assert manifest["packs"][0]["id"] == "acme/onboarding@1.0.0"
        assert {
            artifact["target_path"] for artifact in manifest["packs"][0]["artifacts"]
        } == {
            "AGENTS.md",
            "CLAUDE.md",
            ".claude/skills/reviewer/SKILL.md",
            ".opencode/skills/reviewer/SKILL.md",
        }

        repo = _git_repo(tmp_path)
        env = _write_cli_config(tmp_path, base_url=base_url, token=owner_token)
        runner = CliRunner()
        monkeypatch.chdir(repo)

        sync = runner.invoke(cli_app, ["sync"], env=env)
        assert sync.exit_code == 0, sync.stdout
        assert project["id"] in sync.stdout
        project_link = tomllib.loads(
            (repo / ".agh" / "project.toml").read_text(encoding="utf-8")
        )
        assert project_link["instance_url"] == base_url
        assert project_link["project_id"] == project["id"]
        assert project_link["repo_url_normalized"] == "github.com/acme/app"

        dry_run = runner.invoke(cli_app, ["pull", "--dry-run"], env=env)
        assert dry_run.exit_code == 0, dry_run.stdout
        assert '"dry_run": true' in dry_run.stdout
        assert not (repo / "AGENTS.md").exists()
        assert not (repo / "CLAUDE.md").exists()
        assert not (repo / ".agh" / "packs").exists()
        assert not (repo / ".agh" / "lock.toml").exists()

        pull = runner.invoke(cli_app, ["pull"], env=env)
        assert pull.exit_code == 0, pull.stdout
        assert '"dry_run": false' in pull.stdout
        assert "Hint: add .agh/packs/ to .gitignore" in pull.stdout

        agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
        claude = (repo / "CLAUDE.md").read_text(encoding="utf-8")
        assert "<!-- AGH-BEGIN" in agents
        assert "# OpenCode" in agents
        assert "<!-- AGH-BEGIN" in claude
        assert "# Claude" in claude
        assert (
            repo
            / ".agh"
            / "packs"
            / "acme"
            / "onboarding"
            / "1.0.0"
            / "instructions"
            / "AGENTS.md"
        ).read_text(encoding="utf-8") == "# OpenCode\nUse AGH guidance.\n"
        assert (repo / ".claude" / "skills" / "reviewer" / "SKILL.md").read_text(
            encoding="utf-8"
        ) == "# Reviewer\nReview carefully.\n"
        assert (repo / ".opencode" / "skills" / "reviewer" / "SKILL.md").read_text(
            encoding="utf-8"
        ) == "# Reviewer\nReview carefully.\n"

        lock = tomllib.loads((repo / ".agh" / "lock.toml").read_text(encoding="utf-8"))
        assert lock["project"]["id"] == project["id"]
        assert [pack["ref"] for pack in lock["packs"]] == ["acme/onboarding@1.0.0"]
        sources = {artifact["source"] for artifact in lock["artifacts"]}
        assert all(source.startswith(".agh/packs/") for source in sources)
        assert any(
            artifact["mode"] in {"symlink", "copy"} for artifact in lock["artifacts"]
        )
