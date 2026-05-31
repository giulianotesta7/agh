"""Advisory local agent integration detection."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentAvailability:
    """Advisory availability for a local agent integration."""

    name: str
    command: str
    workspace_dir: str
    available: bool
    command_path: str | None
    workspace_dir_exists: bool


def detect_agent_availability(
    *,
    workspace: Path | None = None,
    path: str | None = None,
) -> list[AgentAvailability]:
    """Detect known local agent integrations without creating or modifying files."""
    root = Path.cwd() if workspace is None else workspace
    return [
        _detect_agent(
            name="Claude Code",
            command="claude",
            workspace_dir=".claude",
            workspace=root,
            path=path,
        ),
        _detect_agent(
            name="OpenCode",
            command="opencode",
            workspace_dir=".opencode",
            workspace=root,
            path=path,
        ),
    ]


def format_agent_availability(agents: list[AgentAvailability]) -> str:
    """Render sober, plain advisory output for `agh agent`."""
    lines: list[str] = []
    for agent in agents:
        marker = "✓" if agent.available else "✗"
        status = "available" if agent.available else "not found"
        reasons: list[str] = []
        if agent.command_path is not None:
            reasons.append(f"command: {agent.command_path}")
        if agent.workspace_dir_exists:
            reasons.append(f"workspace: {agent.workspace_dir}/")
        reason_text = f" ({', '.join(reasons)})" if reasons else ""
        lines.append(f"{agent.name}: {marker} {status}{reason_text}")
    return "\n".join(lines)


def _detect_agent(
    *,
    name: str,
    command: str,
    workspace_dir: str,
    workspace: Path,
    path: str | None,
) -> AgentAvailability:
    command_path = shutil.which(command, path=path)
    workspace_dir_exists = (workspace / workspace_dir).is_dir()
    return AgentAvailability(
        name=name,
        command=command,
        workspace_dir=workspace_dir,
        available=command_path is not None or workspace_dir_exists,
        command_path=command_path,
        workspace_dir_exists=workspace_dir_exists,
    )
