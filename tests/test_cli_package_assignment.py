"""Phase 4: Package assignment UX (``cli-command-ux`` delta).

Covers the ``Package assignment is target-based and unambiguous`` and ``Latest
package describe resolves to highest version`` requirements:

* ``package assign|activate|deactivate|unassign PACKAGE_REF
  (--project PROJECT_REF | --collection COLLECTION_REF)`` with mutually
  exclusive target flags and no positional target / ``--position``
* ``package list`` accepts the same mutually exclusive target flags to scope the
  listing to one assignment table
* ``package describe PACKAGE_REF`` resolves ``@latest`` to the highest SemVer
* legacy ``project package`` and ``collection package`` subgroups are removed
  (breaking) and exit 2 as unsupported subgroup commands
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest
from typer.testing import CliRunner

from agh.cli.main import app as cli_app

PACKAGE_REF_HELP_TOKENS = ("PACKAGE_REF", "name@version", "pkgv_")
TARGET_REQUIRED_MESSAGE = (
    "package assignment requires exactly one of --project or --collection"
)


# ---------------------------------------------------------------------------
# Mutually exclusive target flags
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("verb", ["assign", "activate", "deactivate", "unassign"])
def test_package_assignment_verbs_require_exactly_one_target(monkeypatch, verb) -> None:
    from agh.cli import main as cli_main

    calls: list[dict[str, Any]] = []

    def fake_api_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, **kwargs})
        raise AssertionError(f"must not call API for usage error: {method} {path}")

    monkeypatch.setattr(cli_main, "_api_request", fake_api_request)
    runner = CliRunner()

    neither = runner.invoke(cli_app, ["package", verb, "acme/onboarding@latest"])
    both = runner.invoke(
        cli_app,
        [
            "package",
            verb,
            "acme/onboarding@latest",
            "--project",
            "prj_1",
            "--collection",
            "col_1",
        ],
    )

    assert neither.exit_code == 2, neither.stdout
    assert TARGET_REQUIRED_MESSAGE in neither.stdout
    assert both.exit_code == 2, both.stdout
    assert TARGET_REQUIRED_MESSAGE in both.stdout
    assert calls == []


def test_package_list_rejects_both_target_flags(monkeypatch) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(
        cli_main, "_api_request", lambda *_args, **_kwargs: {"packages": []}
    )
    result = CliRunner().invoke(
        cli_app, ["package", "list", "--project", "prj_1", "--collection", "col_1"]
    )

    assert result.exit_code == 2
    assert TARGET_REQUIRED_MESSAGE in result.stdout


# ---------------------------------------------------------------------------
# assign
# ---------------------------------------------------------------------------


def test_package_assign_posts_to_project_without_position(monkeypatch) -> None:
    from agh.cli import main as cli_main

    calls: list[dict[str, Any]] = []

    def fake_api_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, **kwargs})
        if (method, path) == ("POST", "/projects/prj_1/packages"):
            return {
                "id": "asn_1",
                "package_ref": "acme/onboarding@latest",
                "resolved_ref": "acme/onboarding@1.2.0",
            }
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(cli_main, "_api_request", fake_api_request)
    monkeypatch.setattr(cli_main, "_resolve_project_ref", lambda ref: ref)

    result = CliRunner().invoke(
        cli_app,
        ["package", "assign", "acme/onboarding@latest", "--project", "prj_1"],
    )

    assert result.exit_code == 0, result.stdout
    assert calls == [
        {
            "method": "POST",
            "path": "/projects/prj_1/packages",
            "body": {"package_ref": "acme/onboarding@latest"},
        }
    ]
    assert "Assigned acme/onboarding@latest to project prj_1." in result.stdout
    assert "Resolved: acme/onboarding@1.2.0" in result.stdout
    # Assignment ids stay internal.
    assert "asn_1" not in result.stdout


def test_package_assign_posts_to_collection(monkeypatch) -> None:
    from agh.cli import main as cli_main

    calls: list[dict[str, Any]] = []

    def fake_api_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, **kwargs})
        if (method, path) == ("POST", "/collections/col_1/packages"):
            return {
                "id": "casn_1",
                "package_ref": "acme/skills@latest",
                "resolved_ref": "acme/skills@2.0.0",
            }
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(cli_main, "_api_request", fake_api_request)
    monkeypatch.setattr(cli_main, "_resolve_collection_ref", lambda ref: ref)

    result = CliRunner().invoke(
        cli_app,
        ["package", "assign", "acme/skills@latest", "--collection", "col_1"],
    )

    assert result.exit_code == 0, result.stdout
    assert calls[0]["path"] == "/collections/col_1/packages"
    assert calls[0]["body"] == {"package_ref": "acme/skills@latest"}
    assert "Assigned acme/skills@latest to collection col_1." in result.stdout


def test_package_assign_resolves_exact_project_name_through_real_resolver(
    monkeypatch,
) -> None:
    """Public ref-resolution works end-to-end through ``package assign``.

    Coverage hardening (not a fresh RED/GREEN cycle): an exact project name
    passed to ``--project`` resolves through the real
    ``/projects/by-name/{name}`` resolver before the assignment POST, proving
    the new ``package assign`` surface preserves public project-ref resolution
    (exact-name resolution + canonical-id passthrough).
    """
    from agh.cli import main as cli_main

    calls: list[dict[str, Any]] = []

    def fake_api_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, **kwargs})
        if (method, path) == ("GET", "/projects/by-name/onboarding-platform"):
            return {"id": "prj_42"}
        if (method, path) == ("POST", "/projects/prj_42/packages"):
            return {
                "id": "asn_1",
                "package_ref": "acme/onboarding@latest",
                "resolved_ref": "acme/onboarding@1.2.0",
            }
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(cli_main, "_api_request", fake_api_request)
    # Deliberately do NOT monkeypatch _resolve_project_ref: exercise the real
    # project ref resolver through the package assign surface.

    result = CliRunner().invoke(
        cli_app,
        [
            "package",
            "assign",
            "acme/onboarding@latest",
            "--project",
            "onboarding-platform",
        ],
    )

    assert result.exit_code == 0, result.stdout
    paths = [(call["method"], call["path"]) for call in calls]
    assert ("GET", "/projects/by-name/onboarding-platform") in paths
    assert ("POST", "/projects/prj_42/packages") in paths
    assert "Assigned acme/onboarding@latest to project prj_42." in result.stdout


# ---------------------------------------------------------------------------
# assign: server-side skill-only rejection surfaces (failure path)
# ---------------------------------------------------------------------------


class _SkillOnlyRejectionHandler(BaseHTTPRequestHandler):
    """Stub that rejects a collection package POST as a skill-only violation."""

    received: ClassVar[list[tuple[str, str]]] = []

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        type(self).received.append((self.command, self.path))
        self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {
                    "detail": "package contains instructions and cannot be used "
                    "as a collection skill"
                }
            ).encode("utf-8")
        )

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib API
        return


def _serve_skill_only_rejection() -> tuple[
    ThreadingHTTPServer, type[_SkillOnlyRejectionHandler], str
]:
    _SkillOnlyRejectionHandler.received = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SkillOnlyRejectionHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, _SkillOnlyRejectionHandler, f"http://127.0.0.1:{server.server_port}"


def _write_assignment_config(tmp_path: Path, url: str) -> dict[str, str]:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f'instance_url = "{url}"\nemail = "owner@example.com"\n'
        'token = "stored-secret-token"\n',
        encoding="utf-8",
    )
    return {"AGH_CONFIG_FILE": str(config_path)}


def test_package_assign_collection_surfaces_server_skill_only_rejection(
    tmp_path: Path, monkeypatch
) -> None:
    """Assigning an instruction-bearing package to a collection surfaces the
    server's 400 skill-only rejection as a CLI error (non-zero exit, server
    detail visible), never a silent success.

    Restores the failure-path coverage previously provided by
    ``test_cli_collection_package_add_surfaces_server_skill_only_rejection`` on
    the new unified ``package assign --collection`` surface, exercising the real
    ``_api_request`` error path against a stubbed HTTP server.
    """
    from agh.cli import main as cli_main

    # Skip the version + collection ref resolvers so the only real network call
    # is the assignment POST, exercising the real ``_api_request`` error path.
    monkeypatch.setattr(cli_main, "_resolve_package_version_ref", lambda ref: ref)
    monkeypatch.setattr(cli_main, "_resolve_collection_ref", lambda ref: ref)

    server, handler, url = _serve_skill_only_rejection()
    env = _write_assignment_config(tmp_path, url)
    try:
        result = CliRunner().invoke(
            cli_app,
            ["package", "assign", "acme/instructions@latest", "--collection", "col_1"],
            env=env,
        )
    finally:
        server.shutdown()

    # 400 is not an auth failure: exit non-zero with the server detail surfaced.
    assert result.exit_code == 1, result.stdout
    assert "HTTP 400" in result.stdout
    assert (
        "package contains instructions and cannot be used as a collection skill"
        in result.stdout
    )
    # The CLI never claims success and forwards the assignment POST verbatim.
    assert "Assigned" not in result.stdout
    assert ("POST", "/api/v1/collections/col_1/packages") in handler.received


# ---------------------------------------------------------------------------
# activate / deactivate / unassign (lookup by package ref)
# ---------------------------------------------------------------------------


def _assignment_api_factory(monkeypatch, *, scope: str) -> list[dict[str, Any]]:
    """Wire a fake API where project/collection prj_1/col_1 has one assignment."""
    calls: list[dict[str, Any]] = []
    base = f"/{scope}s"

    def fake_api_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, **kwargs})
        target_id = "prj_1" if scope == "project" else "col_1"
        if (method, path) == ("GET", f"{base}/{target_id}/packages"):
            return {
                f"{scope}_packages": [
                    {
                        "id": "asn_1" if scope == "project" else "casn_1",
                        "package_ref": "acme/onboarding@latest",
                        "resolved_ref": "acme/onboarding@1.2.0",
                        "domain": "acme",
                        "name": "onboarding",
                        "active": True,
                    }
                ]
            }
        assignment_id = "asn_1" if scope == "project" else "casn_1"
        if (method, path) == ("PATCH", f"{base}/{target_id}/packages/{assignment_id}"):
            return {
                "id": assignment_id,
                "package_ref": "acme/onboarding@latest",
                "resolved_ref": "acme/onboarding@1.2.0",
                "active": kwargs["body"].get("active", True),
            }
        if (method, path) == ("DELETE", f"{base}/{target_id}/packages/{assignment_id}"):
            return {"id": assignment_id, "active": False}
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(cli_main_module(), "_api_request", fake_api_request)
    return calls


def cli_main_module():
    from agh.cli import main as cli_main

    return cli_main


def test_package_activate_patches_project_assignment_active(monkeypatch) -> None:
    from agh.cli import main as cli_main

    calls = _assignment_api_factory(monkeypatch, scope="project")
    monkeypatch.setattr(cli_main, "_resolve_project_ref", lambda ref: ref)

    result = CliRunner().invoke(
        cli_app,
        ["package", "activate", "acme/onboarding@1.2.0", "--project", "prj_1"],
    )

    assert result.exit_code == 0, result.stdout
    # Lookup then patch.
    paths = [(c["method"], c["path"]) for c in calls]
    assert ("GET", "/projects/prj_1/packages") in paths
    assert ("PATCH", "/projects/prj_1/packages/asn_1") in paths
    patch_call = next(c for c in calls if c["method"] == "PATCH")
    assert patch_call["body"] == {"active": True}
    # Output echoes the assignment's stored package_ref + resolved version.
    assert "Activated acme/onboarding@latest on project prj_1." in result.stdout
    assert "Resolved: acme/onboarding@1.2.0" in result.stdout


def test_package_deactivate_patches_collection_assignment_inactive(monkeypatch) -> None:
    from agh.cli import main as cli_main

    calls = _assignment_api_factory(monkeypatch, scope="collection")
    monkeypatch.setattr(cli_main, "_resolve_collection_ref", lambda ref: ref)

    result = CliRunner().invoke(
        cli_app,
        ["package", "deactivate", "acme/onboarding@latest", "--collection", "col_1"],
    )

    assert result.exit_code == 0, result.stdout
    patch_call = next(c for c in calls if c["method"] == "PATCH")
    assert patch_call["path"] == "/collections/col_1/packages/casn_1"
    assert patch_call["body"] == {"active": False}
    assert "Deactivated acme/onboarding@latest on collection col_1." in result.stdout


def test_package_unassign_deletes_project_assignment(monkeypatch) -> None:
    from agh.cli import main as cli_main

    calls = _assignment_api_factory(monkeypatch, scope="project")
    monkeypatch.setattr(cli_main, "_resolve_project_ref", lambda ref: ref)

    result = CliRunner().invoke(
        cli_app,
        ["package", "unassign", "acme/onboarding@1.2.0", "--project", "prj_1"],
    )

    assert result.exit_code == 0, result.stdout
    delete_call = next(c for c in calls if c["method"] == "DELETE")
    assert delete_call["path"] == "/projects/prj_1/packages/asn_1"
    assert "Removed acme/onboarding@1.2.0 from project prj_1." in result.stdout


def test_package_activate_names_package_ref_and_target_when_unassigned(
    monkeypatch,
) -> None:
    """Task 4.3: assignment errors must name the package ref and target."""
    from agh.cli import main as cli_main

    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda method, path, **kwargs: {"project_packages": []},
    )
    monkeypatch.setattr(cli_main, "_resolve_project_ref", lambda ref: ref)

    result = CliRunner().invoke(
        cli_app,
        ["package", "activate", "acme/onboarding@latest", "--project", "prj_1"],
    )

    assert result.exit_code == 1, result.stdout
    assert "acme/onboarding@latest" in result.stdout
    assert "project" in result.stdout
    assert "prj_1" in result.stdout
    assert "package list --project" in result.stdout


# ---------------------------------------------------------------------------
# scoped package list
# ---------------------------------------------------------------------------


def test_package_list_scoped_to_project_renders_assignment_table(monkeypatch) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(cli_main, "_resolve_project_ref", lambda ref: ref)
    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda method, path, **kwargs: {
            "project_packages": [
                {
                    "id": "asn_1",
                    "package_ref": "acme/onboarding@latest",
                    "resolved_ref": "acme/onboarding@1.2.0",
                    "active": True,
                }
            ]
        },
    )

    result = CliRunner().invoke(cli_app, ["package", "list", "--project", "prj_1"])

    assert result.exit_code == 0, result.stdout
    header, *rows = result.stdout.splitlines()
    assert header.split() == ["PACKAGE_REF", "RESOLVED", "STATUS"]
    assert rows[0].split() == [
        "acme/onboarding@latest",
        "acme/onboarding@1.2.0",
        "active",
    ]
    # No assignment ids or positions in the public table.
    assert "asn_1" not in result.stdout
    assert "POSITION" not in result.stdout


def test_package_list_scoped_empty_reports_no_assignments(monkeypatch) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(cli_main, "_resolve_collection_ref", lambda ref: ref)
    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda method, path, **kwargs: {"collection_packages": []},
    )

    result = CliRunner().invoke(cli_app, ["package", "list", "--collection", "col_1"])

    assert result.exit_code == 0, result.stdout
    assert result.stdout == "No assigned packages found.\n"


# ---------------------------------------------------------------------------
# describe with @latest resolution
# ---------------------------------------------------------------------------


def test_package_describe_resolves_latest_to_highest_semver(monkeypatch) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda method, path, **kwargs: {
            "packages": [
                {
                    "id": "acme/onboarding@1.0.0",
                    "package_id": "pkg_1",
                    "domain": "acme",
                    "name": "onboarding",
                    "version": "1.0.0",
                    "description": "First release.",
                    "checksum": "sha256:" + "a" * 64,
                },
                {
                    "id": "acme/onboarding@1.2.0",
                    "package_id": "pkg_1",
                    "domain": "acme",
                    "name": "onboarding",
                    "version": "1.2.0",
                    "description": "Latest release.",
                    "checksum": "sha256:" + "b" * 64,
                },
                {
                    "id": "acme/onboarding@1.10.0",
                    "package_id": "pkg_1",
                    "domain": "acme",
                    "name": "onboarding",
                    "version": "1.10.0",
                    "description": "Newer release.",
                    "checksum": "sha256:" + "c" * 64,
                },
            ]
        },
    )

    result = CliRunner().invoke(
        cli_app, ["package", "describe", "acme/onboarding@latest"]
    )

    assert result.exit_code == 0, result.stdout
    # Highest SemVer is 1.10.0, not 1.2.0 (string sort trap).
    assert "Package: acme/onboarding@1.10.0" in result.stdout
    assert "Newer release." in result.stdout


def test_package_describe_exact_version_describes_that_version(monkeypatch) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda method, path, **kwargs: {
            "packages": [
                {
                    "id": "acme/onboarding@1.0.0",
                    "package_id": "pkg_1",
                    "domain": "acme",
                    "name": "onboarding",
                    "version": "1.0.0",
                    "description": "First release.",
                    "checksum": "sha256:" + "a" * 64,
                },
                {
                    "id": "acme/onboarding@2.0.0",
                    "package_id": "pkg_1",
                    "domain": "acme",
                    "name": "onboarding",
                    "version": "2.0.0",
                    "description": "Newer release.",
                    "checksum": "sha256:" + "b" * 64,
                },
            ]
        },
    )

    result = CliRunner().invoke(
        cli_app, ["package", "describe", "acme/onboarding@1.0.0"]
    )

    assert result.exit_code == 0, result.stdout
    assert "Package: acme/onboarding@1.0.0" in result.stdout
    assert "First release." in result.stdout
    assert "2.0.0" not in result.stdout


def test_package_describe_unknown_package_fails(monkeypatch) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda method, path, **kwargs: {"packages": []},
    )

    result = CliRunner().invoke(cli_app, ["package", "describe", "acme/missing@latest"])

    assert result.exit_code == 1, result.stdout
    assert "acme/missing@latest" in result.stdout


def test_package_describe_latest_fetches_packages_once(monkeypatch) -> None:
    """Regression: ``package describe @latest`` must not fetch ``/packages`` twice.

    ``@latest`` SemVer resolution and the describe lookup previously each issued
    ``GET /packages`` (two round-trips). The redundant fetch is removed while
    preserving SemVer-aware resolution and the detail output. This is the
    observable efficiency contract for the describe path.
    """
    from agh.cli import main as cli_main

    calls: list[tuple[str, str]] = []

    def fake_api_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append((method, path))
        return {
            "packages": [
                {
                    "id": "acme/onboarding@1.10.0",
                    "package_id": "pkg_1",
                    "domain": "acme",
                    "name": "onboarding",
                    "version": "1.10.0",
                    "description": "Latest release.",
                    "checksum": "sha256:" + "c" * 64,
                },
            ]
        }

    monkeypatch.setattr(cli_main, "_api_request", fake_api_request)

    result = CliRunner().invoke(
        cli_app, ["package", "describe", "acme/onboarding@latest"]
    )

    assert result.exit_code == 0, result.stdout
    package_gets = [call for call in calls if call == ("GET", "/packages")]
    assert len(package_gets) == 1, calls
    assert "Package: acme/onboarding@1.10.0" in result.stdout


# ---------------------------------------------------------------------------
# legacy removal (breaking)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["project", "package", "list", "prj_1"],
        ["project", "package", "add", "prj_1", "acme/onboarding@latest"],
        ["project", "package", "update", "prj_1", "asn_1", "--inactive"],
        ["project", "package", "remove", "prj_1", "asn_1"],
        ["collection", "package", "list", "col_1"],
        ["collection", "package", "add", "col_1", "acme/onboarding@latest"],
        ["collection", "package", "update", "col_1", "casn_1", "--inactive"],
        ["collection", "package", "remove", "col_1", "casn_1"],
    ],
)
def test_legacy_nested_package_commands_are_not_supported(argv) -> None:
    """Phase 4 breaking policy: nested project/collection package assignment
    (list/add/update/remove) is removed and exits 2 as unsupported."""
    result = CliRunner().invoke(cli_app, argv)
    assert result.exit_code == 2, (argv, result.stdout)


# ---------------------------------------------------------------------------
# help / discovery
# ---------------------------------------------------------------------------


def test_package_help_advertises_assignment_verbs_and_describe() -> None:
    runner = CliRunner()
    package_help = runner.invoke(cli_app, ["package", "--help"])

    assert package_help.exit_code == 0, package_help.stdout
    for verb in ["list", "describe", "assign", "activate", "deactivate", "unassign"]:
        assert verb in package_help.stdout, verb


def test_package_assign_help_uses_ref_metavars() -> None:
    runner = CliRunner()
    assign_help = runner.invoke(cli_app, ["package", "assign", "--help"])

    assert assign_help.exit_code == 0, assign_help.stdout
    for token in PACKAGE_REF_HELP_TOKENS:
        assert token in assign_help.stdout, token
    assert "--project" in assign_help.stdout
    assert "--collection" in assign_help.stdout
    # No legacy positional target or position.
    assert "--position" not in assign_help.stdout
