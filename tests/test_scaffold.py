"""Smoke tests for Phase 1 scaffold."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from agh.cli.main import app as cli_app
from agh.server.app import DEFAULT_PORT, create_app


def test_default_port_constant() -> None:
    assert DEFAULT_PORT == 8912


def test_health_endpoint() -> None:
    application = create_app()
    client = TestClient(application)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["port"] == 8912


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    assert "Agent Guidance Hub" in result.stdout


def test_logging_creates_log_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))

    import agh.server.app as app_module

    importlib.reload(app_module)

    application = app_module.create_app()
    assert application is not None

    log_path = tmp_path / "logs" / "agh.log"
    assert log_path.is_file()
