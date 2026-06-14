# Proposal: Fix Workspace Pull Atomicity

Make `agh pull` publish local cache, targets, skills, and `.agh/lock.toml` as one commit boundary.

Scope: staged outputs, rollback helpers, stale stage cleanup, and preservation of dry-run/conflict/force/symlink/VCS behavior. Out of scope: crash-perfect transactions, server/API changes, broad cache redesign, unrelated sync behavior.

Approach: stage pull artifacts in AGH-owned paths, then promote only after all outputs are ready; failures clean staging and preserve old lock/cache.
