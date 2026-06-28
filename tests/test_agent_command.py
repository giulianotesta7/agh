from __future__ import annotations

import os
from pathlib import Path
import tomllib

from pytest import MonkeyPatch
from typer.testing import CliRunner

from agh.cli.agent_integrations import detect_agent_availability
from agh.cli.main import app as cli_app


def test_top_level_help_lists_agent_command() -> None:
    result = CliRunner().invoke(cli_app, ["--help"])

    assert result.exit_code == 0
    assert "agent" in result.stdout
    assert "Show and manage local agent selection" in result.stdout


def test_agent_command_absent_agents_exits_zero_without_writes(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())

    result = runner.invoke(cli_app, ["agent"], env={"PATH": os.devnull})

    assert result.exit_code == 0, result.stdout
    assert "Selection: not set" in result.stdout
    assert "Claude Code: ✗ not found" in result.stdout
    assert "OpenCode: ✗ not found" in result.stdout
    assert set(tmp_path.iterdir()) == before


def test_agent_unknown_subcommand_exits_2_with_local_help() -> None:
    runner = CliRunner()
    root_help = runner.invoke(cli_app, []).stdout
    result = runner.invoke(cli_app, ["agent", "wrong-command"])

    assert result.exit_code == 2
    assert "Show and manage local agent selection" in result.stdout
    assert result.stdout != root_help


def test_agent_select_show_and_clear_manage_workspace_preference(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    select = runner.invoke(cli_app, ["agent", "select", "claude"])

    assert select.exit_code == 0, select.stdout
    assert "Selected Claude Code for this workspace." in select.stdout
    preferences_path = tmp_path / ".agh-cache" / "preferences.toml"
    preferences = tomllib.loads(preferences_path.read_text(encoding="utf-8"))
    assert preferences["agents"]["target"] == "claude"
    assert isinstance(preferences["agents"]["selected_at"], str)

    show = runner.invoke(cli_app, ["agent", "show"], env={"PATH": os.devnull})

    assert show.exit_code == 0, show.stdout
    assert "Selection: Claude Code (claude)" in show.stdout
    assert "OpenCode: ✗ not found" in show.stdout

    clear = runner.invoke(cli_app, ["agent", "clear"])

    assert clear.exit_code == 0, clear.stdout
    assert "Cleared local agent selection." in clear.stdout
    assert not preferences_path.exists()


def test_agent_select_rejects_unsupported_target(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli_app, ["agent", "select", "both"])

    assert result.exit_code == 2
    assert "agent target must be 'claude' or 'opencode'" in result.stdout
    assert not (tmp_path / ".agh-cache" / "preferences.toml").exists()


def test_agent_detection_uses_path_commands(tmp_path: Path) -> None:
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


def test_agent_detection_uses_workspace_directories(tmp_path: Path) -> None:
    (tmp_path / ".opencode").mkdir()

    agents = detect_agent_availability(workspace=tmp_path, path=os.devnull)

    by_name = {agent.name: agent for agent in agents}
    assert by_name["Claude Code"].available is False
    assert by_name["OpenCode"].available is True
    assert by_name["OpenCode"].workspace_dir_exists is True
