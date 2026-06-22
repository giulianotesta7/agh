# Changelog fragments

Add one Towncrier fragment for each user-facing change:

```bash
uv run towncrier create +short-description.added.md
uv run towncrier create 123.fixed.md
```

Use these fragment types:

- `added` — new user-visible behavior.
- `changed` — changed behavior, output, configuration, or operations.
- `fixed` — user-visible bug fixes.
- `breaking` — incompatible API, config, lockfile, or distribution changes.
- `docs` — important operator-facing documentation changes.

Do not add fragments for tests-only changes, internal refactors, formatting,
typing cleanup, or minor documentation typos.
