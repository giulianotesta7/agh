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
        status, payload = _response_for(self.command, self.path, body)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib API
        return


def _response_for(
    method: str, path: str, body: dict[str, Any] | None = None
) -> tuple[int, dict[str, Any]]:
    if (method, path) == ("POST", "/api/v1/users/missing-token"):
        return 200, {"user": {"id": "usr_missing", "email": "missing@example.com"}}
    if (method, path) == ("POST", "/api/v1/users/usr_2/token:missing"):
        return 200, {}
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
    if (method, path) == ("GET", "/api/v1/users/by-email/member%40example.com"):
        return 200, {"id": "usr_2", "email": "member@example.com"}
    if (method, path) == ("POST", "/api/v1/users"):
        return 201, {
            "user": {
                "id": "usr_2",
                "email": "new@example.com",
                "role": "member",
                "active": True,
            },
            "token": "issued-user-token",
            "token_hash": "issued-hash-secret",
        }
    if (method, path) == ("GET", "/api/v1/users/usr_2"):
        return 200, {
            "id": "usr_2",
            "email": "renamed@example.com",
            "role": "member",
            "active": True,
        }
    if (method, path) == ("PATCH", "/api/v1/users/usr_2"):
        return 200, {
            "id": "usr_2",
            "email": "renamed@example.com",
            "role": "member",
            "active": bool(body.get("active")) if body and "active" in body else False,
        }
    if (method, path) == ("DELETE", "/api/v1/users/usr_2"):
        return 200, {
            "id": "usr_2",
            "email": "renamed@example.com",
            "role": "member",
            "active": False,
        }
    if (method, path) == ("POST", "/api/v1/users/usr_2/token:rotate"):
        return 200, {"token": "rotated-token", "token_hash": "rotated-hash-secret"}
    if (method, path) == ("POST", "/api/v1/users/usr_2/token:reset"):
        return 200, {"token": "reset-token", "token_hash": "reset-hash-secret"}
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
            "active": bool(body.get("active")) if body and "active" in body else False,
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
    if (method, path) == ("GET", "/api/v1/projects/prj_2/members"):
        return 200, {
            "members": [{"id": "usr_2", "email": "member@example.com", "active": True}]
        }
    if (method, path) == ("GET", "/api/v1/collections"):
        return 200, {
            "collections": [
                {
                    "id": "col_0000000000000001",
                    "name": "Team Skills",
                    "description": "Shared skills",
                    "active": True,
                }
            ]
        }
    if (method, path) == ("POST", "/api/v1/collections"):
        return 201, {
            "id": "col_0000000000000002",
            "name": "Ops Skills",
            "description": "ops",
            "active": True,
        }
    if (method, path) == ("GET", "/api/v1/collections/col_0000000000000002"):
        return 200, {
            "id": "col_0000000000000002",
            "name": "Ops Skills",
            "description": "ops",
            "active": True,
        }
    if (method, path) == ("PATCH", "/api/v1/collections/col_0000000000000002"):
        return 200, {
            "id": "col_0000000000000002",
            "name": "Ops Skills2",
            "description": "ops2",
            "active": bool(body.get("active")) if body and "active" in body else False,
        }
    if (method, path) == ("DELETE", "/api/v1/collections/col_0000000000000002"):
        return 200, {
            "id": "col_0000000000000002",
            "name": "Ops Skills2",
            "description": "ops2",
            "active": False,
        }
    if (method, path) == ("GET", "/api/v1/collections/col_0000000000000002/packages"):
        return 200, {
            "collection_packages": [
                {
                    "id": "casn_1",
                    "collection_id": "col_0000000000000002",
                    "package_id": "pkg_1",
                    "package_ref": "acme/reviewer@latest",
                    "resolved_ref": "acme/reviewer@1.0.0",
                    "domain": "acme",
                    "name": "reviewer",
                    "version_ref": "latest",
                    "resolved_version": "1.0.0",
                    "position": 1,
                    "active": True,
                }
            ]
        }
    if (method, path) == ("POST", "/api/v1/collections/col_0000000000000002/packages"):
        return 201, {
            "id": "casn_1",
            "collection_id": "col_0000000000000002",
            "package_ref": "acme/reviewer@latest",
            "resolved_ref": "acme/reviewer@1.0.0",
            "position": 5,
            "active": True,
        }
    if (method, path) == (
        "PATCH",
        "/api/v1/collections/col_0000000000000002/packages/casn_1",
    ):
        return 200, {
            "id": "casn_1",
            "collection_id": "col_0000000000000002",
            "package_ref": "acme/reviewer@1.0.0",
            "resolved_ref": "acme/reviewer@1.0.0",
            "position": 7,
            "active": False,
        }
    if (method, path) == (
        "DELETE",
        "/api/v1/collections/col_0000000000000002/packages/casn_1",
    ):
        return 200, {
            "id": "casn_1",
            "collection_id": "col_0000000000000002",
            "active": False,
        }
    if (method, path) == ("POST", "/api/v1/collections/col_0000000000000003/packages"):
        # Server rejects an instruction-bearing package as not skill-only.
        return 400, {
            "detail": "package contains instructions and cannot be used as a collection skill"
        }
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


def test_cli_admin_unknown_subcommands_exit_2_with_local_help() -> None:
    runner = CliRunner()
    root_help = runner.invoke(cli_app, []).stdout

    cases = {
        ("user", "wrong-command"): "Manage AGH users.",
        ("user", "token", "wrong-command"): "Rotate user API tokens.",
        ("project", "wrong-command"): "Manage AGH projects.",
        ("collection", "wrong-command"): "Manage AGH collections.",
    }
    for args, local_marker in cases.items():
        result = runner.invoke(cli_app, list(args))

        assert result.exit_code == 2, args
        assert local_marker in result.stdout, (args, result.stdout)
        # local group help must never leak the root command map
        assert result.stdout != root_help, args

    member_unknown = runner.invoke(cli_app, ["project", "member", "wrong-command"])
    assert member_unknown.exit_code == 2
    assert "developer membership" in member_unknown.stdout.lower()
    assert member_unknown.stdout != root_help


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
        (["user", "describe", "usr_2"], "renamed@example.com"),
        (
            ["user", "update", "usr_2", "--email", "renamed@example.com", "--inactive"],
            "renamed@example.com",
        ),
        (["user", "deactivate", "usr_2"], "usr_2"),
        (["user", "activate", "usr_2"], "Status: active"),
        (["user", "token", "rotate", "usr_2"], "rotated-token"),
        (["project", "list"], "github.com/org/app"),
        (
            [
                "project",
                "create",
                "API",
                "--git-url",
                "https://github.com/org/api.git",
            ],
            "github.com/org/api",
        ),
        (["project", "describe", "prj_2"], "prj_2"),
        (
            [
                "project",
                "update",
                "prj_2",
                "--name",
                "API2",
                "--git-url",
                "git@github.com:org/api2.git",
                "--inactive",
            ],
            "github.com/org/api2",
        ),
        (["project", "member", "add", "prj_2", "usr_2"], "Added user usr_2"),
        (["project", "member", "list", "prj_2"], "member@example.com"),
        (["project", "member", "remove", "prj_2", "usr_2"], "Removed user usr_2"),
        (["project", "deactivate", "prj_2"], "prj_2"),
        (["project", "activate", "prj_2"], "Status: active"),
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
    project_patch_bodies = [
        request["body"]
        for request in handler.requests
        if (request["method"], request["path"]) == ("PATCH", "/api/v1/projects/prj_2")
    ]
    assert {
        "name": "API2",
        "repo_url": "git@github.com:org/api2.git",
        "active": False,
    } in project_patch_bodies
    assert {"active": True} in project_patch_bodies


def test_cli_user_token_mutations_use_human_output_and_preserve_one_time_tokens(
    tmp_path: Path,
) -> None:
    server, _handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    runner = CliRunner()
    try:
        created = runner.invoke(
            cli_app,
            ["user", "create", "new@example.com", "--role", "member"],
            env=env,
        )
        updated = runner.invoke(
            cli_app,
            ["user", "update", "usr_2", "--email", "renamed@example.com", "--inactive"],
            env=env,
        )
        deactivated = runner.invoke(cli_app, ["user", "deactivate", "usr_2"], env=env)
        activated = runner.invoke(cli_app, ["user", "activate", "usr_2"], env=env)
        rotated = runner.invoke(cli_app, ["user", "token", "rotate", "usr_2"], env=env)
    finally:
        server.shutdown()

    assert created.exit_code == 0, created.stdout
    assert created.stdout == (
        "Created user new@example.com (usr_2).\n"
        "Role: member\n"
        "Status: active\n"
        "Token: issued-user-token\n"
        "Store this token now. AGH will not show it again.\n"
    )
    assert "issued-user-token" in created.stdout

    assert updated.exit_code == 0, updated.stdout
    assert updated.stdout == (
        "Updated user renamed@example.com (usr_2).\nRole: member\nStatus: inactive\n"
    )

    assert deactivated.exit_code == 0, deactivated.stdout
    assert deactivated.stdout == "Deactivated user renamed@example.com (usr_2).\n"

    assert activated.exit_code == 0, activated.stdout
    assert activated.stdout == (
        "Activated user renamed@example.com (usr_2).\nRole: member\nStatus: active\n"
    )

    assert rotated.exit_code == 0, rotated.stdout
    assert rotated.stdout == (
        "Rotated token for user usr_2.\n"
        "Token: rotated-token\n"
        "Store this token now. AGH will not show it again.\n"
    )

    combined = "".join(
        [
            created.stdout,
            updated.stdout,
            deactivated.stdout,
            activated.stdout,
            rotated.stdout,
        ]
    )
    assert "stored-secret-token" not in combined
    assert "token_hash" not in combined
    assert "issued-hash-secret" not in combined
    assert "rotated-hash-secret" not in combined
    for json_field in ['"user"', '"token"', '"email"', '"role"', '"active"']:
        assert json_field not in combined


def test_cli_token_flows_fail_if_plaintext_token_is_missing(monkeypatch) -> None:
    from agh.cli import main as cli_main

    responses = {
        "/users": {"user": {"id": "usr_missing", "email": "missing@example.com"}},
        "/users/usr_2/token:rotate": {},
    }
    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda _method, path, **_kwargs: responses[path],
    )
    runner = CliRunner()

    created = runner.invoke(cli_app, ["user", "create", "missing@example.com"])
    rotated = runner.invoke(cli_app, ["user", "token", "rotate", "usr_2"])

    for result in [created, rotated]:
        assert result.exit_code == 1, result.stdout
        assert (
            "server response did not include the one-time plaintext token"
            in result.stdout
        )
        assert "Store this token now" not in result.stdout


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


def test_cli_project_mutation_commands_use_human_output(tmp_path: Path) -> None:
    server, _handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    runner = CliRunner()
    try:
        created = runner.invoke(
            cli_app,
            [
                "project",
                "create",
                "API",
                "--git-url",
                "https://github.com/org/api.git",
            ],
            env=env,
        )
        updated = runner.invoke(
            cli_app,
            [
                "project",
                "update",
                "prj_2",
                "--name",
                "API2",
                "--git-url",
                "git@github.com:org/api2.git",
                "--inactive",
            ],
            env=env,
        )
        deactivated = runner.invoke(
            cli_app, ["project", "deactivate", "prj_2"], env=env
        )
        activated = runner.invoke(cli_app, ["project", "activate", "prj_2"], env=env)
        member_added = runner.invoke(
            cli_app, ["project", "member", "add", "prj_2", "usr_2"], env=env
        )
        member_listed = runner.invoke(
            cli_app, ["project", "member", "list", "prj_2"], env=env
        )
        member_removed = runner.invoke(
            cli_app, ["project", "member", "remove", "prj_2", "usr_2"], env=env
        )
        project_get = runner.invoke(cli_app, ["project", "describe", "prj_2"], env=env)
    finally:
        server.shutdown()

    assert created.exit_code == 0, created.stdout
    assert created.stdout == (
        "Created project API (prj_2).\nRepo: github.com/org/api\nStatus: active\n"
    )
    assert '"repo_url_normalized"' not in created.stdout

    assert updated.exit_code == 0, updated.stdout
    assert updated.stdout == (
        "Updated project API2 (prj_2).\nRepo: github.com/org/api2\nStatus: inactive\n"
    )

    assert deactivated.exit_code == 0, deactivated.stdout
    assert deactivated.stdout == "Deactivated project API2 (prj_2).\n"

    assert activated.exit_code == 0, activated.stdout
    assert activated.stdout == (
        "Activated project API2 (prj_2).\nRepo: github.com/org/api2\nStatus: active\n"
    )

    assert member_added.exit_code == 0, member_added.stdout
    assert member_added.stdout == "Added user usr_2 to project prj_2.\n"

    assert member_listed.exit_code == 0, member_listed.stdout
    member_lines = member_listed.stdout.splitlines()
    assert member_lines[0].split() == ["USER_ID", "EMAIL", "STATUS"]
    assert member_lines[1].split() == ["usr_2", "member@example.com", "active"]

    assert member_removed.exit_code == 0, member_removed.stdout
    assert member_removed.stdout == "Removed user usr_2 from project prj_2.\n"

    assert project_get.exit_code == 0, project_get.stdout
    assert project_get.stdout == (
        "Project: API\nProject ID: prj_2\nRepo: github.com/org/api\nStatus: active\n"
    )
    assert '"repo_url_normalized"' not in project_get.stdout


def test_cli_project_refs_resolve_names_and_keep_numeric_refs_as_ids(
    monkeypatch,
) -> None:
    from agh.cli import main as cli_main

    calls: list[tuple[str, str]] = []

    def fake_api(method: str, path: str, **_kwargs):
        calls.append((method, path))
        if path == "/projects/by-name/API":
            return {"id": "prj_2", "name": "API"}
        if path in {"/projects/prj_2", "/projects/12345"}:
            return {"id": path.rsplit("/", 1)[1], "name": "API", "active": True}
        if path == "/projects/prj_2/members/usr_2":
            return {"project_id": "prj_2", "user_id": "usr_2"}
        raise AssertionError(path)

    monkeypatch.setattr(cli_main, "_api_request", fake_api)
    runner = CliRunner()
    by_name = runner.invoke(cli_app, ["project", "describe", "API"])
    member_by_name = runner.invoke(
        cli_app, ["project", "member", "add", "API", "usr_2"]
    )
    numeric = runner.invoke(cli_app, ["project", "describe", "12345"])

    assert by_name.exit_code == 0, by_name.stdout
    assert "Project ID: prj_2" in by_name.stdout
    assert member_by_name.exit_code == 0, member_by_name.stdout
    assert member_by_name.stdout == "Added user usr_2 to project prj_2.\n"
    assert numeric.exit_code == 0, numeric.stdout
    assert "Project ID: 12345" in numeric.stdout

    assert calls.count(("GET", "/projects/by-name/API")) == 2
    assert ("GET", "/projects/12345") in calls
    assert ("GET", "/projects/by-name/12345") not in calls


def test_cli_user_refs_resolve_emails_and_keep_user_ids(monkeypatch) -> None:
    from agh.cli import main as cli_main

    calls: list[tuple[str, str]] = []

    def fake_api(method: str, path: str, **_kwargs):
        calls.append((method, path))
        if path == "/users/by-email/member%40example.com":
            return {"id": "usr_2", "email": "member@example.com"}
        if path == "/users/usr_2":
            return {
                "id": "usr_2",
                "email": "member@example.com",
                "role": "member",
                "active": True,
            }
        if path == "/users/usr_2/token:rotate":
            return {"token": "rotated-token"}
        if path == "/projects/prj_2/members/usr_2":
            return {"project_id": "prj_2", "user_id": "usr_2"}
        raise AssertionError(path)

    monkeypatch.setattr(cli_main, "_api_request", fake_api)
    runner = CliRunner()
    by_email = runner.invoke(cli_app, ["user", "describe", "member@example.com"])
    by_id = runner.invoke(cli_app, ["user", "describe", "usr_2"])
    token_by_email = runner.invoke(
        cli_app, ["user", "token", "rotate", "member@example.com"]
    )
    member_by_email = runner.invoke(
        cli_app, ["project", "member", "add", "prj_2", "member@example.com"]
    )

    assert by_email.exit_code == 0, by_email.stdout
    assert "User ID: usr_2" in by_email.stdout
    assert by_id.exit_code == 0, by_id.stdout
    assert token_by_email.exit_code == 0, token_by_email.stdout
    assert token_by_email.stdout.startswith("Rotated token for user usr_2.")
    assert member_by_email.exit_code == 0, member_by_email.stdout
    assert member_by_email.stdout == "Added user usr_2 to project prj_2.\n"

    assert calls.count(("GET", "/users/by-email/member%40example.com")) == 3
    assert calls.count(("GET", "/users/usr_2")) == 2


def test_cli_user_refs_prefer_valid_usr_prefixed_email_over_id(monkeypatch) -> None:
    from agh.cli import main as cli_main

    calls: list[tuple[str, str]] = []

    def fake_api(method: str, path: str, **_kwargs):
        calls.append((method, path))
        if path == "/users/by-email/usr_jane%40example.com":
            return {"id": "usr_2", "email": "usr_jane@example.com"}
        if path == "/users/usr_2":
            return {
                "id": "usr_2",
                "email": "usr_jane@example.com",
                "role": "member",
                "active": True,
            }
        raise AssertionError(path)

    monkeypatch.setattr(cli_main, "_api_request", fake_api)

    result = CliRunner().invoke(cli_app, ["user", "describe", "usr_jane@example.com"])

    assert result.exit_code == 0, result.stdout
    assert "User ID: usr_2" in result.stdout
    assert calls == [
        ("GET", "/users/by-email/usr_jane%40example.com"),
        ("GET", "/users/usr_2"),
    ]


def test_cli_user_email_refs_cover_mutation_token_and_member_remove(
    monkeypatch,
) -> None:
    from agh.cli import main as cli_main

    calls: list[tuple[str, str]] = []

    def fake_api(method: str, path: str, **_kwargs):
        calls.append((method, path))
        if path == "/users/by-email/member%40example.com":
            return {"id": "usr_2", "email": "member@example.com"}
        if path == "/users/usr_2":
            return {
                "id": "usr_2",
                "email": "renamed@example.com",
                "role": "member",
                "active": True,
            }
        if path == "/projects/prj_2/members/usr_2":
            return {"project_id": "prj_2", "user_id": "usr_2"}
        raise AssertionError(path)

    monkeypatch.setattr(cli_main, "_api_request", fake_api)
    runner = CliRunner()
    updated = runner.invoke(
        cli_app,
        ["user", "update", "member@example.com", "--email", "renamed@example.com"],
    )
    deleted = runner.invoke(cli_app, ["user", "deactivate", "member@example.com"])
    member_removed = runner.invoke(
        cli_app, ["project", "member", "remove", "prj_2", "member@example.com"]
    )

    assert updated.exit_code == 0, updated.stdout
    assert updated.stdout == (
        "Updated user renamed@example.com (usr_2).\nRole: member\nStatus: active\n"
    )
    assert deleted.exit_code == 0, deleted.stdout
    assert deleted.stdout == "Deactivated user renamed@example.com (usr_2).\n"
    assert member_removed.exit_code == 0, member_removed.stdout
    assert member_removed.stdout == "Removed user usr_2 from project prj_2.\n"

    assert calls.count(("GET", "/users/by-email/member%40example.com")) == 3
    assert ("PATCH", "/users/usr_2") in calls
    assert ("DELETE", "/users/usr_2") in calls
    assert ("DELETE", "/projects/prj_2/members/usr_2") in calls


def test_cli_user_ref_validation_rejects_malformed_email_without_api_call(
    monkeypatch,
) -> None:
    from agh.cli import main as cli_main

    calls = []
    monkeypatch.setattr(
        cli_main, "_api_request", lambda *args, **_kwargs: calls.append(args)
    )

    result = CliRunner().invoke(cli_app, ["user", "describe", "not-an-email"])

    assert result.exit_code == 2
    assert "USER_REF must be a user id" in result.stdout
    assert calls == []


def test_cli_project_name_validation_rejects_digit_only_names_without_api_call(
    monkeypatch,
) -> None:
    from agh.cli import main as cli_main

    calls = []
    monkeypatch.setattr(
        cli_main, "_api_request", lambda *args, **kwargs: calls.append(args)
    )
    runner = CliRunner()
    created = runner.invoke(
        cli_app,
        ["project", "create", "12345", "--git-url", "https://github.com/org/x.git"],
    )
    updated = runner.invoke(cli_app, ["project", "update", "prj_2", "--name", "12345"])

    assert created.exit_code == 2, created.stdout
    assert "project name cannot contain only digits" in created.stdout
    assert updated.exit_code == 2, updated.stdout
    assert "project name cannot contain only digits" in updated.stdout
    assert calls == []


def test_cli_read_commands_show_empty_messages(monkeypatch) -> None:
    from agh.cli import main as cli_main

    responses = {
        "/users": {"users": []},
        "/projects": {"projects": []},
        "/projects/prj_2/members": {"members": []},
    }

    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda _method, path, **_kwargs: responses[path],
    )
    runner = CliRunner()

    users = runner.invoke(cli_app, ["user", "list"])
    projects = runner.invoke(cli_app, ["project", "list"])
    project_members = runner.invoke(cli_app, ["project", "member", "list", "prj_2"])

    assert users.exit_code == 0, users.stdout
    assert users.stdout == "No users found.\n"
    assert projects.exit_code == 0, projects.stdout
    assert projects.stdout == "No projects found.\n"
    assert project_members.exit_code == 0, project_members.stdout
    assert project_members.stdout == "No project members found.\n"


def test_cli_admin_commands_convert_auth_failures_to_exit_code_4(
    tmp_path: Path, monkeypatch
) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(cli_main, "user_path", lambda _user_id: "/forbidden")
    server, _handler, url = _serve_api()
    try:
        result = CliRunner().invoke(
            cli_app,
            ["user", "deactivate", "usr_forbidden"],
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
            ["project", "describe", "prj_leaky"],
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


def test_cli_collection_commands_map_to_api_and_mask_stored_token(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    runner = CliRunner()
    commands = [
        (["collection", "list"], "Team Skills"),
        (
            ["collection", "create", "Ops Skills", "--description", "ops"],
            "col_0000000000000002",
        ),
        (["collection", "describe", "col_0000000000000002"], "Ops Skills"),
        (
            [
                "collection",
                "update",
                "col_0000000000000002",
                "--name",
                "Ops Skills2",
                "--description",
                "ops2",
                "--inactive",
            ],
            "Ops Skills2",
        ),
        (["collection", "deactivate", "col_0000000000000002"], "col_0000000000000002"),
        (["collection", "activate", "col_0000000000000002"], "Status: active"),
    ]
    try:
        for args, expected_output in commands:
            result = runner.invoke(cli_app, args, env=env)
            assert result.exit_code == 0, (args, result.stdout)
            assert expected_output in result.stdout
            assert "stored-secret-token" not in result.stdout
    finally:
        server.shutdown()

    assert {request["authorization"] for request in handler.requests} == {
        "Bearer stored-secret-token"
    }
    observed = {
        (request["method"], request["path"]): request["body"]
        for request in handler.requests
    }
    assert ("POST", "/api/v1/collections") in observed
    assert observed[("POST", "/api/v1/collections")] == {
        "name": "Ops Skills",
        "description": "ops",
    }
    collection_patch_bodies = [
        request["body"]
        for request in handler.requests
        if (request["method"], request["path"])
        == ("PATCH", "/api/v1/collections/col_0000000000000002")
    ]
    assert {
        "name": "Ops Skills2",
        "description": "ops2",
        "active": False,
    } in collection_patch_bodies
    assert {"active": True} in collection_patch_bodies


def test_cli_collection_read_and_mutation_commands_use_human_output(
    tmp_path: Path,
) -> None:
    server, _handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    runner = CliRunner()
    try:
        listed = runner.invoke(cli_app, ["collection", "list"], env=env)
        created = runner.invoke(
            cli_app,
            ["collection", "create", "Ops Skills", "--description", "ops"],
            env=env,
        )
        fetched = runner.invoke(
            cli_app, ["collection", "describe", "col_0000000000000002"], env=env
        )
        updated = runner.invoke(
            cli_app,
            [
                "collection",
                "update",
                "col_0000000000000002",
                "--name",
                "Ops Skills2",
                "--description",
                "ops2",
                "--inactive",
            ],
            env=env,
        )
        deactivated = runner.invoke(
            cli_app, ["collection", "deactivate", "col_0000000000000002"], env=env
        )
        activated = runner.invoke(
            cli_app, ["collection", "activate", "col_0000000000000002"], env=env
        )
    finally:
        server.shutdown()

    assert listed.exit_code == 0, listed.stdout
    listed_lines = listed.stdout.splitlines()
    assert listed_lines[0].split() == [
        "COLLECTION_ID",
        "NAME",
        "DESCRIPTION",
        "STATUS",
    ]
    assert listed_lines[1].split() == [
        "col_0000000000000001",
        "Team",
        "Skills",
        "Shared",
        "skills",
        "active",
    ]
    assert '"collections"' not in listed.stdout

    assert created.exit_code == 0, created.stdout
    assert created.stdout == (
        "Created collection Ops Skills (col_0000000000000002).\nStatus: active\n"
    )
    assert '"active"' not in created.stdout

    assert fetched.exit_code == 0, fetched.stdout
    assert fetched.stdout == (
        "Collection: Ops Skills\n"
        "Collection ID: col_0000000000000002\n"
        "Description: ops\n"
        "Status: active\n"
    )

    assert updated.exit_code == 0, updated.stdout
    assert updated.stdout == (
        "Updated collection Ops Skills2 (col_0000000000000002).\nStatus: inactive\n"
    )

    assert deactivated.exit_code == 0, deactivated.stdout
    assert (
        deactivated.stdout
        == "Deactivated collection Ops Skills2 (col_0000000000000002).\n"
    )

    assert activated.exit_code == 0, activated.stdout
    assert activated.stdout == (
        "Activated collection Ops Skills2 (col_0000000000000002).\nStatus: active\n"
    )


def test_cli_collection_list_empty_message(monkeypatch) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda _method, _path, **_kwargs: {"collections": []},
    )
    runner = CliRunner()

    result = runner.invoke(cli_app, ["collection", "list"])

    assert result.exit_code == 0, result.stdout
    assert result.stdout == "No collections found.\n"


def test_cli_collection_refs_resolve_names_and_pass_through_col_ids(
    monkeypatch,
) -> None:
    from agh.cli import main as cli_main

    calls: list[tuple[str, str]] = []

    def fake_api(method: str, path: str, **_kwargs):
        calls.append((method, path))
        if path == "/collections/by-name/Team%20Skills":
            return {"id": "col_0000000000000002", "name": "Team Skills"}
        if path == "/collections/by-name/col_team":
            return {"id": "col_0000000000000003", "name": "col_team"}
        if path in {
            "/collections/col_0000000000000002",
            "/collections/col_0000000000000003",
            "/collections/col_0000000000000123",
        }:
            return {
                "id": path.rsplit("/", 1)[1],
                "name": "Team Skills",
                "description": "",
                "active": True,
            }
        raise AssertionError(path)

    monkeypatch.setattr(cli_main, "_api_request", fake_api)
    runner = CliRunner()
    by_name = runner.invoke(cli_app, ["collection", "describe", "Team Skills"])
    col_prefixed_name = runner.invoke(cli_app, ["collection", "describe", "col_team"])
    col_id = runner.invoke(cli_app, ["collection", "describe", "col_0000000000000123"])
    update_by_name = runner.invoke(
        cli_app,
        ["collection", "update", "Team Skills", "--description", "refreshed"],
    )

    assert by_name.exit_code == 0, by_name.stdout
    assert "Collection ID: col_0000000000000002" in by_name.stdout
    assert col_prefixed_name.exit_code == 0, col_prefixed_name.stdout
    assert "Collection ID: col_0000000000000003" in col_prefixed_name.stdout
    assert col_id.exit_code == 0, col_id.stdout
    assert "Collection ID: col_0000000000000123" in col_id.stdout
    assert update_by_name.exit_code == 0, update_by_name.stdout
    assert (
        "Updated collection Team Skills (col_0000000000000002)."
        in update_by_name.stdout
    )

    assert calls.count(("GET", "/collections/by-name/Team%20Skills")) == 2
    assert ("GET", "/collections/by-name/col_team") in calls
    assert ("GET", "/collections/col_0000000000000003") in calls
    assert ("GET", "/collections/col_0000000000000123") in calls
    assert ("GET", "/collections/by-name/col_0000000000000123") not in calls
    assert ("PATCH", "/collections/col_0000000000000002") in calls


def test_cli_admin_help_preserves_main_manual_and_command_help() -> None:
    runner = CliRunner()
    root_help = runner.invoke(cli_app, []).stdout

    # Subgroups invoked without a subcommand show LOCAL group help, not the
    # root command map. Unknown nested commands likewise show local help.
    user_no_args = runner.invoke(cli_app, ["user"])
    assert user_no_args.exit_code == 0, user_no_args.stdout
    assert "Manage AGH users." in user_no_args.stdout
    assert user_no_args.stdout != root_help

    project_wrong = runner.invoke(cli_app, ["project", "wrong"])
    assert project_wrong.exit_code == 2, project_wrong.stdout
    assert "Manage AGH projects." in project_wrong.stdout
    assert project_wrong.stdout != root_help

    user_group_help = runner.invoke(cli_app, ["user", "--help"])
    project_group_help = runner.invoke(cli_app, ["project", "--help"])
    member_group_help = runner.invoke(cli_app, ["project", "member", "--help"])
    user_help = runner.invoke(cli_app, ["user", "create", "--help"])
    project_help = runner.invoke(cli_app, ["project", "create", "--help"])
    member_help = runner.invoke(cli_app, ["project", "member", "add", "--help"])

    assert user_group_help.exit_code == 0
    assert "create" in user_group_help.stdout
    assert "describe" in user_group_help.stdout
    assert "activate" in user_group_help.stdout
    assert "deactivate" in user_group_help.stdout
    assert "show" not in user_group_help.stdout
    assert "delete" not in user_group_help.stdout
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
    assert "--git-url" in project_help.stdout
    assert member_help.exit_code == 0
    assert "PROJECT_REF" in member_help.stdout or "project_ref" in member_help.stdout
    assert "USER_REF" in member_help.stdout or "user_ref" in member_help.stdout
    collection_group_help = runner.invoke(cli_app, ["collection", "--help"])
    collection_help = runner.invoke(cli_app, ["collection", "create", "--help"])
    assert collection_group_help.exit_code == 0
    assert "create" in collection_group_help.stdout
    assert "describe" in collection_group_help.stdout
    assert "activate" in collection_group_help.stdout
    assert "deactivate" in collection_group_help.stdout
    assert "get" not in collection_group_help.stdout
    assert "delete" not in collection_group_help.stdout
    assert collection_help.exit_code == 0
    assert "--description" in collection_help.stdout


def test_cli_main_help_lists_collection_command() -> None:
    """R2: APP_HELP must list the `collection` command."""
    runner = CliRunner()
    help_output = runner.invoke(cli_app, []).stdout

    assert any(
        line.strip().startswith("collection") for line in help_output.splitlines()
    ), help_output
    assert "Manage collections." in help_output


def test_cli_collection_target_arguments_use_collection_ref_metavar() -> None:
    """R2: targeted collection args accept id or name, so the metavar is COLLECTION_REF."""
    runner = CliRunner()
    for subcommand in ["describe", "update", "activate", "deactivate"]:
        help_output = runner.invoke(cli_app, ["collection", subcommand, "--help"])
        assert help_output.exit_code == 0, help_output.stdout
        usage_line = help_output.stdout.splitlines()[0]
        assert "COLLECTION_REF" in usage_line, (subcommand, usage_line)
        assert "COLLECTION_ID" not in usage_line, (subcommand, usage_line)


def test_cli_collection_deactivate_resolves_name_before_delete(monkeypatch) -> None:
    """R3: `collection deactivate <name>` resolves to a col_ id before issuing DELETE."""
    from agh.cli import main as cli_main

    calls: list[tuple[str, str]] = []

    def fake_api(method: str, path: str, **_kwargs):
        calls.append((method, path))
        if path == "/collections/by-name/Team%20Skills":
            return {"id": "col_0000000000000002", "name": "Team Skills"}
        if (method, path) == ("DELETE", "/collections/col_0000000000000002"):
            return {
                "id": "col_0000000000000002",
                "name": "Team Skills",
                "description": "",
                "active": False,
            }
        raise AssertionError((method, path))

    monkeypatch.setattr(cli_main, "_api_request", fake_api)
    result = CliRunner().invoke(cli_app, ["collection", "deactivate", "Team Skills"])

    assert result.exit_code == 0, result.stdout
    assert (
        result.stdout == "Deactivated collection Team Skills (col_0000000000000002).\n"
    )
    assert ("GET", "/collections/by-name/Team%20Skills") in calls
    assert ("DELETE", "/collections/col_0000000000000002") in calls
    # DELETE must target the resolved id, never the raw name/resolver path.
    assert ("DELETE", "/collections/by-name/Team%20Skills") not in calls
    assert ("DELETE", "/collections/Team%20Skills") not in calls


def test_cli_collection_resolver_failure_exits_with_message(monkeypatch) -> None:
    """R3: a malformed resolver payload surfaces as a CLI failure, not a crash."""
    from agh.cli import main as cli_main

    calls: list[tuple[str, str]] = []

    def fake_api(method: str, path: str, **_kwargs):
        calls.append((method, path))
        if path == "/collections/by-name/Ghost":
            # 200 OK but the resolver payload is malformed (no collection id).
            return {"name": "Ghost"}
        raise AssertionError((method, path))

    monkeypatch.setattr(cli_main, "_api_request", fake_api)
    result = CliRunner().invoke(cli_app, ["collection", "describe", "Ghost"])

    assert result.exit_code == 1, result.stdout
    assert (
        "COLLECTION_REF resolver response did not include a collection id"
        in result.stdout
    )
    # No follow-up fetch against an unresolved id should occur.
    assert not any(
        path.startswith("/collections/") and "/by-name/" not in path
        for _method, path in calls
    )
