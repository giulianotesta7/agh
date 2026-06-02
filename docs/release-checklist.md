# Release Checklist

Use this checklist before tagging an AGH release. It verifies the Python package, Docker server, local CLI install path, docs, and workspace smoke flow.

## 1. Start clean

```bash
git status --short
uv lock --locked
```

Expected:

```text
# no tracked or untracked release artifacts
```

## 2. Check version metadata

Keep these values in sync before tagging:

- `pyproject.toml`
- `agh/__init__.py`
- `agh/server/app.py`
- `uv.lock`

For `0.1.0`, each should report `0.1.0`.

## 3. Run validation

CI runs these checks on pull requests and pushes to `main`. Run them locally before opening a release PR:

```bash
uv lock --locked
uv run pytest -q
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
uv run --with pyright pyright agh tests
docker build --check .
uv build
uv tool install --force dist/*.whl
agh --help
```

Notes:

- The current warning about Starlette/httpx testclient is known.
- Use `uv run --with ruff` and `uv run --with pyright` unless those tools are added to dev dependencies later.

## 4. Check the CLI package

```bash
uv run agh --help
uv run python - <<'PY'
from importlib.metadata import distribution
pkg = distribution("agh")
print(pkg.version)
for entry in pkg.entry_points:
    if entry.name == "agh":
        print(f"{entry.name} = {entry.value}")
PY
```

Expected:

```text
0.1.0
agh = agh.cli.main:app
```

## 5. Check Docker packaging

```bash
docker build --check .
docker build -t agh:release-check .
```

Run the server with persistent `/data`:

```bash
docker run --rm -p 8912:8912 -v agh-release-check:/data \
  -e AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com \
  agh:release-check
```

In another shell:

```bash
curl http://127.0.0.1:8912/api/v1/health
```

## 6. Check CLI install

Before using the package install path for a release, confirm package ownership and the published version:

```bash
uv tool install --force agh
agh --help
```

Then check the installer path without cloning the repo:

```bash
curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh
agh --help
```

Also check the development install path from a checkout:

```bash
uv tool install --force .
agh --help
```

## 7. Run a workspace smoke test

Use temporary data and config. Verify this flow works:

```text
login -> project create -> pack publish -> project pack add -> repo sync -> pull dry-run -> pull
```

Confirm these files after pull:

```text
.agh/project.toml
.agh/lock.toml
.agh-cache/packs/...
AGENTS.md / CLAUDE.md when assigned
.claude/skills/... and .opencode/skills/... when assigned
```

Also confirm `.gitignore` guidance recommends:

```gitignore
.agh-cache/
```

## 8. Review docs

```bash
uv run pytest tests/test_docs_guidance.py -q
```

Check both language entry points:

- `README.md`
- `README.es.md`

## 9. Pre-tag blockers

Resolve these items before tagging `0.1.0`:

- Skill-only packs.
- `agh pack init` for manifest/template generation.

## 10. Explicit release decisions

Decide and document these items before tagging. They may be included in `0.1.0` or deliberately deferred:

- Agent selection wizard and persisted pull target choice.
- AGH-specific API error envelope.

## 11. Tag only after approval

Do not tag or publish without explicit release approval.
