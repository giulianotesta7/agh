# Projects

A project is an AGH record linked to one git repository. Projects decide which packs a repo receives when you run `agh sync` and `agh pull`.

## Create a project

Use the repository URL that developers have in git remotes:

```bash
agh project create "<project-name>" --repo-url <git-repo-url>
```

Example:

```bash
agh project create "Agent Guidance Hub" \
  --repo-url https://github.com/giulianotesta7/AgentGuidanceHub.git
```

Example output:

```text
Created project Agent Guidance Hub (prj_...).
Repo: github.com/giulianotesta7/AgentGuidanceHub
Status: active
```

## List and inspect projects

```bash
agh project list
agh project get prj_...
```

List output uses typed headers:

```text
PROJECT_ID            NAME                REPO                                           STATUS
prj_...               Agent Guidance Hub  github.com/giulianotesta7/AgentGuidanceHub     active
```

`agh project get` shows one project:

```text
Project: Agent Guidance Hub
Project ID: prj_...
Repo: github.com/giulianotesta7/AgentGuidanceHub
Status: active
```

## Update or deactivate a project

```bash
agh project update prj_... --name "App API"
agh project update prj_... --repo-url git@github.com:acme/app-api.git
agh project delete prj_...
```

`delete` deactivates the project. It does not remove historical records from the server.

## Assign packs

A project pack assignment connects a project to a pack reference.

```bash
agh project pack add prj_... acme/onboarding@latest
```

Example:

```text
Assigned acme/onboarding@latest to project prj_...
Resolved: acme/onboarding@1.0.0
Assignment: asn_...
```

`asn_...` is the assignment id. It identifies the project-to-pack relationship, not the pack itself.

## List assignments

```bash
agh project pack list prj_...
```

Example:

```text
ASSIGNMENT_ID          PACK_REF                RESOLVED               POSITION  STATUS
asn_...                acme/onboarding@latest  acme/onboarding@1.0.0  0         active
```

## Update or remove assignments

```bash
agh project pack update prj_... asn_... --pack-ref acme/onboarding@1.0.0
agh project pack update prj_... asn_... --position 10
agh project pack update prj_... asn_... --inactive
agh project pack remove prj_... asn_...
```

## How `latest` works

Use an exact version when you want a project pinned at assignment time:

```bash
agh project pack add prj_... acme/onboarding@1.0.0
```

Use `latest` when the project should resolve to the newest published version during manifest generation:

```bash
agh project pack add prj_... acme/onboarding@latest
```

When a workspace runs `agh pull`, AGH writes the resolved concrete version and checksum to `.agh/lock.toml`.

## Workspace flow

After project setup, run these commands in the target repo:

```bash
agh sync
agh pull --dry-run
agh pull
```

See the [Workspace guide](workspace.md) for markers, skills, `.agh/lock.toml`, and `.agh-cache/`.
