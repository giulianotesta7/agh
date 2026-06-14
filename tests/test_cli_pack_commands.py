"""CLI pack publish/list and project pack assignment tests."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

from typer.testing import CliRunner

from agh.cli.main import app as cli_app
from agh.cli.pack_publish import MAX_PACK_FILE_BYTES, MAX_PACK_FILES
from agh.common.pack_manifest import load_pack_manifest


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
    if (method, path) == ("GET", "/api/v1/packs"):
        return 200, {
            "packs": [
                {
                    "id": "acme/onboarding@1.0.0",
                    "domain": "acme",
                    "name": "onboarding",
                    "version": "1.0.0",
                    "description": "Demo onboarding instructions.",
                }
            ]
        }
    if (method, path) == ("POST", "/api/v1/packs"):
        return 201, {
            "id": "acme/onboarding@1.0.0",
            "pack_id": "pack_1",
            "description": "Demo onboarding instructions.",
            "checksum": "sha256:" + "a" * 64,
            "token_hash": "server-secret",
        }
    if (method, path) == ("GET", "/api/v1/projects/prj_1/packs"):
        return 200, {
            "project_packs": [
                {
                    "id": "asn_1",
                    "pack_ref": "acme/onboarding@latest",
                    "resolved_ref": "acme/onboarding@1.0.0",
                    "position": 0,
                    "active": True,
                }
            ]
        }
    if (method, path) == ("POST", "/api/v1/projects/prj_1/packs"):
        return 201, {
            "id": "asn_1",
            "project_id": "prj_1",
            "pack_ref": "acme/onboarding@latest",
            "resolved_ref": "acme/onboarding@1.0.0",
            "position": 5,
            "active": True,
        }
    if (method, path) == ("PATCH", "/api/v1/projects/prj_1/packs/asn_1"):
        return 200, {
            "id": "asn_1",
            "project_id": "prj_1",
            "pack_ref": "acme/onboarding@1.0.0",
            "resolved_ref": "acme/onboarding@1.0.0",
            "position": 7,
            "active": False,
        }
    if (method, path) == ("DELETE", "/api/v1/projects/prj_1/packs/asn_1"):
        return 200, {"id": "asn_1", "project_id": "prj_1", "active": False}
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
        'token = "stored-pack-token"\n',
        encoding="utf-8",
    )
    return {"AGH_CONFIG_FILE": str(config_path)}


def test_cli_pack_unknown_subcommands_exit_2_with_help_first_output() -> None:
    runner = CliRunner()
    expected_help = runner.invoke(cli_app, []).stdout

    for args in [
        ["pack", "wrong-command"],
        ["project", "pack", "wrong-command"],
    ]:
        result = runner.invoke(cli_app, args)

        assert result.exit_code == 2, args
        assert result.stdout == expected_help


def _pack_dir(tmp_path: Path) -> Path:
    root = tmp_path / "pack"
    (root / "instructions").mkdir(parents=True)
    (root / "skills" / "lint").mkdir(parents=True)
    (root / "agh.pack.toml").write_text(
        'domain = "acme"\nname = "onboarding"\nversion = "1.0.0"\n'
        'description = "desc"\n',
        encoding="utf-8",
    )
    (root / "instructions" / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / "skills" / "lint" / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    return root


def test_cli_pack_init_creates_minimal_template(tmp_path: Path) -> None:
    pack_dir = tmp_path / "my-pack"

    result = CliRunner().invoke(
        cli_app,
        [
            "pack",
            "init",
            str(pack_dir),
            "--domain",
            "acme",
            "--name",
            "onboarding",
            "--version",
            "1.0.0",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Initialized pack template" in result.stdout
    assert (pack_dir / "agh.pack.toml").read_text(encoding="utf-8") == (
        'domain = "acme"\n'
        'name = "onboarding"\n'
        'version = "1.0.0"\n'
        'description = "TODO"\n'
    )
    assert (pack_dir / "instructions").is_dir()
    assert (pack_dir / "skills").is_dir()
    assert not (pack_dir / "instructions" / "AGENTS.md").exists()
    assert not (pack_dir / "instructions" / "CLAUDE.md").exists()


def test_cli_pack_init_creates_custom_optional_templates(tmp_path: Path) -> None:
    pack_dir = tmp_path / "review-pack"

    result = CliRunner().invoke(
        cli_app,
        [
            "pack",
            "init",
            str(pack_dir),
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
    assert 'version = "1.2.3"' in (pack_dir / "agh.pack.toml").read_text(
        encoding="utf-8"
    )
    assert 'description = "Shared review skills"' in (
        pack_dir / "agh.pack.toml"
    ).read_text(encoding="utf-8")
    assert (pack_dir / "instructions" / "AGENTS.md").read_text(encoding="utf-8")
    assert (pack_dir / "instructions" / "CLAUDE.md").read_text(encoding="utf-8")
    assert (pack_dir / "skills" / "reviewer" / "SKILL.md").read_text(encoding="utf-8")
    assert (pack_dir / "skills" / "lint" / "SKILL.md").read_text(encoding="utf-8")


def test_cli_pack_init_escapes_description_as_valid_toml(tmp_path: Path) -> None:
    pack_dir = tmp_path / "escaped-pack"

    result = CliRunner().invoke(
        cli_app,
        [
            "pack",
            "init",
            str(pack_dir),
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
    manifest = (pack_dir / "agh.pack.toml").read_text(encoding="utf-8")
    assert load_pack_manifest(pack_dir / "agh.pack.toml").description == (
        'Quote " slash \\ newline \n backspace \b'
    )
    assert "\\b" in manifest


def test_cli_pack_init_rejects_existing_path_and_invalid_values(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    runner = CliRunner()

    existing_result = runner.invoke(
        cli_app,
        [
            "pack",
            "init",
            str(existing),
            "--domain",
            "acme",
            "--name",
            "pack",
            "--version",
            "1.0.0",
        ],
    )
    invalid_domain = runner.invoke(
        cli_app,
        [
            "pack",
            "init",
            str(tmp_path / "a"),
            "--domain",
            "Bad",
            "--name",
            "pack",
            "--version",
            "1.0.0",
        ],
    )
    invalid_version = runner.invoke(
        cli_app,
        [
            "pack",
            "init",
            str(tmp_path / "b"),
            "--domain",
            "acme",
            "--name",
            "pack",
            "--version",
            "latest",
        ],
    )
    invalid_skill = runner.invoke(
        cli_app,
        [
            "pack",
            "init",
            str(tmp_path / "c"),
            "--domain",
            "acme",
            "--name",
            "pack",
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
            "pack",
            "init",
            str(duplicate_skill_path),
            "--domain",
            "acme",
            "--name",
            "pack",
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


def test_cli_pack_publish_list_and_project_pack_commands_map_to_api(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    pack_dir = _pack_dir(tmp_path)
    runner = CliRunner()
    commands = [
        (["pack", "list"], "acme/onboarding@1.0.0"),
        (["pack", "publish", str(pack_dir)], "acme/onboarding@1.0.0"),
        (["project", "pack", "list", "prj_1"], "asn_1"),
        (
            [
                "project",
                "pack",
                "add",
                "prj_1",
                "acme/onboarding@latest",
                "--position",
                "5",
            ],
            "Assigned acme/onboarding@latest",
        ),
        (
            [
                "project",
                "pack",
                "update",
                "prj_1",
                "asn_1",
                "--pack-ref",
                "acme/onboarding@1.0.0",
                "--position",
                "7",
                "--inactive",
            ],
            "Status: inactive",
        ),
        (["project", "pack", "remove", "prj_1", "asn_1"], "Removed assignment asn_1"),
    ]
    try:
        for args, expected in commands:
            result = runner.invoke(cli_app, args, env=env)
            assert result.exit_code == 0, (args, result.stdout)
            assert expected in result.stdout
            assert "stored-pack-token" not in result.stdout
            assert "server-secret" not in result.stdout
    finally:
        server.shutdown()

    assert {request["authorization"] for request in handler.requests} == {
        "Bearer stored-pack-token"
    }
    bodies = {
        (request["method"], request["path"]): request["body"]
        for request in handler.requests
    }
    publish_body = bodies[("POST", "/api/v1/packs")]
    assert publish_body == {
        "files": {
            "agh.pack.toml": (
                'domain = "acme"\nname = "onboarding"\nversion = "1.0.0"\n'
                'description = "desc"\n'
            ),
            "instructions/AGENTS.md": "# Agents\n",
            "skills/lint/SKILL.md": "# Skill\n",
        }
    }
    assert bodies[("POST", "/api/v1/projects/prj_1/packs")] == {
        "pack_ref": "acme/onboarding@latest",
        "position": 5,
    }
    assert bodies[("PATCH", "/api/v1/projects/prj_1/packs/asn_1")] == {
        "pack_ref": "acme/onboarding@1.0.0",
        "position": 7,
        "active": False,
    }


def test_cli_pack_publish_accepts_skill_only_pack(tmp_path: Path) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    pack_dir = _pack_dir(tmp_path)
    for path in (pack_dir / "instructions").iterdir():
        path.unlink()
    try:
        result = CliRunner().invoke(
            cli_app, ["pack", "publish", str(pack_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    publish_body = handler.requests[0]["body"]
    assert publish_body == {
        "files": {
            "agh.pack.toml": (
                'domain = "acme"\nname = "onboarding"\nversion = "1.0.0"\n'
                'description = "desc"\n'
            ),
            "skills/lint/SKILL.md": "# Skill\n",
        }
    }


def test_cli_pack_publish_uses_human_output_without_secret_fields(
    tmp_path: Path,
) -> None:
    server, _handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    pack_dir = _pack_dir(tmp_path)
    try:
        result = CliRunner().invoke(
            cli_app, ["pack", "publish", str(pack_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 0, result.stdout
    assert result.stdout == (
        "Published acme/onboarding@1.0.0.\n"
        "Pack ID: pack_1\n"
        "Description: Demo onboarding instructions.\n"
        f"Checksum: sha256:{'a' * 64}\n"
    )
    assert "token_hash" not in result.stdout
    assert "server-secret" not in result.stdout


def test_cli_pack_read_commands_use_human_output(tmp_path: Path) -> None:
    server, _handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    runner = CliRunner()
    try:
        packs = runner.invoke(cli_app, ["pack", "list"], env=env)
        assignments = runner.invoke(
            cli_app, ["project", "pack", "list", "prj_1"], env=env
        )
    finally:
        server.shutdown()

    assert packs.exit_code == 0, packs.stdout
    pack_lines = packs.stdout.splitlines()
    assert pack_lines[0].split() == ["PACK_REF", "DESCRIPTION"]
    assert pack_lines[1].split(maxsplit=1) == [
        "acme/onboarding@1.0.0",
        "Demo onboarding instructions.",
    ]
    assert '"packs"' not in packs.stdout

    assert assignments.exit_code == 0, assignments.stdout
    assignment_lines = assignments.stdout.splitlines()
    assert assignment_lines[0].split() == [
        "ASSIGNMENT_ID",
        "PACK_REF",
        "RESOLVED",
        "POSITION",
        "STATUS",
    ]
    assert assignment_lines[1].split() == [
        "asn_1",
        "acme/onboarding@latest",
        "acme/onboarding@1.0.0",
        "0",
        "active",
    ]
    assert '"project_packs"' not in assignments.stdout


def test_cli_project_pack_mutation_commands_use_human_output(tmp_path: Path) -> None:
    server, _handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    runner = CliRunner()
    try:
        added = runner.invoke(
            cli_app,
            [
                "project",
                "pack",
                "add",
                "prj_1",
                "acme/onboarding@latest",
                "--position",
                "5",
            ],
            env=env,
        )
        updated = runner.invoke(
            cli_app,
            [
                "project",
                "pack",
                "update",
                "prj_1",
                "asn_1",
                "--pack-ref",
                "acme/onboarding@1.0.0",
                "--position",
                "7",
                "--inactive",
            ],
            env=env,
        )
        removed = runner.invoke(
            cli_app, ["project", "pack", "remove", "prj_1", "asn_1"], env=env
        )
    finally:
        server.shutdown()

    assert added.exit_code == 0, added.stdout
    assert added.stdout == (
        "Assigned acme/onboarding@latest to project prj_1.\n"
        "Resolved: acme/onboarding@1.0.0\n"
        "Assignment: asn_1\n"
    )
    assert '"project_id"' not in added.stdout

    assert updated.exit_code == 0, updated.stdout
    assert updated.stdout == (
        "Updated assignment asn_1 on project prj_1.\n"
        "Pack: acme/onboarding@1.0.0\n"
        "Resolved: acme/onboarding@1.0.0\n"
        "Position: 7\n"
        "Status: inactive\n"
    )

    assert removed.exit_code == 0, removed.stdout
    assert removed.stdout == "Removed assignment asn_1 from project prj_1.\n"


def test_cli_project_pack_commands_resolve_pack_version_refs(monkeypatch) -> None:
    from agh.cli import main as cli_main

    calls: list[dict[str, Any]] = []

    def fake_api_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, **kwargs})
        if (method, path) == (
            "GET",
            "/packs/versions:resolve?ref=onboarding%401.0.0",
        ):
            return {"pack_ref": "acme/onboarding@1.0.0"}
        if (method, path) == (
            "GET",
            "/packs/versions:resolve?ref=packv_0123456789abcdef",
        ):
            return {"pack_ref": "acme/onboarding@1.2.0"}
        if (method, path) == ("POST", "/projects/prj_1/packs"):
            return {
                "id": "asn_1",
                "pack_ref": kwargs["body"]["pack_ref"],
                "resolved_ref": kwargs["body"]["pack_ref"],
            }
        if (method, path) == ("PATCH", "/projects/prj_1/packs/asn_1"):
            return {
                "id": "asn_1",
                "pack_ref": kwargs["body"]["pack_ref"],
                "resolved_ref": kwargs["body"]["pack_ref"],
                "position": 0,
                "active": True,
            }
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(cli_main, "_api_request", fake_api_request)
    runner = CliRunner()

    added = runner.invoke(
        cli_app, ["project", "pack", "add", "prj_1", "onboarding@1.0.0"]
    )
    updated = runner.invoke(
        cli_app,
        [
            "project",
            "pack",
            "update",
            "prj_1",
            "asn_1",
            "--pack-ref",
            "packv_0123456789abcdef",
        ],
    )

    assert added.exit_code == 0, added.stdout
    assert updated.exit_code == 0, updated.stdout
    assert calls[1]["body"] == {"pack_ref": "acme/onboarding@1.0.0", "position": 0}
    assert calls[3]["body"] == {"pack_ref": "acme/onboarding@1.2.0"}


def test_cli_pack_read_commands_show_empty_messages(monkeypatch) -> None:
    from agh.cli import main as cli_main

    responses = {
        "/packs": {"packs": []},
        "/projects/prj_1/packs": {"project_packs": []},
    }

    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda _method, path, **_kwargs: responses[path],
    )
    runner = CliRunner()

    packs = runner.invoke(cli_app, ["pack", "list"])
    assignments = runner.invoke(cli_app, ["project", "pack", "list", "prj_1"])

    assert packs.exit_code == 0, packs.stdout
    assert packs.stdout == "No packs found.\n"
    assert assignments.exit_code == 0, assignments.stdout
    assert assignments.stdout == "No assigned packs found.\n"


def test_cli_pack_publish_local_validation_errors_exit_2_without_api_call(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    bad_pack = tmp_path / "bad-pack"
    bad_pack.mkdir()
    (bad_pack / "agh.pack.toml").write_text(
        'domain = "acme"\nname = "bad"\nversion = "1.0.0"\ndescription = "desc"\n',
        encoding="utf-8",
    )
    try:
        result = CliRunner().invoke(
            cli_app, ["pack", "publish", str(bad_pack)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "at least one instruction file or skill" in result.stdout
    assert handler.requests == []


def test_cli_pack_publish_refuses_symlinked_manifest_before_reading(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    pack_dir = _pack_dir(tmp_path)
    outside = tmp_path / "outside.toml"
    outside.write_text("not valid toml =", encoding="utf-8")
    (pack_dir / "agh.pack.toml").unlink()
    (pack_dir / "agh.pack.toml").symlink_to(outside)
    try:
        result = CliRunner().invoke(
            cli_app, ["pack", "publish", str(pack_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "symlinked pack path" in result.stdout
    assert "invalid agh.pack.toml" not in result.stdout
    assert handler.requests == []


def test_cli_pack_publish_refuses_symlinked_instruction_directory(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    pack_dir = _pack_dir(tmp_path)
    outside = tmp_path / "outside-instructions"
    outside.mkdir()
    (outside / "AGENTS.md").write_text("secret", encoding="utf-8")
    for child in (pack_dir / "instructions").iterdir():
        child.unlink()
    (pack_dir / "instructions").rmdir()
    (pack_dir / "instructions").symlink_to(outside, target_is_directory=True)
    try:
        result = CliRunner().invoke(
            cli_app, ["pack", "publish", str(pack_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "symlinked pack path" in result.stdout
    assert handler.requests == []


def test_cli_pack_publish_refuses_oversized_manifest_before_parsing(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    pack_dir = _pack_dir(tmp_path)
    (pack_dir / "agh.pack.toml").write_text(
        "x" * (MAX_PACK_FILE_BYTES + 1), encoding="utf-8"
    )
    try:
        result = CliRunner().invoke(
            cli_app, ["pack", "publish", str(pack_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "too large" in result.stdout
    assert "invalid agh.pack.toml" not in result.stdout
    assert handler.requests == []


def test_cli_pack_publish_refuses_symlinked_parent_path(tmp_path: Path) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    outside = tmp_path / "outside"
    outside.mkdir()
    pack_dir = _pack_dir(outside)
    link = tmp_path / "link"
    link.symlink_to(outside, target_is_directory=True)
    symlinked_pack_dir = link / pack_dir.name
    try:
        result = CliRunner().invoke(
            cli_app, ["pack", "publish", str(symlinked_pack_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "must not contain symlinks" in result.stdout
    assert handler.requests == []


def test_cli_pack_publish_refuses_binary_manifest_and_oversized_files(
    tmp_path: Path,
) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    pack_dir = _pack_dir(tmp_path)
    (pack_dir / "agh.pack.toml").write_bytes(b"\xff\xfe\x00")
    try:
        binary = CliRunner().invoke(
            cli_app, ["pack", "publish", str(pack_dir)], env=env
        )
        (pack_dir / "agh.pack.toml").write_text(
            'domain = "acme"\nname = "onboarding"\nversion = "1.0.0"\n'
            'description = "desc"\n',
            encoding="utf-8",
        )
        (pack_dir / "instructions" / "AGENTS.md").write_text(
            "x" * (MAX_PACK_FILE_BYTES + 1), encoding="utf-8"
        )
        oversized = CliRunner().invoke(
            cli_app, ["pack", "publish", str(pack_dir)], env=env
        )
    finally:
        server.shutdown()

    assert binary.exit_code == 2
    assert "codec" in binary.stdout or "UTF-8" in binary.stdout
    assert oversized.exit_code == 2
    assert "too large" in oversized.stdout
    assert handler.requests == []


def test_cli_pack_publish_refuses_too_many_allowed_files(tmp_path: Path) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    pack_dir = _pack_dir(tmp_path)
    skills_dir = pack_dir / "skills"
    for index in range(MAX_PACK_FILES):
        skill_dir = skills_dir / f"skill-{index}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("use this skill\n", encoding="utf-8")
    try:
        result = CliRunner().invoke(
            cli_app, ["pack", "publish", str(pack_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "more than" in result.stdout or "too many" in result.stdout
    assert handler.requests == []


def test_cli_pack_publish_refuses_unexpected_hidden_files(tmp_path: Path) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    pack_dir = _pack_dir(tmp_path)
    (pack_dir / ".env").write_text("SECRET=1\n", encoding="utf-8")
    try:
        result = CliRunner().invoke(
            cli_app, ["pack", "publish", str(pack_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "unexpected pack file path" in result.stdout
    assert handler.requests == []


def test_cli_pack_publish_refuses_symlinked_pack_paths(tmp_path: Path) -> None:
    server, handler, url = _serve_api()
    env = _write_config(tmp_path, url)
    pack_dir = _pack_dir(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    (pack_dir / "instructions" / "LEAK.md").symlink_to(outside)
    try:
        result = CliRunner().invoke(
            cli_app, ["pack", "publish", str(pack_dir)], env=env
        )
    finally:
        server.shutdown()

    assert result.exit_code == 2
    assert "symlinked pack path" in result.stdout
    assert handler.requests == []


def test_cli_pack_help_is_discoverable() -> None:
    runner = CliRunner()

    pack_help = runner.invoke(cli_app, ["pack", "--help"])
    project_pack_help = runner.invoke(cli_app, ["project", "pack", "--help"])
    project_pack_add_help = runner.invoke(cli_app, ["project", "pack", "add", "--help"])
    publish_help = runner.invoke(cli_app, ["pack", "publish", "--help"])
    init_help = runner.invoke(cli_app, ["pack", "init", "--help"])

    assert pack_help.exit_code == 0
    assert "init" in pack_help.stdout
    assert "publish" in pack_help.stdout
    assert "list" in pack_help.stdout
    assert project_pack_help.exit_code == 0
    assert "add" in project_pack_help.stdout
    assert "remove" in project_pack_help.stdout
    assert project_pack_add_help.exit_code == 0
    assert "packv_" in project_pack_add_help.stdout
    assert "name@version" in project_pack_add_help.stdout
    assert publish_help.exit_code == 0
    assert "PATH" in publish_help.stdout or "path" in publish_help.stdout
    assert init_help.exit_code == 0
    assert "--domain" in init_help.stdout
    assert "--with-skill" in init_help.stdout
