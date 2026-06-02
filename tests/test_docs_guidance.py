from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_readme_is_docker_first_landing_page_with_doc_links() -> None:
    readme = _read("README.md")

    for expected in [
        "Self-hosted agent instructions and skills",
        "[Español](README.es.md)",
        "docker build -t agh .",
        "docker run --rm -p 8912:8912 -v agh-data:/data \\",
        "AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com",
        "uv tool install --force .",
        "agh login",
        "agh sync",
        "agh pull --dry-run",
        "agh pull",
        "agh agent",
        "[Installation](docs/installation.md)",
        "[Quickstart](docs/quickstart.md)",
        "[Packs](docs/packs.md)",
        "[Projects](docs/projects.md)",
        "[Admin](docs/admin.md)",
        "[Workspace guide](docs/workspace.md)",
        "[Operations](docs/operations.md)",
        "[Release checklist](docs/release-checklist.md)",
        ".agh/project.toml",
        ".agh/lock.toml",
        ".agh-cache/packs/",
        ".agh-cache/",
    ]:
        assert expected in readme


def test_installation_docs_cover_cli_install_and_uninstall() -> None:
    installation = _read("docs/installation.md")

    for expected in [
        "curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh",
        "uv tool install --force agh",
        "uv tool install --force .",
        "agh --help",
        "uv tool update-shell",
        "uv tool dir",
        "uv tool uninstall agh",
        "docker build -t agh .",
        "docker run --rm -p 8912:8912 -v agh-data:/data \\",
    ]:
        assert expected in installation


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


def test_quickstart_documents_first_run_and_first_pull() -> None:
    quickstart = _read("docs/quickstart.md")

    for expected in [
        "docker build -t agh .",
        "docker run --rm -p 8912:8912 -v agh-data:/data \\",
        "/data/secrets/initial_owner_token",
        "uv tool install --force .",
        "agh --help",
        "agh login",
        "agh project create",
        "agh sync",
        "agh pull --dry-run",
        "agh pull",
        "agh agent",
        ".agh/project.toml",
        ".agh/lock.toml",
        ".agh-cache/packs/",
        ".agh-cache/",
    ]:
        assert expected in quickstart


def test_workspace_docs_explain_pull_markers_skills_lock_and_git_rules() -> None:
    workspace = _read("docs/workspace.md")

    for expected in [
        "agh sync",
        "agh pull --dry-run",
        "agh pull --force",
        "AGH-BEGIN",
        "AGH-END",
        ".claude/skills/<skill>/SKILL.md",
        ".opencode/skills/<skill>/SKILL.md",
        'mode = "symlink"',
        'mode = "copy"',
        ".agh/project.toml",
        ".agh/lock.toml",
        ".agh-cache/packs/",
        ".agh-cache/",
        "old pre-release `.agh/packs/` cache",
        "Exit codes",
    ]:
        assert expected in workspace


def test_operations_docs_cover_docker_runtime_layout_and_maintenance() -> None:
    operations = _read("docs/operations.md")

    for expected in [
        "AGH_DATA_DIR=/data",
        "docker run --rm -p 8912:8912 -v agh-data:/data \\",
        "/data/agh.sqlite3",
        "/data/packs/",
        "/data/logs/agh.log",
        "/data/secrets/initial_owner_token",
        "curl http://127.0.0.1:8912/api/v1/health",
        "Backup",
        "Upgrade",
        "uv run pytest",
    ]:
        assert expected in operations


def test_pack_docs_cover_pack_authoring_and_publish() -> None:
    packs = _read("docs/packs.md")

    for expected in [
        "agh.pack.toml",
        'description = "Shared onboarding instructions and review skills."',
        "instructions/AGENTS.md",
        "instructions/CLAUDE.md",
        "skills/<name>/SKILL.md",
        "agh pack publish",
        "agh pack list",
        "SemVer",
        "Published versions are immutable",
        "Do not publish `latest`",
        "Use UTF-8 text files",
        "Do not include symlinks",
        "Published acme/onboarding@1.0.0.",
    ]:
        assert expected in packs


def test_project_docs_cover_projects_assignments_and_pull_resolution() -> None:
    projects = _read("docs/projects.md")

    for expected in [
        "A project is an AGH record linked to one git repository",
        "agh project create",
        "agh project list",
        "agh project get",
        "agh project update",
        "agh project delete",
        "agh project pack add",
        "agh project pack list",
        "agh project pack update",
        "agh project pack remove",
        "asn_...",
        "assignment id",
        "latest",
        "Resolved: acme/onboarding@1.0.0",
        ".agh/lock.toml",
        "Workspace guide",
    ]:
        assert expected in projects


def test_admin_docs_cover_bootstrap_users_roles_tokens_and_config() -> None:
    admin = _read("docs/admin.md")

    for expected in [
        "AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com",
        "/data/secrets/initial_owner_token",
        "agh login",
        "agh config show",
        "agh user list",
        "agh user create",
        "agh user update",
        "agh user delete",
        "agh token rotate",
        "agh token reset",
        "owner",
        "admin",
        "member",
        "Store this token now. AGH will not show it again.",
        "masks the stored token",
        "token hashes",
    ]:
        assert expected in admin


def test_spanish_readme_and_docs_mirror_core_flows() -> None:
    spanish_readme = _read("README.es.md")

    for expected in [
        "Instrucciones y skills",
        "[English](README.md)",
        "uv tool install --force .",
        "agh sync",
        "agh pull --dry-run",
        "[Instalación](docs/es/installation.md)",
        "[Packs](docs/es/packs.md)",
        "[Proyectos](docs/es/projects.md)",
        "[Admin](docs/es/admin.md)",
        ".agh-cache/",
    ]:
        assert expected in spanish_readme

    expected_docs = {
        "docs/es/installation.md": [
            "curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh",
            "uv tool install --force agh",
            "uv tool install --force .",
            "agh --help",
            "uv tool uninstall agh",
        ],
        "docs/es/quickstart.md": [
            "agh login",
            "agh project create",
            "agh pull --dry-run",
            ".agh-cache/",
        ],
        "docs/es/workspace.md": [
            "AGH-BEGIN",
            "agh pull --force",
            ".agh-cache/packs/",
            "Exit codes",
        ],
        "docs/es/operations.md": [
            "AGH_DATA_DIR=/data",
            "curl http://127.0.0.1:8912/api/v1/health",
            "Backup",
            "Upgrade",
        ],
        "docs/es/packs.md": [
            "agh.pack.toml",
            'description = "Shared onboarding instructions and review skills."',
            "agh pack publish",
            "SemVer",
        ],
        "docs/es/projects.md": [
            "agh project create",
            "agh project pack add",
            "ASSIGNMENT_ID",
            "Resolved: acme/onboarding@1.0.0",
        ],
        "docs/es/admin.md": [
            "agh user create",
            "agh token rotate",
            "token = ****",
            "Store this token now. AGH will not show it again.",
        ],
    }
    for path, expected_values in expected_docs.items():
        content = _read(path)
        for expected in expected_values:
            assert expected in content


def test_release_checklist_covers_pre_tag_validation() -> None:
    checklist = _read("docs/release-checklist.md")

    for expected in [
        "uv lock --locked",
        "uv run pytest -q",
        "uv run ruff check .",
        "uv run --with pyright pyright agh tests",
        "docker build --check .",
        "curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh",
        "uv tool install --force .",
        "login -> project create -> pack publish -> project pack add -> repo sync -> pull dry-run -> pull",
        "uv tool install --force agh",
        "## 9. Pre-tag blockers",
        "Skill-only packs",
        "agh pack init",
        "## 10. Explicit release decisions",
        "Agent selection wizard and persisted pull target choice",
        "AGH-specific API error envelope",
        "Do not tag or publish without explicit release approval",
    ]:
        assert expected in checklist
    assert "local-checkout-only" not in checklist


def test_dockerfile_documents_data_dirs_and_healthcheck() -> None:
    dockerfile = _read("Dockerfile")

    assert "ENV AGH_DATA_DIR=/data" in dockerfile
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
