# Installation

AGH has two parts:

- the server, which runs with Docker;
- the local `agh` CLI, which you install on your workstation.

Install the CLI first, then use it for login, pack/project administration, and workspace operations.

## Install the CLI from the package

After the `agh` package is published for release, install it without cloning the repo:

```bash
curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh
```

The installer runs:

```bash
uv tool install --force agh
```

Do not use the package install path for a release until package ownership and the published version have been validated.

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

The server is Docker-first. Build and run it with a persistent `/data` volume:

```bash
docker build -t agh .
docker run --rm -p 8912:8912 -v agh-data:/data \
  -e AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com \
  agh
```

See [Operations](operations.md) for `/data`, logs, healthcheck, backup, and upgrade notes.
