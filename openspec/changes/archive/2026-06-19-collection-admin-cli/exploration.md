## Exploration: collection-admin-cli

### Current State
AGH already has server-side collection CRUD and package-assignment APIs, plus `agh skill ...` commands for listing/installing/removing collection-backed global skills. The CLI can resolve collection skills, download verified `SKILL.md` artifacts, and install them into the selected agent’s native global skill directory with a local AGH global lock/cache.

What is missing is an admin-facing collection CLI. There are no `agh collection ...` commands yet for create/list/show/update/deactivate or for package assignment management (`add/list/update/remove`). Today, collection creation and package assignment are only reachable through the API.

### Affected Areas
- `agh/cli/main.py` — add the new `collection` command group and wire admin CRUD/assignment subcommands.
- `agh/server/routes/collections.py` — reuse the existing collection API contract; likely the CLI will call these endpoints directly.
- `agh/cli/global_skills.py` — keep as the consumer/global-install path; do not mix admin collection management into it.
- `tests/test_global_skills.py` — existing coverage proves consumer skill flows, but not collection admin UX.
- `tests/` — add CLI tests for collection admin commands and error handling.
- `README.md` / `README.es.md` — document the new admin CLI surface after implementation.

### Approaches
1. **Thin CLI wrapper over existing collection APIs** — add `agh collection ...` commands that map 1:1 to server endpoints and format responses for admins.
   - Pros: minimal new behavior, consistent with current CLI architecture, low risk.
   - Cons: more subcommands to design; CLI parsing/UX still needs careful shaping.
   - Effort: Medium

2. **CLI orchestration layer with composite commands** — expose fewer higher-level commands that combine related API calls (for example, create collection + assign initial package).
   - Pros: fewer user steps for common admin tasks.
   - Cons: more opinionated, harder to match server semantics, more edge cases.
   - Effort: High

### Recommendation
Use a thin wrapper over the existing collection APIs. The server contract already exists and the user pain point is discoverability/operability from the CLI, not new business logic.

### Risks
- Command surface can grow quickly if CRUD and package-assignment flows are over-grouped.
- The CLI must preserve admin-only authorization errors clearly instead of masking API failures.
- `collection` commands must stay separate from `skill` consumer commands to avoid confusing admin and member workflows.

### Ready for Proposal
Yes. The scope is clear enough to move to proposal/spec once the exact command set and output shapes are confirmed.
