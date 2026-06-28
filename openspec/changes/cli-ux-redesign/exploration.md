# Exploration: CLI UX Redesign

## Current State

`agh/cli/main.py` wires a broad Typer surface with a custom help group that currently prints a flat top-level summary from `APP_HELP`. Root help lists only first-level commands and does not expand nested subcommands. Command help is mixed: some subcommands use real Typer help, but unknown nested commands still fall back to the root summary.

Current public vocabulary is inconsistent with the target UX:

- `config show` exists, but `config set`, `config clear`, `whoami`, and `logout` do not.
- `user` still exposes `show`, `delete`, and `token` is top-level with `rotate`/`reset`.
- `project` still exposes `get`/`delete` and `member`/`package` nesting; `repo_url` is still the public option name.
- `collection` still exposes `get`/`delete` and package assignment is nested under `collection package` with assignment IDs in the response model.
- `package` is registry-centric today, but assignment UX still exists under `project package` and `collection package` with `position` in the payloads.
- `agent` and `skill agent ...` still represent local/global target selection; public UX has not been renamed to `target`.
- `sync` still exists as the repository-linking command.

Docs tests in `tests/test_docs_guidance.py` assert the current README command examples, so the CLI rewrite will need matching docs updates in the same change.

## Affected Areas

- `agh/cli/main.py` — Typer command tree, help behavior, aliases, and renamed command wiring.
- `agh/cli/config.py` — config/auth lifecycle (`config set/clear`, `login`, `whoami`, `logout`).
- `agh/cli/user_refs.py`, `project_refs.py`, `collection_refs.py`, `package_refs.py` — ref naming and help text.
- `agh/cli/agent_integrations.py` — target selection vocabulary and workspace/global target persistence.
- `tests/test_cli_*.py` — command/help/alias regression coverage.
- `tests/test_docs_guidance.py` and `README.md` / `README.es.md` — public command examples and help vocabulary.
- `openspec/specs/*` and the new change folder — proposal/spec slices once this exploration is promoted.

## Approaches

1. **Single command-tree rewrite with compatibility aliases** — reorganize Typer groups to the target vocabulary, keep hidden deprecated aliases for old entry points, and make root help render a full command map.
   - Pros: Clear end-state UX; least surprise for users; preserves backwards compatibility.
   - Cons: Large help/alias surface; easy to miss nested help edge cases.
   - Effort: High.

2. **Incremental rename slices by domain** — ship `config/auth`, then `user/project/collection`, then `package/target/link` in chained slices.
   - Pros: Fits the 400-line review budget; easier to validate and roll back.
   - Cons: Temporary hybrid UX; more coordination across slices.
   - Effort: High overall, lower per slice.

## Recommendation

Use **incremental rename slices** under one OpenSpec change, with a compatibility layer that keeps deprecated aliases hidden from help where practical. The root help redesign should be solved first, because it affects discoverability and command-map clarity for every other slice.

## Risks

- Root help and nested help are easy to regress in Typer when custom groups and aliases coexist.
- Changing public verbs (`get`/`show`/`delete`/`sync`/`agent`) will cascade into many docs/tests, likely exceeding the review budget if bundled into one PR.
- Renaming `agent` to `target` while also changing global-skill selection rules risks conflating two behaviors unless the CLI surface is sliced carefully.
- Package assignment UX removes `POSITION` and hides `ASSIGNMENT_ID`; that probably requires both API response formatting changes and CLI output changes.

## Questions / Assumptions

- Should deprecated aliases remain hidden indefinitely, or only for one release window?
- Should root help show every nested command as a full tree, or a condensed command map with nested groups expanded one level deep?
- For `config`, should `agh config` itself behave as `show`, or only be a group with explicit subcommands?
- Should `agh login` prompt for email/token only when interactive, and hard-fail otherwise?
- Should `agh target --global` use the existing global-skills defaults file, or a separate dedicated target preference store?
- For package assignment, should the server continue returning assignment IDs internally while the CLI stops exposing them in normal output?

## Review Slicing Concerns

This change is almost certainly over the 400-line review budget if implemented as one PR. Likely slices:

1. root help + command-tree plumbing + compatibility aliases
2. config/auth rename slice (`config`, `login`, `whoami`, `logout`)
3. resource vocabulary slice (`user`, `project`, `collection`)
4. package/assignment slice (`package` target flags, `POSITION` removal, hidden assignment IDs)
5. target/link/skill slice (`target`, `link`, global skill target UX)

Each slice should include its own focused CLI tests plus the relevant README/docs expectations.

## Ready for Proposal

Yes. The current code shape supports a staged redesign, but proposal work should first define the compatibility policy and the first slice boundary.
