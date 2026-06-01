from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_readme_is_docker_first_landing_page_with_doc_links() -> None:
    readme = _read("README.md")

    for expected in [
        "Self-hosted agent instructions and skills",
        "docker build -t agh .",
        "docker run --rm -p 8912:8912 -v agh-data:/data \\",
        "AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com",
        "agh login",
        "agh sync",
        "agh pull --dry-run",
        "agh pull",
        "agh agent",
        "[Quickstart](docs/quickstart.md)",
        "[Workspace guide](docs/workspace.md)",
        "[Operations](docs/operations.md)",
        ".agh/project.toml",
        ".agh/lock.toml",
        ".agh/packs/",
    ]:
        assert expected in readme


def test_quickstart_documents_first_run_and_first_pull() -> None:
    quickstart = _read("docs/quickstart.md")

    for expected in [
        "docker build -t agh .",
        "docker run --rm -p 8912:8912 -v agh-data:/data \\",
        "/data/secrets/initial_owner_token",
        "agh login",
        "agh project create",
        "agh sync",
        "agh pull --dry-run",
        "agh pull",
        "agh agent",
        ".agh/project.toml",
        ".agh/lock.toml",
        ".agh/packs/",
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
        ".agh/packs/",
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
