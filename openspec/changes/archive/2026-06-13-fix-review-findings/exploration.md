## Exploration: fix-review-findings

### Current State
The review findings are mostly real. `agh/server/app.py` sets `db_path` on app startup, but pack routes still call `get_data_dir()` during requests, so filesystem writes can drift if `AGH_DATA_DIR` changes after startup. Pack publish writes to a staging dir, copies into final storage, then inserts the DB row; a crash between copy and commit can leave orphaned files or a “blocked” version path. `Content-Length` is cast with `int(...)` before validation, so malformed headers can raise an unhandled `ValueError`. CLI unknown-command handling intentionally exits 0 today. Pack downloads and pull-manifest generation read storage files directly and currently return 500 on unexpected missing/corrupt content.

### Affected Areas
- `agh/server/app.py` — startup state and `Content-Length` middleware validation.
- `agh/server/routes/packs.py` — publish transaction ordering, storage root usage, download safety.
- `agh/server/routes/projects.py` — pull-manifest file reads and missing/corrupt pack handling.
- `agh/cli/main.py` — unknown command exit behavior.
- `agh/cli/workspace_sync.py` — git subprocess timeout risk.
- `agh/cli/workspace_pull.py` — non-atomic filesystem changes and git subprocess timeout risk.
- `agh/server/migrations/002_unique_project_names.sql` and `tests/test_db_migrations.py` — duplicate project-name startup failure path.

### Approaches
1. **Fix the high-severity data-integrity issues first** — make pack publish use startup-root state consistently, then make publish storage/DB work atomic enough to avoid permanent version lockout after crashes.
   - Pros: addresses the two CRITICAL findings and the strongest user-visible corruption risk.
   - Cons: needs careful transaction/file cleanup sequencing and new regression tests.
   - Effort: High

2. **Bundle all review findings into one broad hardening change** — include CLI exit semantics, malformed header handling, missing-file fallbacks, timeout guards, and workspace atomicity.
   - Pros: one pass over the codebase.
   - Cons: exceeds review budget and mixes unrelated concerns; hard to validate and risky to merge.
   - Effort: Very High

### Recommendation
Split the work. First change should cover pack publish correctness and request-header validation only: consistent data-root usage, publish crash recovery/cleanup, and malformed `Content-Length` handling. Defer CLI exit-code policy, missing-file 500s, subprocess timeouts, workspace atomicity, and migration-startup risk into follow-up changes.

### Risks
- Crash-recovery logic can accidentally delete valid storage if rollback cleanup is too broad.
- Changing publish ordering may expose latent uniqueness/locking assumptions in pack version tests.
- Migration startup failure is real but orthogonal; leaving it for follow-up means fresh installs remain safe while legacy duplicate data still needs a separate remediation plan.

### Ready for Proposal
Yes — tell the user the first proposal should be narrowly scoped to pack publish integrity plus malformed `Content-Length`, with the rest explicitly deferred.
