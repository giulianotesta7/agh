"""CLI target command tests (PR2: agent selection UX becomes target).

The public selection UX is `target`, backed by the same local state as the
former `agent` command:

* workspace target -> ``.agh-cache/preferences.toml`` ([agents] target)
* global target -> global-skills defaults.toml ([skills] default_agent)
"""

from __future__ import annotations

import os
from pathlib import Path
import tomllib

from pytest import MonkeyPatch
from typer.testing import CliRunner

from agh.cli.agent_integrations import detect_agent_availability
from agh.cli.main import app as cli_app


def _top_level_command_rows(help_output: str) -> list[str]:
    """Parse the maintained root command map's top-level command rows."""
    rows: list[str] = []
    in_commands = False
    for line in help_output.splitlines():
        stripped = line.strip()
        if stripped == "Commands:":
            in_commands = True
            continue
        if not in_commands or not stripped:
            continue
        if not line.startswith("  "):
            break
        if not line.startswith("    "):
            rows.append(stripped.split()[0])
    return rows


def test_top_level_help_lists_target_not_agent() -> None:
    result = CliRunner().invoke(cli_app, ["--help"])

    assert result.exit_code == 0
    assert "target" in result.stdout
    assert "Show and manage local target selection" in result.stdout
    top_level = _top_level_command_rows(result.stdout)
    assert "target" in top_level
    # the legacy top-level agent command is not advertised
    assert "agent" not in top_level


def test_target_command_absent_target_exits_zero_without_writes(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())

    result = runner.invoke(cli_app, ["target"], env={"PATH": os.devnull})

    assert result.exit_code == 0, result.stdout
    assert "not set" in result.stdout.lower()
    assert "Claude Code" in result.stdout
    assert "OpenCode" in result.stdout
    assert set(tmp_path.iterdir()) == before


def test_target_unknown_subcommand_exits_2_with_local_help() -> None:
    runner = CliRunner()
    root_help = runner.invoke(cli_app, []).stdout
    result = runner.invoke(cli_app, ["target", "wrong-command"])

    assert result.exit_code == 2
    assert "local target selection" in result.stdout.lower()
    assert result.stdout != root_help


def test_target_set_show_and_clear_manage_workspace_target(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    set_result = runner.invoke(cli_app, ["target", "set", "claude"])

    assert set_result.exit_code == 0, set_result.stdout
    assert "Claude Code" in set_result.stdout
    assert "claude" in set_result.stdout
    preferences_path = tmp_path / ".agh-cache" / "preferences.toml"
    preferences = tomllib.loads(preferences_path.read_text(encoding="utf-8"))
    assert preferences["agents"]["target"] == "claude"
    assert isinstance(preferences["agents"]["selected_at"], str)

    show = runner.invoke(cli_app, ["target"], env={"PATH": os.devnull})

    assert show.exit_code == 0, show.stdout
    assert "Claude Code" in show.stdout
    assert "claude" in show.stdout
    assert "OpenCode" in show.stdout

    clear = runner.invoke(cli_app, ["target", "clear"])

    assert clear.exit_code == 0, clear.stdout
    assert "Cleared workspace target" in clear.stdout
    assert not preferences_path.exists()


def test_target_clear_with_no_workspace_target_is_noop(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli_app, ["target", "clear"])

    assert result.exit_code == 0, result.stdout
    assert "No workspace target" in result.stdout


def test_target_set_rejects_unsupported_target(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli_app, ["target", "set", "both"])

    assert result.exit_code == 2
    assert "target must be 'claude' or 'opencode'" in result.stdout
    assert not (tmp_path / ".agh-cache" / "preferences.toml").exists()


def test_target_global_set_show_and_clear_use_defaults_file(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    defaults_dir = tmp_path / "state" / "agh" / "global-skills"
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.chdir(tmp_path)
    defaults_path = defaults_dir / "defaults.toml"

    set_result = CliRunner().invoke(cli_app, ["target", "set", "opencode", "--global"])

    assert set_result.exit_code == 0, set_result.stdout
    assert "global target" in set_result.stdout.lower()
    assert "OpenCode" in set_result.stdout
    assert defaults_path.exists()
    data = tomllib.loads(defaults_path.read_text(encoding="utf-8"))
    assert data["skills"]["default_agent"] == "opencode"

    show = CliRunner().invoke(cli_app, ["target", "--global"])
    assert show.exit_code == 0, show.stdout
    assert "OpenCode" in show.stdout
    assert "opencode" in show.stdout

    clear = CliRunner().invoke(cli_app, ["target", "clear", "--global"])
    assert clear.exit_code == 0, clear.stdout
    assert "Cleared global target" in clear.stdout
    assert not defaults_path.exists()


def test_target_global_option_before_subcommand_uses_defaults_file(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    defaults_dir = tmp_path / "state" / "agh" / "global-skills"
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.chdir(tmp_path)
    defaults_path = defaults_dir / "defaults.toml"
    preferences_path = tmp_path / ".agh-cache" / "preferences.toml"

    set_result = CliRunner().invoke(cli_app, ["target", "--global", "set", "opencode"])

    assert set_result.exit_code == 0, set_result.stdout
    assert "global target" in set_result.stdout.lower()
    assert defaults_path.exists()
    assert not preferences_path.exists()

    clear = CliRunner().invoke(cli_app, ["target", "--global", "clear"])

    assert clear.exit_code == 0, clear.stdout
    assert "Cleared global target" in clear.stdout
    assert not defaults_path.exists()


def test_target_global_clear_with_no_global_target_is_noop(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    result = CliRunner().invoke(cli_app, ["target", "clear", "--global"])

    assert result.exit_code == 0, result.stdout
    assert "No global target" in result.stdout


def test_target_global_show_when_not_set(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    result = CliRunner().invoke(cli_app, ["target", "--global"])

    assert result.exit_code == 0, result.stdout
    assert "not set" in result.stdout.lower()


def test_agent_command_is_not_available(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """The legacy `agent` command is removed; it is not a hidden alias."""
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli_app, ["agent"])

    # unknown top-level command -> root help, exit 2
    assert result.exit_code == 2


# --- backing function detection (unchanged behaviour, still covered) -------


def test_target_detection_uses_path_commands(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    claude.write_text("#!/bin/sh\n", encoding="utf-8")
    claude.chmod(0o755)

    agents = detect_agent_availability(workspace=tmp_path, path=str(bin_dir))

    by_name = {agent.name: agent for agent in agents}
    assert by_name["Claude Code"].available is True
    assert by_name["Claude Code"].command_path == str(claude)
    assert by_name["OpenCode"].available is False


def test_target_detection_uses_workspace_directories(tmp_path: Path) -> None:
    (tmp_path / ".opencode").mkdir()

    agents = detect_agent_availability(workspace=tmp_path, path=os.devnull)

    by_name = {agent.name: agent for agent in agents}
    assert by_name["Claude Code"].available is False
    assert by_name["OpenCode"].available is True
    assert by_name["OpenCode"].workspace_dir_exists is True
