"""Typer CLI entrypoint for Agent Guidance Hub."""

from __future__ import annotations

from collections.abc import Iterable
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Annotated, Any, NoReturn

import typer
from typer.core import TyperGroup

from agh.cli.agent_integrations import (
    detect_agent_availability,
    format_agent_availability,
)
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
from agh.cli.pack_init import PackInitError, init_pack_template
from agh.cli.pack_publish import PackPublishBuildError, build_pack_publish_payload
from agh.cli.workspace_pull import (
    WorkspacePullError,
    WorkspacePullResult,
    pull_workspace,
)
from agh.cli.workspace_sync import SyncResult, WorkspaceSyncError, sync_workspace

APP_HELP = """Agent Guidance Hub — manage and distribute agent guidance packs.

Usage:
  agh [OPTIONS] COMMAND [ARGS]...

Commands:
  login        Validate API credentials with /api/v1/me and save local config.
  config show  Show the saved instance URL, email, and masked token.
  user         Manage users.
  token        Rotate or reset user API tokens.
  project      Manage projects and developer memberships.
  pack         Create, publish, and list guidance packs.
  sync         Link this git repository to its matching AGH project.
  pull         Pull assigned guidance packs into this repository.
  agent        Show advisory local agent integration availability.

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
    help="Create, publish, and list AGH packs.",
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

    _echo_pull_result(result)
    if result.vcs_hint:
        typer.echo(result.vcs_hint)
    raise typer.Exit(result.exit_code)


def _echo_pull_result(result: WorkspacePullResult) -> None:
    changed_paths = _sort_pull_paths(
        change.target_path
        for change in result.plan.changes
        if change.status in {"insert", "update"}
    )
    conflict_paths = _sort_pull_paths(
        change.target_path for change in result.plan.changes if change.conflicts
    )
    conflict_count = len(conflict_paths)

    if conflict_count:
        typer.echo(
            f"Pull blocked: {conflict_count} {_plural(conflict_count, 'conflict')}."
        )
        typer.echo("Conflicts:")
        for path in conflict_paths:
            typer.echo(f"  {path}")
        typer.echo()
        typer.echo("Run with --force to replace AGH-managed blocks.")
        return

    if result.dry_run:
        change_count = len(changed_paths)
        typer.echo(
            f"Dry run complete: {change_count} {_plural(change_count, 'change')} "
            f"planned, 0 conflicts."
        )
        if changed_paths:
            typer.echo("Planned:")
            for path in changed_paths:
                typer.echo(f"  {path}")
            typer.echo()
        typer.echo("No files were written.")
        return

    change_count = len(changed_paths)
    if change_count:
        typer.echo(
            f"Pull complete: {change_count} {_plural(change_count, 'changed')}, 0 conflicts."
        )
        typer.echo("Updated:")
        for path in changed_paths:
            typer.echo(f"  {path}")
        typer.echo()
    else:
        typer.echo("Pull complete: no changes.")

    if result.cache_result is not None:
        typer.echo(f"Lockfile: {_format_cli_path(result.cache_result.lock_path)}")


def _sort_pull_paths(paths: Iterable[str]) -> list[str]:
    return sorted(paths, key=lambda path: (path.startswith("."), path))


def _plural(count: int, singular: str) -> str:
    if count == 1:
        return singular
    if singular == "changed":
        return "changed"
    return f"{singular}s"


@app.command("agent", help="Show advisory local agent integration availability.")
def agent() -> None:
    """Show detected Claude Code and OpenCode local integration availability."""
    typer.echo(format_agent_availability(detect_agent_availability()))


def _format_cli_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _echo_sync_success(result: SyncResult) -> None:
    action = "Updated repo link to" if result.replaced else "Linked this repo to"
    typer.echo(f"{action} {result.project_name} ({result.project_id}).")
    typer.echo(f"Project file: {_format_cli_path(result.link_path)}")
    typer.echo(f"Remote: {result.repo_url_normalized}")
    typer.echo(f"Server: {result.instance_url}")


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

    _echo_sync_success(result)


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


def _status_label(payload: dict[str, Any]) -> str:
    return "active" if payload.get("active", True) else "inactive"


def _echo_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    typer.echo(_format_table_row(headers, widths))
    for row in rows:
        typer.echo(_format_table_row(row, widths))


def _format_table_row(values: list[str], widths: list[int]) -> str:
    cells = [value.ljust(widths[index]) for index, value in enumerate(values[:-1])]
    cells.append(values[-1])
    return "  ".join(cells).rstrip()


ONE_TIME_TOKEN_WARNING = "Store this token now. AGH will not show it again."


def _echo_user_list(payload: dict[str, Any]) -> None:
    users = payload.get("users", [])
    if not users:
        typer.echo("No users found.")
        return
    _echo_table(
        ["USER_ID", "EMAIL", "ROLE", "STATUS"],
        [
            [
                str(user.get("id", "")),
                str(user.get("email", "")),
                str(user.get("role", "")),
                _status_label(user),
            ]
            for user in users
        ],
    )


def _echo_user_created(payload: dict[str, Any]) -> None:
    user = payload.get("user", {})
    if not isinstance(user, dict):
        user = {}
    token = _required_plaintext_token(payload)
    typer.echo(f"Created user {user.get('email', '')} ({user.get('id', '')}).")
    typer.echo(f"Role: {user.get('role', '')}")
    typer.echo(f"Status: {_status_label(user)}")
    typer.echo(f"Token: {token}")
    typer.echo(ONE_TIME_TOKEN_WARNING)


def _echo_user_updated(user: dict[str, Any]) -> None:
    typer.echo(f"Updated user {user.get('email', '')} ({user.get('id', '')}).")
    typer.echo(f"Role: {user.get('role', '')}")
    typer.echo(f"Status: {_status_label(user)}")


def _echo_user_deactivated(user: dict[str, Any]) -> None:
    typer.echo(f"Deactivated user {user.get('email', '')} ({user.get('id', '')}).")


def _echo_token_issued(verb: str, payload: dict[str, Any], *, user_id: str) -> None:
    token = _required_plaintext_token(payload)
    typer.echo(f"{verb} token for user {user_id}.")
    typer.echo(f"Token: {token}")
    typer.echo(ONE_TIME_TOKEN_WARNING)


def _required_plaintext_token(payload: dict[str, Any]) -> str:
    token = payload.get("token")
    if not isinstance(token, str) or not token:
        _fail("server response did not include the one-time plaintext token")
    return token


def _echo_project_list(payload: dict[str, Any]) -> None:
    projects = payload.get("projects", [])
    if not projects:
        typer.echo("No projects found.")
        return
    _echo_table(
        ["PROJECT_ID", "NAME", "REPO", "STATUS"],
        [
            [
                str(project.get("id", "")),
                str(project.get("name", "")),
                str(project.get("repo_url_normalized", "")),
                _status_label(project),
            ]
            for project in projects
        ],
    )


def _echo_pack_list(payload: dict[str, Any]) -> None:
    packs = payload.get("packs", [])
    if not packs:
        typer.echo("No packs found.")
        return
    _echo_table(
        ["PACK_REF", "DESCRIPTION"],
        [[_pack_ref(pack), str(pack.get("description", ""))] for pack in packs],
    )


def _pack_ref(pack: dict[str, Any]) -> str:
    if pack.get("id"):
        return str(pack["id"])
    return f"{pack.get('domain', '')}/{pack.get('name', '')}@{pack.get('version', '')}"


def _echo_pack_published(pack: dict[str, Any]) -> None:
    typer.echo(f"Published {_pack_ref(pack)}.")
    if pack.get("pack_id"):
        typer.echo(f"Pack ID: {pack.get('pack_id')}")
    if pack.get("description"):
        typer.echo(f"Description: {pack.get('description')}")
    if pack.get("checksum"):
        typer.echo(f"Checksum: {pack.get('checksum')}")


def _echo_project_pack_list(payload: dict[str, Any]) -> None:
    assignments = payload.get("project_packs", [])
    if not assignments:
        typer.echo("No assigned packs found.")
        return
    _echo_table(
        ["ASSIGNMENT_ID", "PACK_REF", "RESOLVED", "POSITION", "STATUS"],
        [
            [
                str(assignment.get("id", "")),
                str(assignment.get("pack_ref", "")),
                str(assignment.get("resolved_ref") or assignment.get("pack_ref", "")),
                str(assignment.get("position", 0)),
                _status_label(assignment),
            ]
            for assignment in assignments
        ],
    )


def _echo_project_detail(project: dict[str, Any]) -> None:
    typer.echo(f"Project: {project.get('name', '')}")
    typer.echo(f"Project ID: {project.get('id', '')}")
    typer.echo(f"Repo: {project.get('repo_url_normalized', '')}")
    typer.echo(f"Status: {_status_label(project)}")


def _echo_project_success(verb: str, project: dict[str, Any]) -> None:
    typer.echo(f"{verb} project {project.get('name', '')} ({project.get('id', '')}).")
    typer.echo(f"Repo: {project.get('repo_url_normalized', '')}")
    typer.echo(f"Status: {_status_label(project)}")


def _echo_project_deactivated(project: dict[str, Any]) -> None:
    typer.echo(
        f"Deactivated project {project.get('name', '')} ({project.get('id', '')})."
    )


def _echo_project_member_success(
    verb: str, payload: dict[str, Any], *, project_id: str, user_id: str
) -> None:
    returned_project_id = str(payload.get("project_id") or project_id)
    returned_user_id = str(payload.get("user_id") or user_id)
    typer.echo(
        f"{verb} user {returned_user_id} {'to' if verb == 'Added' else 'from'} project {returned_project_id}."
    )


def _echo_project_pack_assigned(payload: dict[str, Any], *, project_id: str) -> None:
    pack_ref = str(payload.get("pack_ref", ""))
    typer.echo(f"Assigned {pack_ref} to project {project_id}.")
    typer.echo(f"Resolved: {payload.get('resolved_ref') or pack_ref}")
    typer.echo(f"Assignment: {payload.get('id', '')}")


def _echo_project_pack_updated(
    payload: dict[str, Any], *, project_id: str, assignment_id: str
) -> None:
    returned_assignment_id = str(payload.get("id") or assignment_id)
    pack_ref = str(payload.get("pack_ref", ""))
    typer.echo(f"Updated assignment {returned_assignment_id} on project {project_id}.")
    typer.echo(f"Pack: {pack_ref}")
    typer.echo(f"Resolved: {payload.get('resolved_ref') or pack_ref}")
    typer.echo(f"Position: {payload.get('position', 0)}")
    typer.echo(f"Status: {_status_label(payload)}")


def _echo_project_pack_removed(
    payload: dict[str, Any], *, project_id: str, assignment_id: str
) -> None:
    returned_assignment_id = str(payload.get("id") or assignment_id)
    typer.echo(
        f"Removed assignment {returned_assignment_id} from project {project_id}."
    )


@user_app.callback(invoke_without_command=True)
def user_main(ctx: typer.Context) -> None:
    """User administration commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@user_app.command("list", help="List users visible to the authenticated admin.")
def user_list() -> None:
    _echo_user_list(_api_request("GET", "/users"))


@user_app.command("create", help="Create a user and print the issued token once.")
def user_create(
    email: Annotated[str, typer.Argument(help="User email address.")],
    role: Annotated[
        str,
        typer.Option("--role", help="Global role: owner, admin, or member."),
    ] = "member",
) -> None:
    payload = _api_request("POST", "/users", body={"email": email, "role": role})
    _echo_user_created(payload)


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
    _echo_user_updated(
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
    _echo_user_deactivated(_api_request("DELETE", user_path(user_id)))


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
    _echo_token_issued(
        "Rotated",
        _api_request("POST", f"/users/{user_id}/token:rotate"),
        user_id=user_id,
    )


@token_app.command("reset", help="Reset a user's token and print the new token once.")
def token_reset(
    user_id: Annotated[str, typer.Argument(help="User id, e.g. usr_...")],
) -> None:
    _echo_token_issued(
        "Reset",
        _api_request("POST", f"/users/{user_id}/token:reset"),
        user_id=user_id,
    )


@project_app.callback(invoke_without_command=True)
def project_main(ctx: typer.Context) -> None:
    """Project administration commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@project_app.command("list", help="List projects visible to the authenticated user.")
def project_list() -> None:
    _echo_project_list(_api_request("GET", "/projects"))


@project_app.command("create", help="Create a project.")
def project_create(
    name: Annotated[str, typer.Argument(help="Project display name.")],
    repo_url: Annotated[
        str,
        typer.Option("--repo-url", help="Git repository URL linked to the project."),
    ],
) -> None:
    _echo_project_success(
        "Created",
        _api_request("POST", "/projects", body={"name": name, "repo_url": repo_url}),
    )


@project_app.command("get", help="Show one project by id.")
def project_get(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
) -> None:
    _echo_project_detail(_api_request("GET", project_path(project_id)))


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
    _echo_project_success(
        "Updated",
        _api_request(
            "PATCH",
            project_path(project_id),
            body=_body_without_none(name=name, repo_url=repo_url, active=active),
        ),
    )


@project_app.command("delete", help="Deactivate a project.")
def project_delete(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
) -> None:
    _echo_project_deactivated(_api_request("DELETE", project_path(project_id)))


def project_path(project_id: str) -> str:
    return f"/projects/{project_id}"


@pack_app.callback(invoke_without_command=True)
def pack_main(ctx: typer.Context) -> None:
    """Pack init/publish/list commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@pack_app.command("list", help="List published pack versions.")
def pack_list() -> None:
    _echo_pack_list(_api_request("GET", "/packs"))


@pack_app.command("init", help="Create a local pack template.")
def pack_init(
    path: Annotated[Path, typer.Argument(help="Directory to create for the pack.")],
    domain: Annotated[str, typer.Option("--domain", help="Pack domain slug.")],
    name: Annotated[str, typer.Option("--name", help="Pack name slug.")],
    version: Annotated[str, typer.Option("--version", help="Initial SemVer version.")],
    description: Annotated[
        str, typer.Option("--description", help="Manifest description.")
    ] = "TODO",
    with_agents: Annotated[
        bool, typer.Option("--with-agents", help="Create instructions/AGENTS.md.")
    ] = False,
    with_claude: Annotated[
        bool, typer.Option("--with-claude", help="Create instructions/CLAUDE.md.")
    ] = False,
    with_skill: Annotated[
        list[str] | None,
        typer.Option("--with-skill", help="Create skills/NAME/SKILL.md."),
    ] = None,
) -> None:
    try:
        result = init_pack_template(
            path,
            domain=domain,
            name=name,
            version=version,
            description=description,
            with_agents=with_agents,
            with_claude=with_claude,
            skills=with_skill,
        )
    except PackInitError as exc:
        _fail(str(exc), code=2)
    typer.echo(f"Initialized pack template at {result.root}")
    typer.echo(f"Manifest: {result.manifest}")
    typer.echo(
        f"Next: add instructions or skills, then run agh pack publish {result.root}"
    )


@pack_app.command("publish", help="Publish a local pack directory.")
def pack_publish(
    path: Annotated[Path, typer.Argument(help="Directory containing agh.pack.toml.")],
) -> None:
    try:
        body = build_pack_publish_payload(path)
    except PackPublishBuildError as exc:
        _fail(str(exc), code=2)
    _echo_pack_published(_api_request("POST", "/packs", body=body))


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
    _echo_project_member_success(
        "Added",
        _api_request("PUT", f"/projects/{project_id}/members/{user_id}"),
        project_id=project_id,
        user_id=user_id,
    )


@project_member_app.command("remove", help="Remove a project developer membership.")
def project_member_remove(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
    user_id: Annotated[str, typer.Argument(help="User id, e.g. usr_...")],
) -> None:
    _echo_project_member_success(
        "Removed",
        _api_request("DELETE", f"/projects/{project_id}/members/{user_id}"),
        project_id=project_id,
        user_id=user_id,
    )


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
    _echo_project_pack_list(_api_request("GET", f"/projects/{project_id}/packs"))


@project_pack_app.command("add", help="Assign a pack to a project.")
def project_pack_add(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
    pack_ref: Annotated[str, typer.Argument(help="Pack ref, e.g. acme/name@1.0.0.")],
    position: Annotated[int, typer.Option("--position", help="Assignment order.")] = 0,
) -> None:
    _echo_project_pack_assigned(
        _api_request(
            "POST",
            f"/projects/{project_id}/packs",
            body={"pack_ref": pack_ref, "position": position},
        ),
        project_id=project_id,
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
    _echo_project_pack_updated(
        _api_request(
            "PATCH",
            f"/projects/{project_id}/packs/{assignment_id}",
            body=_body_without_none(
                pack_ref=pack_ref, position=position, active=active
            ),
        ),
        project_id=project_id,
        assignment_id=assignment_id,
    )


@project_pack_app.command("remove", help="Deactivate a project pack assignment.")
def project_pack_remove(
    project_id: Annotated[str, typer.Argument(help="Project id, e.g. prj_...")],
    assignment_id: Annotated[str, typer.Argument(help="Assignment id, e.g. asn_...")],
) -> None:
    _echo_project_pack_removed(
        _api_request("DELETE", f"/projects/{project_id}/packs/{assignment_id}"),
        project_id=project_id,
        assignment_id=assignment_id,
    )


if __name__ == "__main__":
    app()
