from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_readme_consolidates_guides_and_bookmarks() -> None:
    readme = _read("README.md")

    headings = [line for line in readme.splitlines() if line.startswith("## ")]
    assert headings == [
        "## Install",
        "## Quick start",
        "## How AGH works",
        "## Server operations",
        "## Development",
    ]

    for expected in [
        "Self-hosted guidance distribution for coding agents",
        "[Español](README.es.md)",
        'href="#install"',
        'href="#quick-start"',
        'href="#how-agh-works"',
        'href="#server-operations"',
        'href="#development"',
        "assets/agh-workspace-demo.gif",
        "Centralize guidance",
        "Version every change",
        "AGH is early, Docker-first",
        "brew install giulianotesta7/tap/agh",
        "curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh",
        "uv tool install --force agh",
        "uv tool install --force .",
        "docker compose up -d",
        "curl http://127.0.0.1:8912/api/v1/health",
        "ghcr.io/giulianotesta7/agent-guidance-hub:${AGH_IMAGE_TAG:-latest}",
        "AGH_IMAGE_TAG=0.2.0 docker compose up -d",
        "/data/secrets/initial_owner_token",
        "agh login",
        "agh config show",
        "agh project create",
        "exact project names",
        "All-digit values are treated as ids",
        "agh sync",
        "agh agent select opencode",
        "agh pull --dry-run",
        "agh pull",
        "agh agent show",
        "Pack authoring",
        "Project assignment",
        "Workspace pull and Git state",
        "agh.pack.toml",
        'version = "1.0.0"',
        'description = "TODO"',
        "instructions/AGENTS.md",
        "instructions/CLAUDE.md",
        "skills/<name>/SKILL.md",
        "A pack can contain instructions, skills, or both",
        "at least one instruction file or skill",
        "Published versions are immutable",
        "Do not publish `latest`",
        "Use UTF-8 text files",
        "Do not include symlinks",
        "agh pack init ./my-pack --domain acme --name onboarding --version 1.0.0",
        "--with-skill NAME",
        "agh pack publish",
        "agh pack list",
        "Published acme/onboarding@1.0.0.",
        "agh project pack add",
        "agh project pack update",
        "agh project pack remove",
        "asn_...",
        "packv_...",
        "name@version",
        "No-domain refs must match a single pack domain",
        "latest",
        ".agh/project.toml",
        ".agh/lock.toml",
        ".agh-cache/preferences.toml",
        ".agh-cache/packs/",
        ".agh-cache/",
        "agh pull --force",
        "agh agent clear",
        "AGH-BEGIN",
        "AGH-END",
        'mode = "symlink"',
        'mode = "copy"',
        "Exit codes",
        "token = ****",
        "token hashes",
        "agh user create",
        "agh user show user@example.com",
        "exact emails",
        "agh token rotate",
        "agh token reset",
        "/data/agh.sqlite3",
        "/data/packs/",
        "/data/logs/agh.log",
        "docker run --rm -p 8912:8912 -v agh-data:/data",
        "AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com",
        "Backup",
        "Upgrade",
        "uv run uvicorn agh.server.app:app --host 0.0.0.0 --port 8912",
        "uv sync",
        "uv run pytest",
        "[Contributing](CONTRIBUTING.md)",
        "[Security](SECURITY.md)",
    ]:
        assert expected in readme

    for removed_link_or_heading in [
        "docs/installation.md",
        "docs/quickstart.md",
        "docs/packs.md",
        "docs/projects.md",
        "docs/workspace.md",
        "docs/admin.md",
        "docs/operations.md",
        "docs/assets/",
        "## Core concepts",
        "## Packs",
        "## Projects",
        "## Workspace",
        "## Git state",
        "## Admin and tokens",
        "## Operations",
        "## Status",
    ]:
        assert removed_link_or_heading not in readme


def test_spanish_readme_mirrors_consolidated_guides() -> None:
    spanish_readme = _read("README.es.md")

    headings = [line for line in spanish_readme.splitlines() if line.startswith("## ")]
    assert headings == [
        "## Instalar",
        "## Quick start",
        "## Cómo funciona AGH",
        "## Operaciones del server",
        "## Desarrollo",
    ]

    for expected in [
        "Guidance para agentes de código, self-hosted",
        "[English](README.md)",
        'href="#instalar"',
        'href="#quick-start"',
        'href="#como-funciona-agh"',
        'href="#operaciones-del-server"',
        'href="#desarrollo"',
        "assets/agh-workspace-demo.gif",
        "Centralizá el guidance",
        "Versioná cada cambio",
        "AGH está en una etapa temprana",
        "brew install giulianotesta7/tap/agh",
        "curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh",
        "uv tool install --force agh",
        "uv tool install --force .",
        "docker compose up -d",
        "curl http://127.0.0.1:8912/api/v1/health",
        "ghcr.io/giulianotesta7/agent-guidance-hub:${AGH_IMAGE_TAG:-latest}",
        "AGH_IMAGE_TAG=0.2.0 docker compose up -d",
        "/data/secrets/initial_owner_token",
        "agh login",
        "agh config show",
        "agh project create",
        "agh sync",
        "agh agent select opencode",
        "agh pull --dry-run",
        "agh pull",
        "agh agent show",
        "Autoría de packs",
        "Asignación a proyectos",
        "Pull del workspace y estado en Git",
        "agh.pack.toml",
        'version = "1.0.0"',
        'description = "TODO"',
        "Un pack puede contener instrucciones, skills o ambas",
        "al menos un archivo de instrucciones o una skill",
        "Las versiones publicadas son inmutables",
        "No publiques `latest`",
        "Usá archivos UTF-8",
        "No incluyas symlinks",
        "agh pack init ./my-pack --domain acme --name onboarding --version 1.0.0",
        "--with-skill NAME",
        "agh pack publish",
        "agh pack list",
        "Published acme/onboarding@1.0.0.",
        "agh project pack add",
        "agh project pack update",
        "agh project pack remove",
        "asn_...",
        "latest",
        ".agh/project.toml",
        ".agh/lock.toml",
        ".agh-cache/preferences.toml",
        ".agh-cache/packs/",
        ".agh-cache/",
        "agh pull --force",
        "agh agent clear",
        "AGH-BEGIN",
        "AGH-END",
        'mode = "symlink"',
        'mode = "copy"',
        "Exit codes",
        "token = ****",
        "hashes de tokens",
        "agh user create",
        "agh token rotate",
        "agh token reset",
        "/data/agh.sqlite3",
        "/data/packs/",
        "/data/logs/agh.log",
        "docker run --rm -p 8912:8912 -v agh-data:/data",
        "AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com",
        "Backup",
        "Actualizá",
        "uv run uvicorn agh.server.app:app --host 0.0.0.0 --port 8912",
        "uv sync",
        "uv run pytest",
        "[Contributing](CONTRIBUTING.md)",
        "[Security](SECURITY.md)",
    ]:
        assert expected in spanish_readme

    for removed_link_or_heading in [
        "docs/es/installation.md",
        "docs/es/quickstart.md",
        "docs/es/packs.md",
        "docs/es/projects.md",
        "docs/es/workspace.md",
        "docs/es/admin.md",
        "docs/es/operations.md",
        "docs/assets/",
        "## Conceptos",
        "## Packs",
        "## Proyectos",
        "## Workspace",
        "## Estado en Git",
        "## Admin y tokens",
        "## Estado",
    ]:
        assert removed_link_or_heading not in spanish_readme


def test_docs_guides_are_collapsed_into_readmes() -> None:
    assert Path("assets/agh-workspace-demo.gif").is_file()
    assert Path("assets/agh-workspace-demo.tape").is_file()

    demo_tape = _read("assets/agh-workspace-demo.tape")
    assert "Output assets/agh-workspace-demo.gif" in demo_tape
    assert "docs/assets/" not in demo_tape
    assert not Path("docs").exists()


def test_compose_uses_published_ghcr_image_and_data_volume() -> None:
    compose = _read("docker-compose.yml")

    for expected in [
        "services:",
        "agh:",
        "image: ghcr.io/giulianotesta7/agent-guidance-hub:${AGH_IMAGE_TAG:-latest}",
        '"8912:8912"',
        "agh-data:/data",
        "AGH_BOOTSTRAP_OWNER_EMAIL: owner@example.com",
        "volumes:",
        "agh-data:",
        "name: agh-data",
    ]:
        assert expected in compose


def test_install_cli_script_is_safe_and_uses_uv_tool_install() -> None:
    script = _read("scripts/install.sh")
    mode = Path("scripts/install.sh").stat().st_mode

    assert mode & 0o111
    for expected in [
        "set -eu",
        "command -v uv",
        "AGH_INSTALL_PACKAGE:-agh",
        "uv tool install --force",
        "agh --help",
        "uv tool update-shell",
        "uv tool dir",
    ]:
        assert expected in script
    for forbidden in [".bashrc", ".zshrc", ".profile", ">> ~/"]:
        assert forbidden not in script


def test_package_version_is_dynamic_from_git_metadata() -> None:
    pyproject = _read("pyproject.toml")
    init = _read("agh/__init__.py")
    app = _read("agh/server/app.py")

    for expected in [
        'requires = ["setuptools>=68", "setuptools-scm>=8", "wheel"]',
        'dynamic = ["version"]',
        'description = "Self-hosted guidance distribution for coding agents"',
        'license = "MIT"',
        '"Development Status :: 3 - Alpha"',
        '"Framework :: FastAPI"',
        '"coding-agents"',
        "[project.urls]",
        'Homepage = "https://github.com/giulianotesta7/AgentGuidanceHub"',
        'Container = "https://github.com/giulianotesta7/AgentGuidanceHub/pkgs/container/agent-guidance-hub"',
        "[tool.setuptools_scm]",
    ]:
        assert expected in pyproject

    assert '[project]\nname = "agh"\ndynamic = ["version"]' in pyproject
    assert "from importlib.metadata import PackageNotFoundError, version" in init
    assert '__version__ = version("agh")' in init
    assert "from agh import __version__" in app
    assert 'FastAPI(title="Agent Guidance Hub", version=__version__)' in app


def test_ci_workflow_runs_release_validation_commands() -> None:
    ci = _read(".github/workflows/ci.yml")

    for expected in [
        "pull_request:",
        "branches:",
        "- main",
        "astral-sh/setup-uv@v5",
        'python-version: "3.11"',
        "uv lock --locked",
        "uv run pytest -q",
        "uv run --with ruff ruff check .",
        "uv run --with ruff ruff format --check .",
        "uv run --with pyright pyright agh tests",
        "docker build --check .",
        "uv build",
        "uv tool install --force dist/*.whl",
        "agh --help",
    ]:
        assert expected in ci

    assert "publish" not in ci.lower()


def test_pr_validation_workflow_requires_issue_and_type_label() -> None:
    workflow = _read(".github/workflows/pr-validation.yml")
    pr_template = _read(".github/pull_request_template.md")
    feature_template = _read(".github/ISSUE_TEMPLATE/feature_request.yml")
    bug_template = _read(".github/ISSUE_TEMPLATE/bug_report.yml")
    contributing = _read("CONTRIBUTING.md")
    security = _read("SECURITY.md")

    for expected in [
        "pull_request_target:",
        "exactly one type:* label",
        "status:approved",
        "Closes #N",
        "Fixes #N",
        "Resolves #N",
    ]:
        assert expected in workflow

    for expected in ["Closes #", "type:feature", "uv run pytest"]:
        assert expected in pr_template

    for template in [feature_template, bug_template]:
        assert "status:needs-review" in template
        assert "status:approved" in template
        assert "required: true" in template

    for expected in [
        "issue-first workflow",
        "status:approved",
        "exactly one `type:*` label",
        "uv run --with pyright pyright agh tests",
    ]:
        assert expected in contributing

    for expected in [
        "Do not open a public issue for vulnerabilities",
        "giulianotesta15@gmail.com",
        "token handling and storage",
        "path traversal",
    ]:
        assert expected in security

    license_text = _read("LICENSE")
    assert "MIT License" in license_text
    assert "Copyright (c) 2026 Giuliano Testa" in license_text


def test_tag_release_workflow_publishes_package_image_and_release() -> None:
    release = _read(".github/workflows/release.yml")

    for expected in [
        "name: Release",
        "tags:",
        '"v*"',
        "contents: write",
        "id-token: write",
        "packages: write",
        "fetch-depth: 0",
        "Verify release tag is on main and highest SemVer tag",
        "Re-verify release tag before publishing latest",
        "Derive release version",
        "uv lock --locked",
        "uv run pytest -q",
        "uv run --with ruff ruff check .",
        "uv run --with ruff ruff format --check .",
        "uv run --with pyright pyright agh tests",
        "docker build --check .",
        "uv build",
        "Verify built package version",
        "environment: pypi",
        "environment: ghcr",
        "pypa/gh-action-pypi-publish@release/v1",
        "docker/build-push-action@v6",
        "AGH_VERSION=${{ needs.validate.outputs.version }}",
        "${{ env.IMAGE_NAME }}:${{ needs.validate.outputs.version }}",
        "softprops/action-gh-release@v2",
        "generate_release_notes: true",
    ]:
        assert expected in release


def test_dockerfile_documents_data_dirs_and_healthcheck() -> None:
    dockerfile = _read("Dockerfile")

    assert "ARG AGH_VERSION=0.0.0" in dockerfile
    assert "ENV AGH_DATA_DIR=/data" in dockerfile
    assert (
        "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AGH=${AGH_VERSION} uv sync --locked --no-dev"
        in dockerfile
    )
    assert "mkdir -p /data/logs /data/secrets /data/packs" in dockerfile
    assert "EXPOSE 8912" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "127.0.0.1:8912/api/v1/health" in dockerfile
    assert "/data/logs/agh.log" in dockerfile
    assert "/data/secrets/initial_owner_token" in dockerfile


def test_dockerignore_keeps_runtime_state_out_but_keeps_package_inputs() -> None:
    dockerignore = _read(".dockerignore")

    for expected in [
        ".git",
        ".venv",
        ".pytest_cache",
        ".ruff_cache",
        "build",
        "dist",
        ".agh-data",
        ".agh-data-*",
        ".agh-cli*.toml",
        "openspec",
        "sdd",
        ".pi",
        ".pi-lens",
    ]:
        assert expected in dockerignore

    for required in ["agh", "pyproject.toml", "uv.lock", "README.md"]:
        assert required not in dockerignore.splitlines()
