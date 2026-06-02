"""Local pack template scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from agh.common.validation import is_semver, is_valid_slug


class PackInitError(ValueError):
    """Raised when a pack template cannot be initialized."""


@dataclass(frozen=True)
class PackInitResult:
    """Paths created by pack init."""

    root: Path
    manifest: Path
    created_files: tuple[Path, ...]


def init_pack_template(
    path: Path,
    *,
    domain: str,
    name: str,
    version: str,
    description: str = "TODO",
    with_agents: bool = False,
    with_claude: bool = False,
    skills: list[str] | None = None,
) -> PackInitResult:
    """Create a local pack template directory."""
    if not is_valid_slug(domain):
        raise PackInitError(f"invalid domain: {domain}")
    if not is_valid_slug(name):
        raise PackInitError(f"invalid name: {name}")
    if not is_semver(version):
        raise PackInitError(f"invalid version: {version}")
    skill_names = tuple(skills or [])
    seen_skills: set[str] = set()
    for skill in skill_names:
        if not is_valid_slug(skill):
            raise PackInitError(f"invalid skill name: {skill}")
        if skill in seen_skills:
            raise PackInitError(f"duplicate skill name: {skill}")
        seen_skills.add(skill)

    root = path.expanduser()
    if root.exists():
        raise PackInitError(f"pack path already exists: {path}")

    manifest_text = _manifest_template(
        domain=domain, name=name, version=version, description=description
    )
    created_files: list[Path] = []
    try:
        (root / "instructions").mkdir(parents=True)
        (root / "skills").mkdir()
        manifest = root / "agh.pack.toml"
        manifest.write_text(manifest_text, encoding="utf-8")
        created_files.append(manifest)

        if with_agents:
            agents = root / "instructions" / "AGENTS.md"
            agents.write_text("# AGENTS\n\n", encoding="utf-8")
            created_files.append(agents)
        if with_claude:
            claude = root / "instructions" / "CLAUDE.md"
            claude.write_text("# CLAUDE\n\n", encoding="utf-8")
            created_files.append(claude)
        for skill in skill_names:
            skill_file = root / "skills" / skill / "SKILL.md"
            skill_file.parent.mkdir()
            skill_file.write_text(f"# {skill}\n\n", encoding="utf-8")
            created_files.append(skill_file)
    except Exception as exc:
        raise PackInitError(f"failed to initialize pack: {exc}") from exc

    return PackInitResult(
        root=root,
        manifest=root / "agh.pack.toml",
        created_files=tuple(created_files),
    )


def _manifest_template(
    *, domain: str, name: str, version: str, description: str
) -> str:
    return (
        f"domain = {_toml_string(domain)}\n"
        f"name = {_toml_string(name)}\n"
        f"version = {_toml_string(version)}\n"
        f"description = {_toml_string(description)}\n"
    )


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
