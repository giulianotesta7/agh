"""Advisory local agent integration detection and workspace preferences."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
import shutil
import tempfile
import tomllib

SUPPORTED_AGENT_TARGETS = ("claude", "opencode")
AGENT_LABELS = {"claude": "Claude Code", "opencode": "OpenCode"}


class AgentPreferenceError(RuntimeError):
    """Raised for invalid local agent preference operations."""

    def __init__(self, message: str, *, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AgentAvailability:
    """Advisory availability for a local agent integration."""

    name: str
    command: str
    workspace_dir: str
    available: bool
    command_path: str | None
    workspace_dir_exists: bool


@dataclass(frozen=True)
class AgentPreference:
    """Local per-developer agent target selection for one workspace."""

    target: str
    selected_at: str | None
    path: Path

    @property
    def label(self) -> str:
        return AGENT_LABELS[self.target]


def agent_preferences_path(workspace: Path | None = None) -> Path:
    """Return the local workspace preferences TOML path."""
    root = Path.cwd() if workspace is None else workspace
    return root.resolve() / ".agh-cache" / "preferences.toml"


def read_agent_preference(workspace: Path | None = None) -> AgentPreference | None:
    """Read local workspace agent preference, if present."""
    path = agent_preferences_path(workspace)
    if path.parent.is_symlink():
        raise AgentPreferenceError("refusing to read symlinked AGH preferences")
    if path.parent.exists() and not path.parent.is_dir():
        raise AgentPreferenceError(f"non-directory AGH cache path: {path.parent}")
    if not path.exists():
        return None
    if path.is_symlink():
        raise AgentPreferenceError("refusing to read symlinked AGH preferences")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise AgentPreferenceError(f"invalid AGH preferences: {exc}") from exc
    except OSError as exc:
        raise AgentPreferenceError(f"failed to read AGH preferences: {exc}") from exc
    agents = data.get("agents") if isinstance(data, dict) else None
    if not isinstance(agents, dict):
        raise AgentPreferenceError("AGH preferences missing [agents]")
    target = agents.get("target")
    if not isinstance(target, str) or target not in SUPPORTED_AGENT_TARGETS:
        raise AgentPreferenceError(
            "AGH preferences agents.target must be 'claude' or 'opencode'"
        )
    selected_at = agents.get("selected_at")
    if selected_at is not None and not isinstance(selected_at, str):
        raise AgentPreferenceError(
            "AGH preferences agents.selected_at must be a string"
        )
    return AgentPreference(target=target, selected_at=selected_at, path=path)


def write_agent_preference(
    target: str, *, workspace: Path | None = None
) -> AgentPreference:
    """Atomically write the local workspace agent preference."""
    if target not in SUPPORTED_AGENT_TARGETS:
        raise AgentPreferenceError("agent target must be 'claude' or 'opencode'")
    path = agent_preferences_path(workspace)
    cache_dir = path.parent
    if cache_dir.is_symlink():
        raise AgentPreferenceError(
            f"refusing to write through symlinked AGH cache directory: {cache_dir}"
        )
    if cache_dir.exists() and not cache_dir.is_dir():
        raise AgentPreferenceError(f"non-directory AGH cache path: {cache_dir}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    selected_at = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    text = f'[agents]\ntarget = "{target}"\nselected_at = "{selected_at}"\n'
    fd, temp_name = tempfile.mkstemp(
        prefix=".preferences.toml.", suffix=".tmp", dir=cache_dir
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        with suppress(FileNotFoundError):
            temp_path.unlink()
        raise
    return AgentPreference(target=target, selected_at=selected_at, path=path)


def clear_agent_preference(workspace: Path | None = None) -> bool:
    """Remove the local workspace agent preference file if it exists."""
    path = agent_preferences_path(workspace)
    if path.is_symlink() or path.parent.is_symlink():
        raise AgentPreferenceError("refusing to remove symlinked AGH preferences")
    if not path.exists():
        return False
    try:
        path.unlink()
    except OSError as exc:
        raise AgentPreferenceError(f"failed to remove AGH preferences: {exc}") from exc
    return True


def format_agent_preference(preference: AgentPreference | None) -> str:
    """Render the local workspace agent preference."""
    if preference is None:
        return "Selection: not set"
    return f"Selection: {preference.label} ({preference.target})"


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


def relative_symlink_target(*, source: Path, target: Path) -> str:
    """Return a portable relative symlink target from target parent to source."""
    return os.path.relpath(source, start=target.parent)


def symlink_points_to(path: Path, expected: Path) -> bool:
    """Return whether a symlink points to the expected path without writes."""
    try:
        raw_target = os.readlink(path)
    except OSError:
        return False
    target = Path(raw_target)
    if not target.is_absolute():
        target = path.parent / target
    return target.resolve(strict=False) == expected.resolve(strict=False)


def global_skill_dir(agent: str) -> Path:
    """Return the native global skill directory for the selected agent."""
    if agent not in SUPPORTED_AGENT_TARGETS:
        raise AgentPreferenceError(
            "agent target must be 'claude' or 'opencode'", code=2
        )
    if agent == "opencode":
        return Path.home() / ".config" / "opencode" / "skills"
    return Path.home() / ".claude" / "skills"


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
