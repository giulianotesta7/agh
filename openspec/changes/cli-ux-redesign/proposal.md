# Proposal: CLI UX Redesign

## Intent

AGH's CLI has inconsistent vocabulary, incomplete nested help, and legacy nouns (`agent`, `sync`, nested package assignment). Redesign it as a breaking, sliced UX for predictable discovery and scripting.

## Scope

In: full root/help map with nested commands and `--version`; command-local help; honest `*_REF` names; config/auth cleanup; resource verbs; package-centric assignment; `target`; `link`; clearer `pull`. Out: compatibility aliases, monolithic delivery, unrelated API/storage redesign.

## Capabilities

### New Capabilities
- `cli-command-ux`: Canonical command tree, help, config/auth, resource vocabulary, target/link names, breaking policy.

### Modified Capabilities
- `cli-usage-errors`: Help and unknown-command behavior.
- `guidance-packages`: Assignment, mutually exclusive project/collection, no position, `@latest` highest SemVer.
- `global-skill-collections`: Target resolution, official skill commands, removed/hidden unsupported skill commands.

## Proposed UX Command Tree

```text
agh [--help] [--version]
config; config set INSTANCE_URL; config clear
login [--email EMAIL --token TOKEN]; whoami; logout
user list/create/describe/update/activate/deactivate; user token rotate
project list/create --git-url/describe/update --git-url/activate/deactivate
project member list/add/remove
collection list/create/describe/update/activate/deactivate
package list [--project PROJECT_REF | --collection COLLECTION_REF]
package describe PACKAGE_REF
package assign/activate/deactivate/unassign PACKAGE_REF (--project PROJECT_REF | --collection COLLECTION_REF)
target; target set TARGET [--global]; target clear [--global]
skill list; skill install PACKAGE_REF SKILL_NAME --target TARGET [--force]
link; pull
```

Use `PROJECT_REF`, `USER_REF`, `COLLECTION_REF`, `PACKAGE_REF`. `agh config` shows only configured instance. `login` never prompts for instance URL. Skill target resolution: explicit `--target`, workspace, global, interactive prompt, non-interactive error.

## Compatibility Policy

Breaking: no public aliases for `show`/`get`/`delete`, `sync`, `agent`, nested package assignment, position, or unofficial `skill installed/remove/agent`.

## Slice Strategy

1 root/help + infrastructure; 2 config/auth + target foundation; 3 user/project/collection vocabulary; 4 package assignment UX; 5 skill + link/pull cleanup; 6 docs/changelog final. Each slice must fit 400 changed lines or become chained.

## Impacted Areas

Modified: CLI wiring/config/refs/target, CLI tests, README/README.es/docs tests. New: `changelog.d/` breaking fragments.

## Risks

High: nested help regressions and review overload; mitigate with help-first tests and enforced slices/budget. Medium: broken scripts and mixed package/skill semantics; mitigate with changelog/docs migration notes and separate slices.

## Rollback Plan

Revert the active slice PR. Do not partially ship mixed old/new command names.

## Dependencies

- Existing auth/config/package/collection/global-skill APIs; package `@latest` highest-SemVer resolver.

## Success Criteria

- [ ] Root/command help show the agreed tree/names.
- [ ] Removed legacy commands fail as unsupported.
- [ ] Each slice includes CLI tests and docs/changelog coverage.
- [ ] Final UX exposes `target`, `link`, package-centric assignment, and clearer `pull`.
