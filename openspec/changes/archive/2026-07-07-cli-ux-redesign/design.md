# Design: CLI UX Redesign

## Technical Approach

Redesign the Typer surface in small, breaking slices while reusing existing API helpers and storage. `agh/cli/main.py` remains the command wiring entrypoint; `agh/cli/config.py`, `agent_integrations.py`, `global_skills.py`, ref resolvers, and workspace sync/pull helpers become the backing services for clearer command names.

## Architecture Decisions

| Topic | Choice | Tradeoff / Rationale |
|---|---|---|
| Command wiring | Keep Typer groups, but rebuild the public tree around `config`, `login`, `whoami`, `logout`, resources, `package`, `target`, `skill`, `link`, and `pull`. | Lowest-risk path because current CLI already centralizes command registration in `main.py`; avoids a dispatcher rewrite. |
| Help behavior | Root uses a maintained full command-map help string; each subgroup uses local help via a subgroup help class/callback, not `APP_HELP`. | Prevents the current bug where empty groups and unknown nested commands show root help. Command `--help` remains Typer-native. |
| Breaking policy | Remove old public names instead of hidden aliases. | Matches proposal/spec; scripts fail loudly instead of silently depending on deprecated behavior. |
| Config/auth | Split instance config from credentials in `config.py`; `config set INSTANCE_URL` stores only instance, `login` uses that instance and stores validated email/token, `logout` clears credentials only, `whoami` calls `/me`. | Avoids prompting for URL during login and prevents credentials from being reused against a changed instance. |
| Target state | Reuse local state paths: workspace target in `.agh-cache/preferences.toml`; global target in `${XDG_STATE_HOME:-~/.local/state}/agh/global-skills/defaults.toml`. | Preserves existing local state shape while renaming the public UX from agent/default-agent to target. |
| Package assignment | Route assignments through `package` commands with exactly one of `--project PROJECT_REF` or `--collection COLLECTION_REF`; omit `position`. | Keeps server assignment IDs internal; CLI resolves refs and finds assignments by package ref when activate/deactivate/unassign needs the existing assignment id. |

## Data Flow

```text
Typer command -> ref/config/target resolver -> _api_request -> existing API
      |                 |                         |
      |                 +-> local TOML state        +-> formatted stdout/errors
      +-> local help renderer
```

Target resolution for `skill install`: explicit `--target`, workspace target, global target, interactive prompt, then non-interactive usage error.

## File Changes

| File | Action | Description |
|---|---|---|
| `agh/cli/main.py` | Modify | Rewire command tree/help; add `whoami`, `logout`, `link`; rename resource verbs; move package assignment commands. |
| `agh/cli/config.py` | Modify | Support instance-only state, optional credentials, config set/clear, logout-safe writes. |
| `agh/cli/agent_integrations.py` | Modify | Add target-named wrappers over workspace/global target reads/writes. |
| `agh/cli/workspace_sync.py` | Modify | Keep behavior, expose through `link` and update messages/help. |
| `agh/cli/*_refs.py`, `package_refs.py` | Modify | Align help/error text with `*_REF`; keep resolver behavior. |
| `agh/server/routes/projects.py` | Modify if needed | Add minimal `GET /projects/{project_id}/members` if no existing route can back `project member list`. |
| `tests/test_cli_*.py`, `tests/test_docs_guidance.py` | Modify | Strict TDD coverage per slice. |
| `README.md`, `README.es.md`, `changelog.d/*.breaking.md` | Modify/Create | Update public examples and release notes with the breaking CLI map. |

## Interfaces / Contracts

- `agh config` displays configured instance only; `config set INSTANCE_URL`; `config clear` removes instance and credentials.
- `agh login [--email EMAIL --token TOKEN]` requires existing instance config; interactive prompts cover email/token only.
- Resources use `list/create/describe/update/activate/deactivate`; `user token rotate`; `project member list/add/remove`.
- `package list [--project PROJECT_REF | --collection COLLECTION_REF]`; `package describe PACKAGE_REF`; `package assign|activate|deactivate|unassign PACKAGE_REF (--project PROJECT_REF | --collection COLLECTION_REF)`.
- Removed names are not advertised: `sync`, `agent`, top-level `token`, `show/get/delete`, nested `project package` and `collection package`, `--position`, `skill installed/remove/agent`.

## Testing Strategy

| Slice | Tests |
|---|---|
| Root/help | Failing CLI tests for root tree, subgroup local help, `--version`, removed names absent, unknown command exit 2. |
| Config/auth/target | Isolated `AGH_CONFIG_FILE`, temp workspaces/state, mocked `/me`, credential redaction, non-interactive failures. |
| Resources | Mock API tests for renamed verbs, member list, token nesting, legacy verbs failing. |
| Package | Mutually exclusive target flags, no positional target/position, latest describe, assignment lookup routes. |
| Skill/link/pull | Target resolution order, `link` replacing `sync`, explicit `pull` help. |
| Docs/changelog | README/README.es mirror, docs guidance tests, Towncrier breaking fragment. |

Strict TDD applies: write focused failing tests before each runtime slice, then broaden with `uv run pytest` before PR readiness.

## Migration / Rollout

Ship as chained PR slices near the 400-line review budget: help infrastructure; config/auth/target foundation; resources; package assignment; skill/link/pull cleanup; docs/changelog final. Roll back by reverting the active slice only; do not ship mixed old/new names in one public release.

## Risks

- Help rendering can regress command-specific `--help`; protect with golden-ish focused CLI assertions.
- Package assignment lookup can be ambiguous; error messages must name the target and package ref and suggest `package list --project/--collection`.
- Breaking command removals affect scripts; changelog and README migration notes are mandatory.

## Open Questions

None.
