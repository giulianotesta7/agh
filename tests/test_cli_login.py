"""CLI login and local config tests."""

from __future__ import annotations

import json
import os
import stat
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

from typer.testing import CliRunner

from agh.cli.main import app as cli_app


class _RedirectHandler(BaseHTTPRequestHandler):
    redirect_url = ""
    seen_authorization: ClassVar[list[str | None]] = []

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        type(self).seen_authorization.append(self.headers.get("Authorization"))
        self.send_response(302)
        self.send_header("Location", type(self).redirect_url)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib API
        return


class _MeHandler(BaseHTTPRequestHandler):
    email = "owner@example.com"
    status_code = 200
    expected_token = "good-token"
    seen_authorization: ClassVar[list[str | None]] = []

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path != "/api/v1/me":
            self.send_response(404)
            self.end_headers()
            return
        type(self).seen_authorization.append(self.headers.get("Authorization"))
        self.send_response(type(self).status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = {"id": "usr_test", "email": type(self).email, "role": "owner"}
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib API
        return


def _serve_me(*, email: str = "owner@example.com", status_code: int = 200):
    class Handler(_MeHandler):
        pass

    Handler.email = email
    Handler.status_code = status_code
    Handler.seen_authorization = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    return server, Handler, url


def _serve_redirect(redirect_url: str):
    class Handler(_RedirectHandler):
        pass

    Handler.redirect_url = redirect_url
    Handler.seen_authorization = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    return server, Handler, url


def _config_env(tmp_path: Path) -> dict[str, str]:
    return {"AGH_CONFIG_FILE": str(tmp_path / "config.toml")}


def test_login_validates_me_and_writes_restricted_config(tmp_path: Path) -> None:
    server, handler, url = _serve_me()
    runner = CliRunner()
    token = "good-token"
    try:
        result = runner.invoke(
            cli_app,
            [
                "login",
                "--url",
                f"{url}/",
                "--email",
                "owner@example.com",
                "--token",
                token,
            ],
            env=_config_env(tmp_path),
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert "Logged in" in result.stdout
    assert token not in result.stdout
    assert handler.seen_authorization == [f"Bearer {token}"]

    config_path = tmp_path / "config.toml"
    config_text = config_path.read_text(encoding="utf-8")
    assert f'instance_url = "{url}"' in config_text
    assert 'email = "owner@example.com"' in config_text
    assert f'token = "{token}"' in config_text
    if os.name == "posix":
        assert stat.S_IMODE(config_path.stat().st_mode) == 0o600


def test_invalid_login_preserves_existing_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        'instance_url = "http://old.example"\nemail = "old@example.com"\ntoken = "old-token"\n',
        encoding="utf-8",
    )
    if os.name == "posix":
        config_path.chmod(0o600)
    before = config_path.read_text(encoding="utf-8")

    server, _handler, url = _serve_me(status_code=401)
    try:
        result = CliRunner().invoke(
            cli_app,
            [
                "login",
                "--url",
                url,
                "--email",
                "owner@example.com",
                "--token",
                "bad-token",
            ],
            env={"AGH_CONFIG_FILE": str(config_path)},
        )
    finally:
        server.shutdown()

    assert result.exit_code != 0
    assert config_path.read_text(encoding="utf-8") == before


def test_login_email_mismatch_preserves_existing_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        'instance_url = "old"\nemail = "old@example.com"\ntoken = "old"\n',
        encoding="utf-8",
    )
    before = config_path.read_text(encoding="utf-8")

    server, _handler, url = _serve_me(email="other@example.com")
    try:
        result = CliRunner().invoke(
            cli_app,
            [
                "login",
                "--url",
                url,
                "--email",
                "owner@example.com",
                "--token",
                "good-token",
            ],
            env={"AGH_CONFIG_FILE": str(config_path)},
        )
    finally:
        server.shutdown()

    assert result.exit_code != 0
    assert "email" in result.stdout.lower()
    assert config_path.read_text(encoding="utf-8") == before


def test_login_rejects_redirect_without_forwarding_token(tmp_path: Path) -> None:
    target_server, target_handler, target_url = _serve_me()
    redirect_server, _redirect_handler, redirect_url = _serve_redirect(
        f"{target_url}/api/v1/me"
    )
    try:
        result = CliRunner().invoke(
            cli_app,
            [
                "login",
                "--url",
                redirect_url,
                "--email",
                "owner@example.com",
                "--token",
                "redirect-secret",
            ],
            env=_config_env(tmp_path),
        )
    finally:
        redirect_server.shutdown()
        target_server.shutdown()

    assert result.exit_code != 0
    assert "redirect" in result.stdout.lower()
    assert target_handler.seen_authorization == []
    assert not (tmp_path / "config.toml").exists()


def test_login_timeout_is_clean_failure(tmp_path: Path, monkeypatch) -> None:
    from agh.cli import config as cli_config

    def raise_timeout(*_args, **_kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(cli_config._NO_REDIRECT_OPENER, "open", raise_timeout)

    result = CliRunner().invoke(
        cli_app,
        [
            "login",
            "--url",
            "http://agh.example",
            "--email",
            "owner@example.com",
            "--token",
            "secret-token",
        ],
        env=_config_env(tmp_path),
    )

    assert result.exit_code != 0
    assert "timed out" in result.stdout.lower()
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert not (tmp_path / "config.toml").exists()


def test_login_socket_timeout_is_clean_failure(tmp_path: Path, monkeypatch) -> None:
    from agh.cli import config as cli_config

    def raise_timeout(*_args, **_kwargs):
        raise TimeoutError("socket timed out")

    monkeypatch.setattr(cli_config._NO_REDIRECT_OPENER, "open", raise_timeout)

    result = CliRunner().invoke(
        cli_app,
        [
            "login",
            "--url",
            "http://agh.example",
            "--email",
            "owner@example.com",
            "--token",
            "secret-token",
        ],
        env=_config_env(tmp_path),
    )

    assert result.exit_code != 0
    assert "timed out" in result.stdout.lower()
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert not (tmp_path / "config.toml").exists()


def test_config_show_masks_token(tmp_path: Path) -> None:
    token = "super-secret-token"
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f'instance_url = "http://agh.example"\nemail = "owner@example.com"\ntoken = "{token}"\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli_app,
        ["config", "show"],
        env={"AGH_CONFIG_FILE": str(config_path)},
    )

    assert result.exit_code == 0, result.stdout
    assert "instance_url" in result.stdout
    assert "http://agh.example" in result.stdout
    assert "owner@example.com" in result.stdout
    assert token not in result.stdout
    assert "supe" in result.stdout
    assert "****" in result.stdout


def test_top_level_help_lists_login_config_flags_and_arguments() -> None:
    runner = CliRunner()

    no_args = runner.invoke(cli_app, [])
    help_result = runner.invoke(cli_app, ["--help"])
    invalid_command = runner.invoke(cli_app, ["wrong-command"])
    config_no_args = runner.invoke(cli_app, ["config"])
    config_help = runner.invoke(cli_app, ["config", "--help"])
    config_invalid_command = runner.invoke(cli_app, ["config", "wrong-command"])

    assert no_args.exit_code == 0
    assert help_result.exit_code == 0
    assert invalid_command.exit_code == 2
    assert config_no_args.exit_code == 0
    assert config_help.exit_code == 0
    assert config_invalid_command.exit_code == 2
    # root invocations (no args, --help, unknown command) share the root map
    assert help_result.stdout == no_args.stdout
    assert invalid_command.stdout == no_args.stdout
    # config shows LOCAL config help, never the root command map
    for config_output in (
        config_no_args.stdout,
        config_help.stdout,
        config_invalid_command.stdout,
    ):
        assert "local AGH CLI configuration" in config_output
        assert config_output != no_args.stdout
    for output in (no_args.stdout, help_result.stdout):
        assert "Agent Guidance Hub" in output
        assert "Usage" in output
        assert "Commands" in output
        assert "login" in output
        assert "config" in output
        assert "--help" in output
        assert "Arguments" in output or "Options" in output


def test_command_specific_help_still_works() -> None:
    runner = CliRunner()

    login_help = runner.invoke(cli_app, ["login", "--help"])
    config_show_help = runner.invoke(cli_app, ["config", "show", "--help"])

    assert login_help.exit_code == 0
    assert "--url" in login_help.stdout
    assert "--email" in login_help.stdout
    assert "--token" in login_help.stdout
    assert config_show_help.exit_code == 0
    assert "Show local AGH config" in config_show_help.stdout
