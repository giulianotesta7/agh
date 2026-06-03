# Installation

AGH has two parts:

- the server, which runs with Docker;
- the local `agh` CLI, which you install on your workstation.

Install the CLI first, then use it for login, pack/project administration, and workspace operations.

## Install the CLI from the package

Install it without cloning the repo:

```bash
curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh
```

The installer runs:

```bash
uv tool install --force agh
```

The installer does not edit shell startup files, Docker state, AGH config, or login credentials.

Verify the command:

```bash
agh --help
```

The installer places the `agh` binary on the user's `PATH`. Workspace commands resolve the target repo from the current working directory.

## Install the CLI from a checkout

For development before package publication, clone the repo and install from the checkout directly:

```bash
git clone https://github.com/giulianotesta7/AgentGuidanceHub.git
cd AgentGuidanceHub
uv tool install --force .
```

## PATH troubleshooting

If the script finishes but `agh` is not found, add uv's tool bin directory to your shell:

```bash
uv tool update-shell
```

Restart your shell and check again:

```bash
agh --help
```

To inspect uv's tool directory:

```bash
uv tool dir
```

## Uninstall

```bash
uv tool uninstall agh
```

## Server install

The server is Docker-first. Use Docker Compose with the published image and a persistent `/data` volume:

```bash
docker compose up -d
```

The compose file uses:

```text
ghcr.io/giulianotesta7/agent-guidance-hub:0.1.0
```

For a direct `docker run` command, `/data`, logs, healthcheck, backup, and upgrade notes, see [Operations](operations.md).
