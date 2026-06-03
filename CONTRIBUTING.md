# Contributing

AGH uses an issue-first workflow. Keep changes small and reviewable.

## Workflow

1. Search existing issues.
2. Open a bug report or feature request.
3. Wait for a maintainer to add `status:approved`.
4. Create a branch and open a PR that links the issue with `Closes #N`, `Fixes #N`, or `Resolves #N`.
5. Add exactly one `type:*` label to the PR.

PRs without an approved linked issue or exactly one `type:*` label fail validation.

## Branches and commits

Use conventional commits:

```text
feat: add workspace option
fix: handle invalid pack manifest
docs: clarify Docker setup
chore: update workflow checks
```

Prefer one focused change per PR. Split large changes before review becomes hard.

## Development

Install dependencies:

```bash
uv sync
```

Run validation before opening a PR:

```bash
uv run pytest
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
uv run --with pyright pyright agh tests
```

For Docker/runtime changes, also run:

```bash
docker build --check .
```

## Docs

README is the landing page. Put detailed usage in `docs/`.

When a user-facing docs change affects both languages, update the English doc and the Spanish mirror in the same PR.

## Releases

Most docs, workflow, and repo-hygiene changes do not need a release tag.

Tag a release only when publishing a package or container change:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```
