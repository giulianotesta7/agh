"""Typer CLI entrypoint for Agent Guidance Hub."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Annotated, Any, NoReturn

import typer
from typer.core import TyperGroup

from agh.cli.config import (
    AghConfig,
    ConfigError,
    LoginValidationError,
    get_config_path,
    load_config,
    mask_token,
    normalize_instance_url,
    save_config,
    validate_login,
)
from agh.cli.pack_publish import PackPublishBuildError, build_pack_publish_payload
from agh.cli.workspace_pull import WorkspacePullError, pull_workspace
from agh.cli.workspace_sync import WorkspaceSyncError, sync_workspace

APP_HELP = """Agent Guidance Hub — manage and distribute agent guidance packs.

Usage:
  agh [OPTIONS] COMMAND [ARGS]...

Commands:
  login        Validate API credentials with /api/v1/me and save local config.
  config show  Show the saved instance URL, email, and masked token.
  user         Manage users.
  token        Rotate or reset user API tokens.
  project      Manage projects and developer memberships.
  pack         Publish and list guidance packs.
  sync         Link this git repository to its matching AGH project.
  pull         Pull assigned guidance packs into this repository.

Global options:
  --help       Show this help page.

Arguments:
  Run `agh <command> --help` for command-specific options and arguments.
"""


class AghHelpGroup(TyperGroup):
    """Typer group that shows AGH's command overview for help/unknown commands."""

    def get_help(self, ctx: Any) -> str:
        return APP_HELP

    def resolve_command(self, ctx: Any, args: list[str]) -> Any:
        if args:
            command_name = args[0]
            command = self.get_command(ctx, command_name)
            if command is None and not command_name.startswith("-"):
                typer.echo(APP_HELP)
                raise typer.Exit(0)
        return super().resolve_command(ctx, args)


class AghSubcommandGroup(TyperGroup):
    """Typer subgroup that keeps real help but routes unknown commands to APP_HELP."""

    def resolve_command(self, ctx: Any, args: list[str]) -> Any:
        if args:
            command_name = args[0]
            command = self.get_command(ctx, command_name)
            if command is None and not command_name.startswith("-"):
                typer.echo(APP_HELP)
                raise typer.Exit(0)
        return super().resolve_command(ctx, args)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects so Bearer tokens are never forwarded to another URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)

app = typer.Typer(
    name="agh",
    cls=AghHelpGroup,
    help="Agent Guidance Hub — manage and distribute agent guidance packs.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
config_app = typer.Typer(
    cls=AghHelpGroup,
    help="Inspect local AGH CLI configuration.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
user_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Manage AGH users.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
token_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Rotate or reset user API tokens.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
project_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Manage AGH projects.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
project_member_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Manage project developer memberships.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
project_pack_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Manage project pack assignments.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
pack_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Publish and list AGH packs.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
app.add_typer(config_app, name="config")
app.add_typer(user_app, name="user")
app.add_typer(token_app, name="token")
app.add_typer(project_app, name="project")
app.add_typer(pack_app, name="pack")
project_app.add_typer(project_member_app, name="member")
project_app.add_typer(project_pack_app, name="pack")


def _fail(message: str, *, code: int = 1) -> NoReturn:
    typer.secho(f"Error: {message}", fg=typer.colors.RED, err=False)
    raise typer.Exit(code)


def _api_request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
) -> Any:
    try:
        config = load_config()
    except ConfigError as exc:
        _fail(str(exc), code=4)

    data = None
    headers = {
        "Authorization": f"Bearer {config.token}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{config.instance_url}/api/v1{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        # noqa: S310 - configured AGH URL
        with _NO_REDIRECT_OPENER.open(request, timeout=10) as response:
            payload = response.read()
            if not payload:
                return None
            return json.loads(payload.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code < 400:
            _fail("API request redirected; refusing to forward token", code=1)
        detail = _error_detail(exc)
        code = 4 if exc.code in {401, 403} else 1
        _fail(f"HTTP {exc.code}: {detail}", code=code)
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        _fail(f"API request failed: {reason}", code=1)
    except TimeoutError as exc:
        _fail(f"API request failed: {exc}", code=1)
    except json.JSONDecodeError as exc:
        _fail(f"API returned invalid JSON: {exc}", code=1)


def _error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except Exception:
        return exc.reason
    redacted_payload = _redact(payload)
    detail = (
        redacted_payload.get("detail") if isinstance(redacted_payload, dict) else None
    )
    if isinstance(detail, str):
        return detail
    return json.dumps(redacted_payload, sort_keys=True)


def _redact(value: Any, *, allow_plain_token: bool = False) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = key.lower()
            if lowered == "token_hash":
                redacted[key] = "****"
            elif lowered == "token" and not allow_plain_token:
                redacted[key] = mask_token(str(item))
            else:
                redacted[key] = _redact(item, allow_plain_token=allow_plain_token)
        return redacted
    if isinstance(value, list):
        return [_redact(item, allow_plain_token=allow_plain_token) for item in value]
    return value


def _echo_payload(payload: Any, *, allow_plain_token: bool = False) -> None:
    typer.echo(
        json.dumps(_redact(payload, allow_plain_token=allow_plain_token), indent=2)
    )


def _body_without_none(**fields: Any) -> dict[str, Any]:
    return {key: value for key, value in fields.items() if value is not None}


@app.command("pull", help="Pull assigned guidance packs into this repository.")
def pull(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show planned changes without writing files."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Overwrite checksum-conflicted AGH-managed blocks only.",
        ),
    ] = False,
) -> None:
    """Fetch the linked project pull-manifest and apply managed guidance blocks."""
    try:
        result = pull_workspace(dry_run=dry_run, force=force)
    except WorkspacePullError as exc:
        _fail(str(exc), code=exc.code)

    _echo_payload(
        {
            "status": result.status,
            "dry_run": result.dry_run,
            "changes": [
                {
                    "target_path": change.target_path,
                    "status": change.status,
                    "conflicts": [
                        {
                            "pack_ref": conflict.pack_ref,
                            "artifact_path": conflict.artifact_path,
                            "expected_checksum": conflict.expected_checksum,
                            "actual_checksum": conflict.actual_checksum,
                        }
                        for conflict in change.conflicts
                    ],
                }
                for change in result.plan.changes
            ],
            "lock_path": str(result.cache_result.lock_path)
            if result.cache_result is not None
            else None,
        }
    )
    raise typer.Exit(result.exit_code)


@app.command("sync", help="Link this git repository to its matching AGH project.")
def sync(
    remote: Annotated[
        str,
        typer.Option("--remote", help="Git remote name to match against AGH projects."),
    ] = "origin",
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace only .agh/project.toml if it exists."),
    ] = False,
) -> None:
    """Match the selected git remote to an accessible AGH project and write .agh/project.toml."""
    try:
        result = sync_workspace(remote=remote, force=force)
    except WorkspaceSyncError as exc:
        _fail(str(exc), code=exc.code)

    _echo_payload(
        {
            "project_id": result.project_id,
            "project_name": result.project_name,
            "instance_url": result.instance_url,
            "repo_url_normalized": result.repo_url_normalized,
            "project_file": str(result.link_path),
            "replaced": result.replaced,
        }
    )


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Agent Guidance Hub CLI."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@app.command(help="Validate API credentials and save local AGH config.")
def login(
    url: Annotated[
        str,
        typer.Option(
            "--url",
            prompt="AGH instance URL",
            help="AGH server base URL, e.g. http://localhost:8912.",
        ),
    ],
    email: Annotated[
        str,
        typer.Option(
            "--email",
            prompt="Email",
            help="Email expected from GET /api/v1/me.",
        ),
    ],
    token: Annotated[
        str,
        typer.Option(
            "--token",
            prompt="Token",
            hide_input=True,
            help="AGH API token. The token is validated but never printed.",
        ),
    ],
) -> None:
    """Validate credentials against /api/v1/me, then write config.toml."""
    try:
        instance_url = normalize_instance_url(url)
        validate_login(instance_url=instance_url, email=email, token=token)
        save_config(AghConfig(instance_url=instance_url, email=email, token=token))
    except (ConfigError, LoginValidationError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=False)
        raise typer.Exit(1) from exc

    typer.echo(
        f"Logged in to {instance_url} as {email}. Config saved to {get_config_path()}."
    )


@config_app.callback(invoke_without_command=True)
def config_main(ctx: typer.Context) -> None:
    """Local AGH CLI configuration commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@config_app.command("show", help="Show local AGH config with the token masked.")
def config_show() -> None:
    """Show local config without revealing the plaintext token."""
    try:
        config = load_config()
    except ConfigError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=False)
        raise typer.Exit(1) from exc

    typer.echo(f"instance_url = {config.instance_url}")
    typer.echo(f"email = {config.email}")
    typer.echo(f"token = {mask_token(config.token)}")


@user_app.callback(invoke_without_command=True)
def user_main(ctx: typer.Context) -> None:
    """User administration commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@user_app.command("list", help="List users visible to the authenticated admin.")
def user_list() -> None:
    _echo_payload(_api_request("GET", "/users"))


@user_app.command("create", help="Create a user and print the issued token once.")
def user_create(
    email: Annotated[str, typer.Argument(help="User email address.")],
    role: Annotated[
        str,
        typer.Option("--role", help="Global role: owner, admin, or member."),
    ] = "member",
) -> None:
    payload = _api_request("POST", "/users", body={"email": email, "role": role})
    _echo_payload(payload, allow_plain_token=True)


@user_app.command("update", help="Update user email, role, or active flag.")
def user_update(
    user_id: Annotated[str, typer.Argument(help="User id, e.g. usr_...")],
    email: Annotated[str | None, typer.Option("--email", help="New email.")] = None,
    role: Annotated[
        str | None,
        typer.Option("--role", help="New role: owner, admin, or member."),
    ] = None,
    active: Annotated[
        bool | None,
        typer.Option("--active/--inactive", help="Set whether the user is active."),
    ] = None,
) -> None:
    _echo_payload(
        _api_request(
            "PATCH",
            user_path(user_id),
            body=_body_without_none(email=email, role=role, active=active),
        )
    )


@user_app.command("delete", help="Deactivate a user.")
def user_delete(
    user_id: Annotated[str, typer.Argument(help="User id, e.g. usr_...")],
) -> None:
    _echo_payload(_api_request("DELETE", user_path(user_id)))


def user_path(user_id: str) -> str:
    return f"/users/{user_id}"


@token_app.callback(invoke_without_command=True)
def token_main(ctx: typer.Context) -> None:
    """Token lifecycle commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@token_app.command("rotate", help="Rotate a user's token and print the new token once.")
def token_rotate(
    user_id: Annotated[str, typer.Argument(help="User id, e.g. usr_...")],
) -> None:
    _echo_payload(
        _api_request("POST", f"/users/{user_id}/token:rotate"),
        allow_plain_token=True,
    )


@token_app.command("reset", help="Reset a user's token and print the new token once.")
def token_reset(
    user_id: Annotated[str, typer.Argument(help="User id, e.g. usr_...")],
) -> None:
    _echo_payload(
        _api_request("POST", f"/users/{user_id}/token:reset"),
        allow_plain_token=True,
    )


@project_app.callback(invoke_without_command=True)
def project_main(ctx: typer.Context) -> None:
    """Project administration commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@project_app.command("list", help="List projects visible to the authenticated user.")
def project_list() -> None:
    _echo_payload(_api_request("GET", "/projects"))


@project_app.command("create", help="Create a project.")
def project_create(
    name: Annotated[str, typer.Argument(help="Project display name.")],
    repo_url: Annotated[
        str,
        typer.Option("--repo-url", help="Git repository URL linked to the project."),
    ],
) -> None:
    _echo_payload(
        _api_request("POST", "/projects", body={"name": name, "repo_url": repo_url})
    )


@project_app.command("get", help="Show one project by id.")
def project_get(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
) -> None:
    _echo_payload(_api_request("GET", project_path(project_id)))


@project_app.command("update", help="Update project name, repo URL, or active flag.")
def project_update(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
    name: Annotated[
        str | None, typer.Option("--name", help="New project name.")
    ] = None,
    repo_url: Annotated[
        str | None,
        typer.Option("--repo-url", help="New linked Git repository URL."),
    ] = None,
    active: Annotated[
        bool | None,
        typer.Option("--active/--inactive", help="Set whether the project is active."),
    ] = None,
) -> None:
    _echo_payload(
        _api_request(
            "PATCH",
            project_path(project_id),
            body=_body_without_none(name=name, repo_url=repo_url, active=active),
        )
    )


@project_app.command("delete", help="Deactivate a project.")
def project_delete(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
) -> None:
    _echo_payload(_api_request("DELETE", project_path(project_id)))


def project_path(project_id: str) -> str:
    return f"/projects/{project_id}"


@pack_app.callback(invoke_without_command=True)
def pack_main(ctx: typer.Context) -> None:
    """Pack publish/list commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@pack_app.command("list", help="List published pack versions.")
def pack_list() -> None:
    _echo_payload(_api_request("GET", "/packs"))


@pack_app.command("publish", help="Publish a local pack directory.")
def pack_publish(
    path: Annotated[Path, typer.Argument(help="Directory containing agh.pack.toml.")],
) -> None:
    try:
        body = build_pack_publish_payload(path)
    except PackPublishBuildError as exc:
        _fail(str(exc), code=2)
    _echo_payload(_api_request("POST", "/packs", body=body))


@project_member_app.callback(invoke_without_command=True)
def project_member_main(ctx: typer.Context) -> None:
    """Project developer membership commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@project_member_app.command("add", help="Add an active user as a project developer.")
def project_member_add(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
    user_id: Annotated[str, typer.Argument(help="User id, e.g. usr_...")],
) -> None:
    _echo_payload(_api_request("PUT", f"/projects/{project_id}/members/{user_id}"))


@project_member_app.command("remove", help="Remove a project developer membership.")
def project_member_remove(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
    user_id: Annotated[str, typer.Argument(help="User id, e.g. usr_...")],
) -> None:
    _echo_payload(_api_request("DELETE", f"/projects/{project_id}/members/{user_id}"))


@project_pack_app.callback(invoke_without_command=True)
def project_pack_main(ctx: typer.Context) -> None:
    """Project pack assignment commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@project_pack_app.command("list", help="List project pack assignments.")
def project_pack_list(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
) -> None:
    _echo_payload(_api_request("GET", f"/projects/{project_id}/packs"))


@project_pack_app.command("add", help="Assign a pack to a project.")
def project_pack_add(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
    pack_ref: Annotated[str, typer.Argument(help="Pack ref, e.g. acme/name@1.0.0.")],
    position: Annotated[int, typer.Option("--position", help="Assignment order.")] = 0,
) -> None:
    _echo_payload(
        _api_request(
            "POST",
            f"/projects/{project_id}/packs",
            body={"pack_ref": pack_ref, "position": position},
        )
    )


@project_pack_app.command("update", help="Update a project pack assignment.")
def project_pack_update(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
    assignment_id: Annotated[str, typer.Argument(help="Assignment id, e.g. asn_...")],
    pack_ref: Annotated[
        str | None, typer.Option("--pack-ref", help="New pack ref.")
    ] = None,
    position: Annotated[
        int | None, typer.Option("--position", help="New order.")
    ] = None,
    active: Annotated[
        bool | None,
        typer.Option("--active/--inactive", help="Set whether assignment is active."),
    ] = None,
) -> None:
    _echo_payload(
        _api_request(
            "PATCH",
            f"/projects/{project_id}/packs/{assignment_id}",
            body=_body_without_none(
                pack_ref=pack_ref, position=position, active=active
            ),
        )
    )


@project_pack_app.command("remove", help="Deactivate a project pack assignment.")
def project_pack_remove(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
    assignment_id: Annotated[str, typer.Argument(help="Assignment id, e.g. asn_...")],
) -> None:
    _echo_payload(
        _api_request("DELETE", f"/projects/{project_id}/packs/{assignment_id}")
    )


if __name__ == "__main__":
    app()
