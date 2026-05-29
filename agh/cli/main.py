"""Typer CLI entrypoint for Agent Guidance Hub."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="agh",
    help="Agent Guidance Hub — manage and distribute agent guidance packs.",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Agent Guidance Hub CLI."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()
