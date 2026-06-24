"""CLI ``--version`` option coverage for the frozen binary version gate."""

from __future__ import annotations

from typer.testing import CliRunner

from agh import __version__ as agh_version
from agh.cli.main import app as cli_app


def test_cli_version_option_prints_agh_and_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == f"agh {agh_version}"


def test_cli_version_option_respects_version_override(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """The --version output must track agh.__version__, proving frozen metadata works."""
    monkeypatch.setattr("agh.cli.main.__version__", "9.9.9")
    runner = CliRunner()
    result = runner.invoke(cli_app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "agh 9.9.9"


def test_cli_help_still_works_after_version_option() -> None:
    """--version must not break the existing --help behavior."""
    runner = CliRunner()
    result = runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    assert "Agent Guidance Hub" in result.stdout
