"""CLI user, token, and project command tests."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

from typer.testing import CliRunner

from agh.cli.main import app as cli_app


class _ApiHandler(BaseHTTPRequestHandler):
    requests: ClassVar[list[dict[str, Any]]] = []

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        self._handle()

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        self._handle()

    def do_PATCH(self) -> None:  # noqa: N802 - stdlib handler API
        self._handle()

    def do_PUT(self) -> None:  # noqa: N802 - stdlib handler API
        self._handle()

    def do_DELETE(self) -> None:  # noqa: N802 - stdlib handler API
        self._handle()

    def _handle(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b""
        body = json.loads(raw_body.decode("utf-8")) if raw_body else None
        type(self).requests.append(
            {
                "method": self.command,
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "body": body,
            }
        )
        status, payload = _response_for(self.command, self.path)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib API
        return


def _response_for(method: str, path: str) -> tuple[int, dict[str, Any]]:
    if (method, path) == ("GET", "/api/v1/users"):
        return 200, {
            "users": [
                {
                    "id": "usr_1",
                    "email": "dev@example.com",
                    "role": "member",
                    "active": True,
                    "token_hash": "hash-secret-value",
                }
            ]
        }
    if (method, path) == ("POST", "/api/v1/users"):
        return 201, {
            "user": {
                "id": "usr_2",
                "email": "new@example.com",
                "role": "member",
                "active": True,
            },
            "token": "issued-user-token",
        }
    if (method, path) == ("PATCH", "/api/v1/users/usr_2"):
        return 200, {
            "id": "usr_2",
            "email": "renamed@example.com",
            "role": "member",
            "active": False,
        }
    if (method, path) == ("DELETE", "/api/v1/users/usr_2"):
        return 200, {
            "id": "usr_2",
            "email": "renamed@example.com",
            "role": "member",
            "active": False,
        }
    if (method, path) == ("POST", "/api/v1/users/usr_2/token:rotate"):
        return 200, {"token": "rotated-token"}
    if (method, path) == ("POST", "/api/v1/users/usr_2/token:reset"):
        return 200, {"token": "reset-token"}
    if (method, path) == ("GET", "/api/v1/projects"):
        return 200, {
            "projects": [
                {
                    "id": "prj_1",
                    "name": "App",
                    "repo_url": "git@github.com:org/app.git",
                    "repo_url_normalized": "github.com/org/app",
                    "active": True,
                }
            ]
        }
    if (method, path) == ("POST", "/api/v1/projects"):
        return 201, {
            "id": "prj_2",
            "name": "API",
            "repo_url": "https://github.com/org/api.git",
            "repo_url_normalized": "github.com/org/api",
            "active": True,
        }
    if (method, path) == ("GET", "/api/v1/projects/prj_2"):
        return 200, {
            "id": "prj_2",
            "name": "API",
            "repo_url": "https://github.com/org/api.git",
            "repo_url_normalized": "github.com/org/api",
            "active": True,
        }
    if (method, path) == ("PATCH", "/api/v1/projects/prj_2"):
        return 200, {
            "id": "prj_2",
            "name": "API2",
            "repo_url": "git@github.com:org/api2.git",
            "repo_url_normalized": "github.com/org/api2",
            "active": False,
        }
    if (method, path) == ("DELETE", "/api/v1/projects/prj_2"):
        return 200, {
            "id": "prj_2",
            "name": "API2",
            "repo_url": "git@github.com:org/api2.git",
            "repo_url_normalized": "github.com/org/api2",
            "active": False,
        }
    if (method, path) == ("PUT", "/api/v1/projects/prj_2/members/usr_2"):
        return 200, {"project_id": "prj_2", "user_id": "usr_2"}
    if (method, path) == ("DELETE", "/api/v1/projects/prj_2/members/usr_2"):
        return 200, {"project_id": "prj_2", "user_id": "usr_2", "removed": True}
    if path == "/api/v1/forbidden":
        return 403, {"detail": "forbidden"}
    if path == "/api/v1/leaky-error":
        return 500, {
            "detail": {
                "token": "error-token-secret",
                "token_hash": "error-hash-secret",
            },
            "token": "top-level-error-token",
        }
    return 404, {"detail": f"unexpected {method} {path}"}


def _serve_api():
    class Handler(_ApiHandler):
        pass

    Handler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    return server, Handler, url


def _write_config(
    tmp_path: Path, url: str, token: str = "stored-secret-token"
) -> dict[str, str]:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f'instance_url = "{url}"\nemail = "owner@example.com"\ntoken = "{token}"\n',
        encoding="utf-8",
    )
    return {"AGH_CONFIG_FILE": str(config_path)}


def test_cli_user_token_project_commands_map_to_api_and_mask_stored_token(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    runner = CliRunner()
    commands = [
        (["user", "list"], "dev@example.com"),
        (
            ["user", "create", "new@example.com", "--role", "member"],
            "issued-user-token",
        ),
        (
            ["user", "update", "usr_2", "--email", "renamed@example.com", "--inactive"],
            "renamed@example.com",
        ),
        (["user", "delete", "usr_2"], "usr_2"),
        (["token", "rotate", "usr_2"], "rotated-token"),
        (["token", "reset", "usr_2"], "reset-token"),
        (["project", "list"], "github.com/org/app"),
        (
            [
                "project",
                "create",
                "API",
                "--repo-url",
                "https://github.com/org/api.git",
            ],
            "github.com/org/api",
        ),
        (["project", "get", "prj_2"], "prj_2"),
        (
            [
                "project",
                "update",
                "prj_2",
                "--name",
                "API2",
                "--repo-url",
                "git@github.com:org/api2.git",
                "--inactive",
            ],
            "github.com/org/api2",
        ),
        (["project", "member", "add", "prj_2", "usr_2"], "usr_2"),
        (["project", "member", "remove", "prj_2", "usr_2"], "removed"),
        (["project", "delete", "prj_2"], "prj_2"),
    ]
    try:
        for args, expected_output in commands:
            result = runner.invoke(cli_app, args, env=env)
            assert result.exit_code == 0, (args, result.stdout)
            assert expected_output in result.stdout
            assert "stored-secret-token" not in result.stdout
            assert "hash-secret-value" not in result.stdout
    finally:
        server.shutdown()

    assert {request["authorization"] for request in handler.requests} == {
        "Bearer stored-secret-token"
    }
    assert ("POST", "/api/v1/users") in {
        (request["method"], request["path"]) for request in handler.requests
    }
    assert {
        (request["method"], request["path"]): request["body"]
        for request in handler.requests
    }[("PATCH", "/api/v1/projects/prj_2")] == {
        "name": "API2",
        "repo_url": "git@github.com:org/api2.git",
        "active": False,
    }


def test_cli_read_commands_use_human_output(tmp_path: Path) -> None:
    server, _handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    runner = CliRunner()
    try:
        users = runner.invoke(cli_app, ["user", "list"], env=env)
        projects = runner.invoke(cli_app, ["project", "list"], env=env)
    finally:
        server.shutdown()

    assert users.exit_code == 0, users.stdout
    user_lines = users.stdout.splitlines()
    assert user_lines[0].split() == ["USER_ID", "EMAIL", "ROLE", "STATUS"]
    assert user_lines[1].split() == ["usr_1", "dev@example.com", "member", "active"]
    assert '"users"' not in users.stdout
    assert "token_hash" not in users.stdout

    assert projects.exit_code == 0, projects.stdout
    project_lines = projects.stdout.splitlines()
    assert project_lines[0].split() == ["PROJECT_ID", "NAME", "REPO", "STATUS"]
    assert project_lines[1].split() == [
        "prj_1",
        "App",
        "github.com/org/app",
        "active",
    ]
    assert '"projects"' not in projects.stdout


def test_cli_read_commands_show_empty_messages(monkeypatch) -> None:
    from agh.cli import main as cli_main

    responses = {
        "/users": {"users": []},
        "/projects": {"projects": []},
    }

    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda _method, path, **_kwargs: responses[path],
    )
    runner = CliRunner()

    users = runner.invoke(cli_app, ["user", "list"])
    projects = runner.invoke(cli_app, ["project", "list"])

    assert users.exit_code == 0, users.stdout
    assert users.stdout == "No users found.\n"
    assert projects.exit_code == 0, projects.stdout
    assert projects.stdout == "No projects found.\n"


def test_cli_admin_commands_convert_auth_failures_to_exit_code_4(
    tmp_path: Path, monkeypatch
) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(cli_main, "user_path", lambda _user_id: "/forbidden")
    server, _handler, url = _serve_api()
    try:
        result = CliRunner().invoke(
            cli_app,
            ["user", "delete", "usr_forbidden"],
            env=_write_config(tmp_path, url),
        )
    finally:
        server.shutdown()

    assert result.exit_code == 4
    assert "HTTP 403" in result.stdout
    assert "forbidden" in result.stdout


def test_cli_admin_commands_redact_token_fields_from_error_payloads(
    tmp_path: Path, monkeypatch
) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(cli_main, "project_path", lambda _project_id: "/leaky-error")
    server, _handler, url = _serve_api()
    try:
        result = CliRunner().invoke(
            cli_app,
            ["project", "get", "prj_leaky"],
            env=_write_config(tmp_path, url),
        )
    finally:
        server.shutdown()

    assert result.exit_code == 1
    assert "HTTP 500" in result.stdout
    assert "error-token-secret" not in result.stdout
    assert "error-hash-secret" not in result.stdout
    assert "top-level-error-token" not in result.stdout
    assert "****" in result.stdout


def test_cli_admin_help_preserves_main_manual_and_command_help() -> None:
    runner = CliRunner()

    assert runner.invoke(cli_app, ["user"]).stdout == runner.invoke(cli_app, []).stdout
    assert (
        runner.invoke(cli_app, ["project", "wrong"]).stdout
        == runner.invoke(cli_app, []).stdout
    )

    user_group_help = runner.invoke(cli_app, ["user", "--help"])
    project_group_help = runner.invoke(cli_app, ["project", "--help"])
    member_group_help = runner.invoke(cli_app, ["project", "member", "--help"])
    user_help = runner.invoke(cli_app, ["user", "create", "--help"])
    project_help = runner.invoke(cli_app, ["project", "create", "--help"])
    member_help = runner.invoke(cli_app, ["project", "member", "add", "--help"])

    assert user_group_help.exit_code == 0
    assert "create" in user_group_help.stdout
    assert "delete" in user_group_help.stdout
    assert project_group_help.exit_code == 0
    assert "member" in project_group_help.stdout
    assert "create" in project_group_help.stdout
    assert member_group_help.exit_code == 0
    assert "add" in member_group_help.stdout
    assert "remove" in member_group_help.stdout
    assert user_help.exit_code == 0
    assert "new@example.com" not in user_help.stdout
    assert "--role" in user_help.stdout
    assert project_help.exit_code == 0
    assert "--repo-url" in project_help.stdout
    assert member_help.exit_code == 0
    assert "PROJECT_ID" in member_help.stdout or "project_id" in member_help.stdout
