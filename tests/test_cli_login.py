"""CLI login and instance-config tests (PR2a: split instance config from auth).

The config-instance slice separates instance configuration from credential
storage in the local config file while leaving the ``login`` command behavior
unchanged (it is rewritten in the auth slice). This file keeps the unchanged
login validation tests and adds the config-instance coverage:

* `agh config` shows only the configured instance URL (never auth)
* `agh config set INSTANCE_URL` stores/overwrites the normalized instance URL
* `agh config clear` clears only the instance URL (credentials preserved)
* Trust-boundary: changing the instance clears stored credentials so they can
  never be sent to a different host (same normalized instance preserves them)
* Corrupt config is recovered gracefully (no traceback; clear guidance; file
  left intact)

The `config show` command is intentionally gone; `config` (no-args) shows the
instance, and `config show` now exits 2 as an unknown subgroup command.
"""

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

INSTANCE_GUIDANCE = "agh config set INSTANCE_URL"


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


def _set_instance(runner: CliRunner, tmp_path: Path, url: str):
    """Configure the instance via the public `config set` command."""
    result = runner.invoke(cli_app, ["config", "set", url], env=_config_env(tmp_path))
    assert result.exit_code == 0, result.stdout
    return result


# --- login (unchanged in this slice; validation kept) ----------------------


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


# --- config: instance only -------------------------------------------------


def test_config_set_then_show_and_clear_instance_url(tmp_path: Path) -> None:
    runner = CliRunner()

    set_result = _set_instance(runner, tmp_path, "http://agh.example/")

    assert "Set instance URL: http://agh.example" in set_result.stdout
    config_path = tmp_path / "config.toml"
    assert 'instance_url = "http://agh.example"' in config_path.read_text("utf-8")

    show = runner.invoke(cli_app, ["config"], env=_config_env(tmp_path))
    assert show.exit_code == 0, show.stdout
    assert "http://agh.example" in show.stdout
    # config shows ONLY the instance, never credentials
    assert "email" not in show.stdout.lower()
    assert "token" not in show.stdout.lower()

    clear = runner.invoke(cli_app, ["config", "clear"], env=_config_env(tmp_path))
    assert clear.exit_code == 0, clear.stdout
    assert "Cleared instance URL" in clear.stdout
    # instance URL is gone (the file may be removed when nothing remains)
    if config_path.exists():
        assert "instance_url" not in config_path.read_text("utf-8")

    show_after = runner.invoke(cli_app, ["config"], env=_config_env(tmp_path))
    assert show_after.exit_code == 0, show_after.stdout
    assert "not set" in show_after.stdout.lower()


def test_config_clear_with_no_instance_is_noop(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli_app, ["config", "clear"], env=_config_env(tmp_path))

    assert result.exit_code == 0, result.stdout
    assert "No instance URL was set" in result.stdout


def test_config_set_rejects_invalid_url_without_writing(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_app, ["config", "set", "not-a-url"], env=_config_env(tmp_path)
    )

    assert result.exit_code != 0
    assert "http://" in result.stdout or "https://" in result.stdout
    assert not (tmp_path / "config.toml").exists()


def test_config_set_overwrites_existing_instance(tmp_path: Path) -> None:
    runner = CliRunner()
    _set_instance(runner, tmp_path, "http://first.example")

    overwrite = runner.invoke(
        cli_app, ["config", "set", "http://second.example"], env=_config_env(tmp_path)
    )
    assert overwrite.exit_code == 0, overwrite.stdout

    config_path = tmp_path / "config.toml"
    text = config_path.read_text("utf-8")
    assert "second.example" in text
    assert "first.example" not in text


def test_config_clear_preserves_credentials(tmp_path: Path) -> None:
    """config clear removes only the instance URL, keeping credentials."""
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        'instance_url = "http://agh.example"\n'
        'email = "owner@example.com"\n'
        'token = "keep-me"\n',
        encoding="utf-8",
    )

    clear = runner.invoke(
        cli_app, ["config", "clear"], env={"AGH_CONFIG_FILE": str(config_path)}
    )
    assert clear.exit_code == 0, clear.stdout

    remaining = config_path.read_text("utf-8")
    assert "instance_url" not in remaining
    assert 'email = "owner@example.com"' in remaining
    assert 'token = "keep-me"' in remaining


def test_config_show_is_not_a_command(tmp_path: Path) -> None:
    """config show was removed; config (no-args) shows the instance instead."""
    runner = CliRunner()
    _set_instance(runner, tmp_path, "http://agh.example")

    result = runner.invoke(cli_app, ["config", "show"], env=_config_env(tmp_path))
    # unknown subgroup command -> local config help, exit 2
    assert result.exit_code == 2


# --- trust boundary: changing instance must not leak credentials ----------


def test_config_set_different_instance_clears_credentials(tmp_path: Path) -> None:
    """Changing the instance URL must clear stored credentials (trust boundary)."""
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        'instance_url = "http://first.example"\n'
        'email = "owner@example.com"\n'
        'token = "old-token"\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        cli_app,
        ["config", "set", "http://second.example"],
        env={"AGH_CONFIG_FILE": str(config_path)},
    )

    assert result.exit_code == 0, result.stdout
    assert "second.example" in result.stdout
    # user is told to re-authenticate
    assert "login" in result.stdout.lower()
    remaining = config_path.read_text("utf-8")
    assert "second.example" in remaining
    assert "first.example" not in remaining
    assert "owner@example.com" not in remaining
    assert "old-token" not in remaining


def test_config_set_same_normalized_instance_preserves_credentials(
    tmp_path: Path,
) -> None:
    """Re-setting the same (normalized) instance keeps credentials."""
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        'instance_url = "http://agh.example"\n'
        'email = "owner@example.com"\n'
        'token = "keep-me"\n',
        encoding="utf-8",
    )

    # trailing slash normalizes to the same instance
    result = runner.invoke(
        cli_app,
        ["config", "set", "http://agh.example/"],
        env={"AGH_CONFIG_FILE": str(config_path)},
    )

    assert result.exit_code == 0, result.stdout
    assert "Set instance URL: http://agh.example" in result.stdout
    assert "cleared" not in result.stdout.lower()
    remaining = config_path.read_text("utf-8")
    assert 'email = "owner@example.com"' in remaining
    assert 'token = "keep-me"' in remaining


def test_config_set_after_clear_does_not_revive_orphaned_credentials(
    tmp_path: Path,
) -> None:
    """After config clear, orphaned credentials must not attach to a new instance."""
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        'instance_url = "http://first.example"\n'
        'email = "owner@example.com"\n'
        'token = "orphan-token"\n',
        encoding="utf-8",
    )

    # clear instance only -> credentials become orphaned (kept by decision)
    clear = runner.invoke(
        cli_app, ["config", "clear"], env={"AGH_CONFIG_FILE": str(config_path)}
    )
    assert clear.exit_code == 0, clear.stdout
    remaining = config_path.read_text("utf-8")
    assert "instance_url" not in remaining
    assert "orphan-token" in remaining

    # configuring a different instance must drop the orphaned credentials
    result = runner.invoke(
        cli_app,
        ["config", "set", "http://second.example"],
        env={"AGH_CONFIG_FILE": str(config_path)},
    )
    assert result.exit_code == 0, result.stdout

    final = config_path.read_text("utf-8")
    assert "second.example" in final
    assert "orphan-token" not in final
    assert "owner@example.com" not in final


# --- corrupted config: graceful recovery, no traceback ---------------------


def _write_corrupt_config(config_path: Path) -> None:
    config_path.write_text(
        'instance_url = "http://agh.example"\nkey = "oops\n', encoding="utf-8"
    )


def test_config_reports_corrupt_config_with_recovery(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    _write_corrupt_config(config_path)

    result = runner.invoke(
        cli_app, ["config"], env={"AGH_CONFIG_FILE": str(config_path)}
    )

    assert result.exit_code != 0
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert str(config_path) in result.stdout
    assert "invalid" in result.stdout.lower()
    # recovery guidance
    assert "config set" in result.stdout.lower()
    # must NOT mask a corrupt file as "not set"
    assert "not set" not in result.stdout.lower()
    # corrupt file left intact (not overwritten)
    assert "oops" in config_path.read_text("utf-8")


def test_config_clear_reports_corrupt_config_without_traceback(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    _write_corrupt_config(config_path)

    result = runner.invoke(
        cli_app, ["config", "clear"], env={"AGH_CONFIG_FILE": str(config_path)}
    )

    assert result.exit_code != 0
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert str(config_path) in result.stdout
    assert "config set" in result.stdout.lower()
    # not overwritten
    assert "oops" in config_path.read_text("utf-8")


# --- help surface ----------------------------------------------------------


def test_config_help_flag_shows_local_help() -> None:
    """config --help shows local config help (never the root map)."""
    runner = CliRunner()
    root_help = runner.invoke(cli_app, []).stdout
    config_help = runner.invoke(cli_app, ["config", "--help"])

    assert config_help.exit_code == 0, config_help.stdout
    assert "local AGH CLI configuration" in config_help.stdout
    assert config_help.stdout != root_help
