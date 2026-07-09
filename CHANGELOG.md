# Changelog

User-facing changes to AGH are recorded here. Contributors add Towncrier
fragments in `changelog.d/`; release maintainers compile them into this file
before tagging a release.

<!-- towncrier release notes start -->

## 0.7.0 - 2026-07-08

### Changed

- Change AGH CLI help to show the current command tree and command-local help consistently.

### Breaking Changes

- Change AGH CLI instance configuration to use `agh config`, `agh config set`, and `agh config clear`, clearing credentials when switching instances.
- Change AGH login to authenticate against the configured instance and add `agh whoami` and `agh logout` session commands.
- Move package assignment under `agh package assign|activate|deactivate|unassign PACKAGE_REF` with mutually exclusive `--project` or `--collection` target flags, remove the nested `project package` and `collection package` subgroups and the `--position` option, scope `package list` to one assignment table with the same target flags, and resolve `package describe PACKAGE_REF@latest` to the highest SemVer version.
- Rename `agh sync` to `agh link`, remove `skill remove`/`installed`/`agent` subcommands, and make `--target` optional on `skill install` with workspace/global fallback resolution.
- Replace the public `agh agent` selection command with `agh target` workspace and global target commands.
- Replace user, project, and collection resource commands with the canonical describe, activate, and deactivate verbs, move token rotation under `agh user token rotate` and remove the legacy `token reset` command, rename the project create/update `--repo-url` option to `--git-url`, and add project member listing.


## 0.6.0 - 2026-06-23

### Added

- Add Scoop-based Windows installation support with per-release binary assets.
- Add Towncrier-based changelog fragments for user-facing AGH changes.
- Add Windows release assets for the AGH CLI as part of the release pipeline.
