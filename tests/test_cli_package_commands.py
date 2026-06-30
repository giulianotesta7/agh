"""CLI package publish/list and describe tests."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

from typer.testing import CliRunner

from agh.cli.main import app as cli_app
from agh.common.package_limits import MAX_PACKAGE_FILE_BYTES, MAX_PACKAGE_FILES
from agh.common.package_manifest import load_package_manifest


class _ApiHandler(BaseHTTPRequestHandler):
    requests: ClassVar[list[dict[str, Any]]] = []

    def do_GET(self) -> None:  # noqa: N802
        self._handle()

    def do_POST(self) -> None:  # noqa: N802
        self._handle()

    def do_PATCH(self) -> None:  # noqa: N802
        self._handle()

    def do_DELETE(self) -> None:  # noqa: N802
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

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def _response_for(method: str, path: str) -> tuple[int, dict[str, Any]]:
    if (method, path) == ("GET", "/api/v1/packages"):
        return 200, {
            "packages": [
                {
                    "id": "acme/onboarding@1.0.0",
                    "package_id": "pkg_1",
                    "domain": "acme",
                    "name": "onboarding",
                    "version": "1.0.0",
                    "description": "Demo onboarding instructions.",
                }
            ]
        }
    if (method, path) == ("POST", "/api/v1/packages"):
        return 201, {
            "id": "acme/onboarding@1.0.0",
            "package_id": "pkg_1",
            "description": "Demo onboarding instructions.",
            "checksum": "sha256:" + "a" * 64,
            "token_hash": "server-secret",
        }
    return 404, {"detail": f"unexpected {method} {path}"}


def _serve_api():
    class Handler(_ApiHandler):
        pass

    Handler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, Handler, f"http://127.0.0.1:{server.server_port}"


def _write_config(tmp_path: Path, url: str) -> dict[str, str]:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f'instance_url = "{url}"\nemail = "owner@example.com"\n'
        'token = "stored-package-token"\n',
        encoding="utf-8",
    )
    return {"AGH_CONFIG_FILE": str(config_path)}


def test_cli_package_unknown_subcommands_exit_2_with_local_help() -> None:
    runner = CliRunner()
    root_help = runner.invoke(cli_app, []).stdout

    package_unknown = runner.invoke(cli_app, ["package", "wrong-command"])

    assert package_unknown.exit_code == 2
    assert package_unknown.stdout != root_help
    assert "Manage guidance packages and assignments." in package_unknown.stdout


def _package_dir(tmp_path: Path) -> Path:
    root = tmp_path / "package"
    (root / "instructions").mkdir(parents=True)
    (root / "skills" / "lint").mkdir(parents=True)
    (root / "agh.package.toml").write_text(
        'domain = "acme"\nname = "onboarding"\nversion = "1.0.0"\n'
        'description = "desc"\n',
        encoding="utf-8",
    )
    (root / "instructions" / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / "skills" / "lint" / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    return root


def test_cli_package_init_creates_minimal_template(tmp_path: Path) -> None:
    package_dir = tmp_path / "my-package"

    result = CliRunner().invoke(
        cli_app,
        [
            "package",
            "init",
            str(package_dir),
            "--domain",
            "acme",
            "--name",
            "onboarding",
            "--version",
            "1.0.0",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Initialized package template" in result.stdout
    assert (package_dir / "agh.package.toml").read_text(encoding="utf-8") == (
        'domain = "acme"\n'
        'name = "onboarding"\n'
        'version = "1.0.0"\n'
        'description = "TODO"\n'
    )
    assert (package_dir / "instructions").is_dir()
    assert (package_dir / "skills").is_dir()
    assert not (package_dir / "instructions" / "AGENTS.md").exists()
    assert not (package_dir / "instructions" / "CLAUDE.md").exists()


def test_cli_package_init_creates_custom_optional_templates(tmp_path: Path) -> None:
    package_dir = tmp_path / "review-package"

    result = CliRunner().invoke(
        cli_app,
        [
            "package",
            "init",
            str(package_dir),
            "--domain",
            "acme",
            "--name",
            "review",
            "--version",
            "1.2.3",
            "--description",
            "Shared review skills",
            "--with-agents",
            "--with-claude",
            "--with-skill",
            "reviewer",
            "--with-skill",
            "lint",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert 'version = "1.2.3"' in (package_dir / "agh.package.toml").read_text(
        encoding="utf-8"
    )
    assert 'description = "Shared review skills"' in (
        package_dir / "agh.package.toml"
    ).read_text(encoding="utf-8")
    assert (package_dir / "instructions" / "AGENTS.md").read_text(encoding="utf-8")
    assert (package_dir / "instructions" / "CLAUDE.md").read_text(encoding="utf-8")
    assert (package_dir / "skills" / "reviewer" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert (package_dir / "skills" / "lint" / "SKILL.md").read_text(encoding="utf-8")


def test_cli_package_init_escapes_description_as_valid_toml(tmp_path: Path) -> None:
    package_dir = tmp_path / "escaped-package"

    result = CliRunner().invoke(
        cli_app,
        [
            "package",
            "init",
            str(package_dir),
            "--domain",
            "acme",
            "--name",
            "escaped",
            "--version",
            "1.0.0",
            "--description",
            'Quote " slash \\ newline \n backspace \b',
        ],
    )

    assert result.exit_code == 0, result.stdout
    manifest = (package_dir / "agh.package.toml").read_text(encoding="utf-8")
    assert load_package_manifest(package_dir / "agh.package.toml").description == (
        'Quote " slash \\ newline \n backspace \b'
    )
    assert "\\b" in manifest


def test_cli_package_init_rejects_existing_path_and_invalid_values(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    runner = CliRunner()

    existing_result = runner.invoke(
        cli_app,
        [
            "package",
            "init",
            str(existing),
            "--domain",
            "acme",
            "--name",
            "package",
            "--version",
            "1.0.0",
        ],
    )
    invalid_domain = runner.invoke(
        cli_app,
        [
            "package",
            "init",
            str(tmp_path / "a"),
            "--domain",
            "Bad",
            "--name",
            "package",
            "--version",
            "1.0.0",
        ],
    )
    invalid_version = runner.invoke(
        cli_app,
        [
            "package",
            "init",
            str(tmp_path / "b"),
            "--domain",
            "acme",
            "--name",
            "package",
            "--version",
            "latest",
        ],
    )
    invalid_skill = runner.invoke(
        cli_app,
        [
            "package",
            "init",
            str(tmp_path / "c"),
            "--domain",
            "acme",
            "--name",
            "package",
            "--version",
            "1.0.0",
            "--with-skill",
            "Bad",
        ],
    )
    duplicate_skill_path = tmp_path / "duplicate"
    duplicate_skill = runner.invoke(
        cli_app,
        [
            "package",
            "init",
            str(duplicate_skill_path),
            "--domain",
            "acme",
            "--name",
            "package",
            "--version",
            "1.0.0",
            "--with-skill",
            "dup",
            "--with-skill",
            "dup",
        ],
    )

    assert existing_result.exit_code == 2
    assert "already exists" in existing_result.stdout
    assert invalid_domain.exit_code == 2
    assert "invalid domain" in invalid_domain.stdout
    assert invalid_version.exit_code == 2
    assert "invalid version" in invalid_version.stdout
    assert invalid_skill.exit_code == 2
    assert "invalid skill name" in invalid_skill.stdout
    assert duplicate_skill.exit_code == 2
    assert "duplicate skill name" in duplicate_skill.stdout
    assert not duplicate_skill_path.exists()


def test_cli_package_publish_list_map_to_api(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    package_dir = _package_dir(tmp_path)
    runner = CliRunner()
    commands = [
        (["package", "list"], "acme/onboarding@1.0.0"),
        (["package", "publish", str(package_dir)], "acme/onboarding@1.0.0"),
    ]
    try:
        for args, expected in commands:
            result = runner.invoke(cli_app, args, env=env)
            assert result.exit_code == 0, (args, result.stdout)
            assert expected in result.stdout
            assert "stored-package-token" not in result.stdout
            assert "server-secret" not in result.stdout
    finally:
        server.shutdown()

    assert {request["authorization"] for request in handler.requests} == {
        "Bearer stored-package-token"
    }
    bodies = {
        (request["method"], request["path"]): request["body"]
        for request in handler.requests
    }
    publish_body = bodies[("POST", "/api/v1/packages")]
    assert publish_body == {
        "files": {
            "agh.package.toml": (
                'domain = "acme"\nname = "onboarding"\nversion = "1.0.0"\n'
                'description = "desc"\n'
            ),
            "instructions/AGENTS.md": "# Agents\n",
            "skills/lint/SKILL.md": "# Skill\n",
        }
    }


def test_cli_package_publish_accepts_skill_only_package(tmp_path: Path) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    package_dir = _package_dir(tmp_path)
    for path in (package_dir / "instructions").iterdir():
        path.unlink()
    try:
        result = CliRunner().invoke(
            cli_app, ["package", "publish", str(package_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    publish_body = handler.requests[0]["body"]
    assert publish_body == {
        "files": {
            "agh.package.toml": (
                'domain = "acme"\nname = "onboarding"\nversion = "1.0.0"\n'
                'description = "desc"\n'
            ),
            "skills/lint/SKILL.md": "# Skill\n",
        }
    }


def test_cli_package_publish_uses_human_output_without_secret_fields(
    tmp_path: Path,
) -> None:
    server, _handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    package_dir = _package_dir(tmp_path)
    try:
        result = CliRunner().invoke(
            cli_app, ["package", "publish", str(package_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert result.stdout == (
        "Published acme/onboarding@1.0.0.\n"
        "Package ID: pkg_1\n"
        "Description: Demo onboarding instructions.\n"
        f"Checksum: sha256:{'a' * 64}\n"
    )
    assert "token_hash" not in result.stdout
    assert "server-secret" not in result.stdout


def test_cli_package_read_commands_use_human_output(tmp_path: Path) -> None:
    server, _handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    runner = CliRunner()
    try:
        packages = runner.invoke(cli_app, ["package", "list"], env=env)
    finally:
        server.shutdown()

    assert packages.exit_code == 0, packages.stdout
    package_lines = packages.stdout.splitlines()
    assert package_lines[0].split() == ["PACKAGE_REF", "DESCRIPTION"]
    assert package_lines[1].split(maxsplit=1) == [
        "acme/onboarding@1.0.0",
        "Demo onboarding instructions.",
    ]
    assert '"packages"' not in packages.stdout


def test_cli_package_read_commands_show_empty_messages(monkeypatch) -> None:
    from agh.cli import main as cli_main

    responses = {
        "/packages": {"packages": []},
    }

    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda _method, path, **_kwargs: responses[path],
    )
    runner = CliRunner()

    packages = runner.invoke(cli_app, ["package", "list"])

    assert packages.exit_code == 0, packages.stdout
    assert packages.stdout == "No packages found.\n"


def test_cli_package_publish_local_validation_errors_exit_2_without_api_call(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    bad_pack = tmp_path / "bad-package"
    bad_pack.mkdir()
    (bad_pack / "agh.package.toml").write_text(
        'domain = "acme"\nname = "bad"\nversion = "1.0.0"\ndescription = "desc"\n',
        encoding="utf-8",
    )
    try:
        result = CliRunner().invoke(
            cli_app, ["package", "publish", str(bad_pack)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "at least one instruction file or skill" in result.stdout
    assert handler.requests == []


def test_cli_package_publish_refuses_symlinked_manifest_before_reading(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    package_dir = _package_dir(tmp_path)
    outside = tmp_path / "outside.toml"
    outside.write_text("not valid toml =", encoding="utf-8")
    (package_dir / "agh.package.toml").unlink()
    (package_dir / "agh.package.toml").symlink_to(outside)
    try:
        result = CliRunner().invoke(
            cli_app, ["package", "publish", str(package_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "symlinked package path" in result.stdout
    assert "invalid agh.package.toml" not in result.stdout
    assert handler.requests == []


def test_cli_package_publish_refuses_symlinked_instruction_directory(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    package_dir = _package_dir(tmp_path)
    outside = tmp_path / "outside-instructions"
    outside.mkdir()
    (outside / "AGENTS.md").write_text("secret", encoding="utf-8")
    for child in (package_dir / "instructions").iterdir():
        child.unlink()
    (package_dir / "instructions").rmdir()
    (package_dir / "instructions").symlink_to(outside, target_is_directory=True)
    try:
        result = CliRunner().invoke(
            cli_app, ["package", "publish", str(package_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "symlinked package path" in result.stdout
    assert handler.requests == []


def test_cli_package_publish_refuses_oversized_manifest_before_parsing(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    package_dir = _package_dir(tmp_path)
    (package_dir / "agh.package.toml").write_text(
        "x" * (MAX_PACKAGE_FILE_BYTES + 1), encoding="utf-8"
    )
    try:
        result = CliRunner().invoke(
            cli_app, ["package", "publish", str(package_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "too large" in result.stdout
    assert "invalid agh.package.toml" not in result.stdout
    assert handler.requests == []


def test_cli_package_publish_refuses_symlinked_parent_path(tmp_path: Path) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    outside = tmp_path / "outside"
    outside.mkdir()
    package_dir = _package_dir(outside)
    link = tmp_path / "link"
    link.symlink_to(outside, target_is_directory=True)
    symlinked_package_dir = link / package_dir.name
    try:
        result = CliRunner().invoke(
            cli_app, ["package", "publish", str(symlinked_package_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "must not contain symlinks" in result.stdout
    assert handler.requests == []


def test_cli_package_publish_refuses_binary_manifest_and_oversized_files(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    package_dir = _package_dir(tmp_path)
    (package_dir / "agh.package.toml").write_bytes(b"\xff\xfe\x00")
    try:
        binary = CliRunner().invoke(
            cli_app, ["package", "publish", str(package_dir)], env=env
        )
        (package_dir / "agh.package.toml").write_text(
            'domain = "acme"\nname = "onboarding"\nversion = "1.0.0"\n'
            'description = "desc"\n',
            encoding="utf-8",
        )
        (package_dir / "instructions" / "AGENTS.md").write_text(
            "x" * (MAX_PACKAGE_FILE_BYTES + 1), encoding="utf-8"
        )
        oversized = CliRunner().invoke(
            cli_app, ["package", "publish", str(package_dir)], env=env
        )
    finally:
        server.shutdown()

    assert binary.exit_code == 2
    assert "codec" in binary.stdout or "UTF-8" in binary.stdout
    assert oversized.exit_code == 2
    assert "too large" in oversized.stdout
    assert handler.requests == []


def test_cli_package_publish_refuses_too_many_allowed_files(tmp_path: Path) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    package_dir = _package_dir(tmp_path)
    skills_dir = package_dir / "skills"
    for index in range(MAX_PACKAGE_FILES):
        skill_dir = skills_dir / f"skill-{index}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("use this skill\n", encoding="utf-8")
    try:
        result = CliRunner().invoke(
            cli_app, ["package", "publish", str(package_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "more than" in result.stdout or "too many" in result.stdout
    assert handler.requests == []


def test_cli_package_publish_refuses_unexpected_hidden_files(tmp_path: Path) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    package_dir = _package_dir(tmp_path)
    (package_dir / ".env").write_text("SECRET=1\n", encoding="utf-8")
    try:
        result = CliRunner().invoke(
            cli_app, ["package", "publish", str(package_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "unexpected package file path" in result.stdout
    assert handler.requests == []


def test_cli_package_publish_refuses_symlinked_package_paths(tmp_path: Path) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    package_dir = _package_dir(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    (package_dir / "instructions" / "LEAK.md").symlink_to(outside)
    try:
        result = CliRunner().invoke(
            cli_app, ["package", "publish", str(package_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "symlinked package path" in result.stdout
    assert handler.requests == []


def test_cli_package_help_is_discoverable() -> None:
    runner = CliRunner()

    package_help = runner.invoke(cli_app, ["package", "--help"])
    describe_help = runner.invoke(cli_app, ["package", "describe", "--help"])
    publish_help = runner.invoke(cli_app, ["package", "publish", "--help"])
    init_help = runner.invoke(cli_app, ["package", "init", "--help"])

    assert package_help.exit_code == 0
    assert "init" in package_help.stdout
    assert "publish" in package_help.stdout
    assert "list" in package_help.stdout
    assert "describe" in package_help.stdout
    assert "assign" in package_help.stdout
    assert describe_help.exit_code == 0
    assert "pkgv_" in describe_help.stdout
    assert "name@version" in describe_help.stdout
    assert publish_help.exit_code == 0
    assert "PATH" in publish_help.stdout or "path" in publish_help.stdout
    assert init_help.exit_code == 0
    assert "--domain" in init_help.stdout
    assert "--with-skill" in init_help.stdout
