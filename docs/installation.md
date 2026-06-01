# Installation

AGH has two parts:

- the server, which runs with Docker;
- the local `agh` CLI, which you install on your workstation.

Install the CLI first, then use it to log in, create projects, publish packs, and run `agh pull` inside repos.

## Install the CLI from a checkout

Clone the repo and run the installer:

```bash
git clone https://github.com/giulianotesta7/AgentGuidanceHub.git
cd AgentGuidanceHub
./scripts/install.sh
```

The script uses `uv tool install --force .` from the repo root. It does not edit shell startup files, Docker state, AGH config, or login credentials.

Verify the command:

```bash
agh --help
```

After this, you can run `agh` from any directory. Workspace commands such as `agh sync` and `agh pull` use the repo you are currently in.

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
