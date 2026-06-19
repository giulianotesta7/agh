## Archive Report

**Change**: `collection-admin-cli`
**Archive Status**: intentional-with-warnings (archive path repaired)
**Archived To**: `openspec/changes/archive/2026-06-19-collection-admin-cli/`

### What was repaired
- Flattened the archive layout so the change lives directly under the dated archive folder.
- Updated source and archived specs to use `agh collection get` instead of `show`.
- Confirmed canonical `col_...` targets pass through and non-canonical `col_`-prefixed names resolve by name.
- Confirmed README/docs sequence matches the Judgment Day fixes.

### Validation
- `tasks.md` shows all implementation tasks checked.
- `grep` found no stale collection detail command references in the relevant OpenSpec/README artifacts after repair.
- `git diff --check` passes.

### Traceability
- PR #112
- PR #114
- PR #116
- PR #118
- Judgment Day approval and follow-up fixes incorporated

### Notes
- The archive was originally nested at `openspec/changes/archive/2026-06-19-collection-admin-cli/collection-admin-cli/`; that extra directory has been removed.
