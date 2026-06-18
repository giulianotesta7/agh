"""Typer CLI entrypoint for Agent Guidance Hub."""

from __future__ import annotations

from collections.abc import Iterable
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Annotated, Any, NoReturn

import typer
from typer.core import TyperGroup

from agh.cli.agent_integrations import (
    AGENT_LABELS,
    SUPPORTED_AGENT_TARGETS,
    AgentPreferenceError,
    clear_agent_preference,
    clear_global_skill_default_agent,
    detect_agent_availability,
    format_agent_availability,
    format_agent_preference,
    read_agent_preference,
    read_global_skill_default_agent,
    write_agent_preference,
    write_global_skill_default_agent,
)
from agh.cli import global_skills as global_skills_module
from agh.cli.global_skills import GlobalSkillError
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
from agh.cli.package_init import PackageInitError, init_package_template
from agh.cli.package_publish import (
    PackagePublishBuildError,
    build_package_publish_payload,
)
from agh.cli.package_refs import (
    PackageVersionRefResolutionError,
    resolve_package_version_ref,
)
from agh.cli.project_refs import ProjectRefResolutionError, resolve_project_ref
from agh.cli.user_refs import UserRefResolutionError, resolve_user_ref
from agh.cli.workspace_pull import (
    WorkspacePullError,
    WorkspacePullResult,
    pull_workspace,
)
from agh.cli.workspace_sync import SyncResult, WorkspaceSyncError, sync_workspace
from agh.common.validation import validate_project_name

APP_HELP = """Agent Guidance Hub — manage and distribute agent guidance packages.

Usage:
  agh [OPTIONS] COMMAND [ARGS]...

Commands:
  login        Validate API credentials with /api/v1/me and save local config.
  config show  Show the saved instance URL, email, and masked token.
  user         Manage users.
  token        Rotate or reset user API tokens.
  project      Manage projects and developer memberships.
  package         Create, publish, and list guidance packages.
  sync         Link this git repository to its matching AGH project.
  pull         Pull assigned guidance packages into this repository.
  agent        Show and manage local agent selection.
  skill        Discover, install, and remove collection-backed global skills.

Global options:
  --help       Show this help page.

Arguments:
  Run `agh <command> --help` for command-specific options and arguments.
"""
USAGE_ERROR_EXIT_CODE = 2
COMMAND_CANCELLED_EXIT_CODE = 130
PROJECT_REF_HELP = "Project id or exact name. Numeric refs are treated as ids."
USER_REF_HELP = "User id or exact email."
PACKAGE_VERSION_REF_HELP = (
    "Package ref: pkgv_..., domain/name@version, or name@version."
)


def _exit_on_unknown_command(group: TyperGroup, ctx: Any, args: list[str]) -> None:
    if not args:
        return

    command_name = args[0]
    command = group.get_command(ctx, command_name)
    if command is None and not command_name.startswith("-"):
        typer.echo(APP_HELP)
        raise typer.Exit(USAGE_ERROR_EXIT_CODE)


class AghHelpGroup(TyperGroup):
    """Typer group that shows AGH's command overview for help/unknown commands."""

    def get_help(self, ctx: Any) -> str:
        return APP_HELP

    def resolve_command(self, ctx: Any, args: list[str]) -> Any:
        _exit_on_unknown_command(self, ctx, args)
        return super().resolve_command(ctx, args)


class AghSubcommandGroup(TyperGroup):
    """Typer subgroup that keeps real help but routes unknown commands to APP_HELP."""

    def resolve_command(self, ctx: Any, args: list[str]) -> Any:
        _exit_on_unknown_command(self, ctx, args)
        return super().resolve_command(ctx, args)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects so Bearer tokens are never forwarded to another URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)

app = typer.Typer(
    name="agh",
    cls=AghHelpGroup,
    help="Agent Guidance Hub — manage and distribute agent guidance packages.",
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
project_package_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Manage project package assignments.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
package_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Create, publish, and list guidance packages.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
agent_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Show and manage local agent selection.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
skill_app = typer.Typer(
    cls=AghSubcommandGroup,
    help=(
        "Discover, install, and remove collection-backed global skills.\n\n"
        "OpenCode: ~/.config/opencode/skills\n\n"
        "Claude: ~/.claude/skills\n\n"
        "Agent selection uses the saved global-skills default; otherwise AGH "
        "prompts with `Select the agent for global skills:`."
    ),
    no_args_is_help=False,
    rich_markup_mode=None,
)
skill_agent_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Manage the saved default agent for global skill commands.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
app.add_typer(config_app, name="config")
app.add_typer(user_app, name="user")
app.add_typer(token_app, name="token")
app.add_typer(project_app, name="project")
app.add_typer(package_app, name="package")
app.add_typer(agent_app, name="agent")
app.add_typer(skill_app, name="skill")
project_app.add_typer(project_member_app, name="member")
project_app.add_typer(project_package_app, name="package")
skill_app.add_typer(skill_agent_app, name="agent")


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


def _clean_project_name_or_exit(name: str) -> str:
    try:
        return validate_project_name(name)
    except ValueError as exc:
        _fail(str(exc), code=2)


def _resolve_project_ref(project_ref: str) -> str:
    try:
        return resolve_project_ref(project_ref, _api_request)
    except ProjectRefResolutionError as exc:
        _fail(str(exc))


def _resolve_user_ref(user_ref: str) -> str:
    try:
        return resolve_user_ref(user_ref, _api_request)
    except UserRefResolutionError as exc:
        _fail(str(exc), code=exc.code)


def _resolve_package_version_ref(package_ref: str) -> str:
    try:
        return resolve_package_version_ref(package_ref, _api_request)
    except PackageVersionRefResolutionError as exc:
        _fail(str(exc), code=exc.code)


global_skills_module.configure_api_request(_api_request)


@app.command("pull", help="Pull assigned guidance packages into this repository.")
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


@agent_app.callback(invoke_without_command=True)
def agent(
    ctx: typer.Context,
) -> None:
    """Show detected integrations and the local workspace selection."""
    if ctx.invoked_subcommand is None:
        _echo_agent_show()


@agent_app.command("show", help="Show local agent availability and selection.")
def agent_show() -> None:
    """Show detected integrations and the local workspace selection."""
    _echo_agent_show()


@agent_app.command("select", help="Select this workspace's local agent target.")
def agent_select(
    target: Annotated[
        str,
        typer.Argument(help="Agent target: claude or opencode."),
    ],
) -> None:
    """Write .agh-cache/preferences.toml for this developer/workspace."""
    if target not in SUPPORTED_AGENT_TARGETS:
        _fail("agent target must be 'claude' or 'opencode'", code=2)
    try:
        preference = write_agent_preference(target)
    except AgentPreferenceError as exc:
        _fail(str(exc), code=exc.code)
    typer.echo(f"Selected {AGENT_LABELS[target]} for this workspace.")
    typer.echo(f"Preferences: {_format_cli_path(preference.path)}")


@agent_app.command("clear", help="Clear this workspace's local agent selection.")
def agent_clear() -> None:
    """Remove .agh-cache/preferences.toml if present."""
    try:
        removed = clear_agent_preference()
    except AgentPreferenceError as exc:
        _fail(str(exc), code=exc.code)
    if removed:
        typer.echo("Cleared local agent selection.")
    else:
        typer.echo("No local agent selection was set.")


def _resolve_global_skill_agent(agent_option: str | None) -> str:
    if agent_option is not None:
        if agent_option not in SUPPORTED_AGENT_TARGETS:
            _fail("agent target must be 'claude' or 'opencode'", code=2)
        return agent_option
    try:
        default = read_global_skill_default_agent()
    except AgentPreferenceError as exc:
        _fail(str(exc), code=exc.code)
    if default is not None:
        return default
    if not _stdin_is_interactive():
        _fail("no default global skill agent; use --agent or run interactively", code=2)
    return _prompt_global_skill_agent()


def _prompt_global_skill_agent() -> str:
    typer.echo("Select the agent for global skills:")
    for index, target in enumerate(SUPPORTED_AGENT_TARGETS, start=1):
        typer.echo(f"{index}. {AGENT_LABELS[target]} ({target})")
    choice_index = _prompt_selection_index(
        "Select an agent", count=len(SUPPORTED_AGENT_TARGETS)
    )
    selected = SUPPORTED_AGENT_TARGETS[choice_index]
    try:
        has_default = read_global_skill_default_agent() is not None
    except AgentPreferenceError:
        has_default = False
    if not has_default and typer.confirm(
        "Save this as the default agent for global skills?"
    ):
        try:
            write_global_skill_default_agent(selected)
        except AgentPreferenceError as exc:
            _fail(str(exc), code=exc.code)
    return selected


@skill_app.command("list", help="List skills available from collection catalogs.")
def skill_list() -> None:
    """Fetch available collection-backed skills."""
    payload = _api_request("GET", "/skills")
    skills = payload.get("skills", []) if isinstance(payload, dict) else []
    if not skills:
        typer.echo("No skills available.")
        return
    _echo_table(
        ["SKILL_NAME", "COLLECTION", "PACKAGE_REF", "RESOLVED_REF", "DESCRIPTION"],
        [
            [
                str(skill.get("skill_name", "")),
                str(skill.get("collection_name", "")),
                str(skill.get("package_ref", "")),
                str(skill.get("resolved_ref", "")),
                str(skill.get("description", "")),
            ]
            for skill in skills
        ],
    )


@skill_app.command(
    "install", help="Install a collection-backed skill into the selected global agent."
)
def skill_install(
    package_ref: Annotated[
        str, typer.Argument(help="Package ref such as acme/pkg@latest.")
    ],
    skill_name: Annotated[str, typer.Argument(help="Skill name to install.")],
    agent: Annotated[
        str | None,
        typer.Option(
            "--agent",
            help=(
                "Use --agent to choose claude or opencode. If omitted, use the "
                "saved default or prompt interactively."
            ),
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite an untracked target skill file."),
    ] = False,
) -> None:
    """Resolve, download, and install a collection skill."""
    selected_agent = _resolve_global_skill_agent(agent)
    try:
        result = global_skills_module.install_skill_global(
            selected_agent, package_ref, skill_name, force=force
        )
    except GlobalSkillError as exc:
        _fail(str(exc), code=exc.code)
    if result.changed:
        typer.echo(
            f"Installed {skill_name} for {AGENT_LABELS[selected_agent]} "
            f"at {_format_cli_path(result.target_path)}."
        )
    else:
        typer.echo(
            f"{skill_name} is already up to date for {AGENT_LABELS[selected_agent]}."
        )


@skill_app.command("remove", help="Remove a globally installed skill.")
def skill_remove(
    skill_name: Annotated[str, typer.Argument(help="Skill name to remove.")],
    agent: Annotated[
        str | None,
        typer.Option(
            "--agent",
            help=(
                "Use --agent to choose claude or opencode. If omitted, use the "
                "saved default or prompt interactively."
            ),
        ),
    ] = None,
) -> None:
    """Remove a global skill from the selected agent and lock file."""
    selected_agent = _resolve_global_skill_agent(agent)
    try:
        global_skills_module.remove_skill_global(selected_agent, skill_name)
    except GlobalSkillError as exc:
        _fail(str(exc), code=exc.code)
    typer.echo(f"Removed {skill_name} for {AGENT_LABELS[selected_agent]}.")


@skill_app.command("installed", help="List globally installed skills for the agent.")
def skill_installed(
    agent: Annotated[
        str | None,
        typer.Option(
            "--agent",
            help=(
                "Use --agent to choose claude or opencode. If omitted, use the "
                "saved default or prompt interactively."
            ),
        ),
    ] = None,
) -> None:
    """Show installed global skills from the local lock file."""
    selected_agent = _resolve_global_skill_agent(agent)
    entries = global_skills_module.list_installed_skills(selected_agent)
    if not entries:
        typer.echo(f"No global skills installed for {AGENT_LABELS[selected_agent]}.")
        return
    _echo_table(
        ["SKILL_NAME", "PACKAGE_REF", "CHECKSUM"],
        [
            [
                str(entry.get("name", "")),
                str(entry.get("package_ref_resolved", "")),
                str(entry.get("checksum", "")),
            ]
            for entry in entries
        ],
    )


@skill_agent_app.callback(invoke_without_command=True)
def skill_agent_main(ctx: typer.Context) -> None:
    """Show the current default global skill agent."""
    if ctx.invoked_subcommand is None:
        skill_agent_show()


@skill_agent_app.command("show", help="Show the default agent for global skills.")
def skill_agent_show() -> None:
    """Read and display the saved default global skill agent."""
    try:
        default = read_global_skill_default_agent()
    except AgentPreferenceError as exc:
        _fail(str(exc), code=exc.code)
    if default is None:
        typer.echo("Default global skill agent: not set.")
    else:
        typer.echo(f"Default global skill agent: {AGENT_LABELS[default]} ({default}).")


@skill_agent_app.command("select", help="Set the default agent for global skills.")
def skill_agent_select(
    target: Annotated[
        str,
        typer.Argument(help="Default agent target: claude or opencode."),
    ],
) -> None:
    """Persist the default agent for future global skill commands."""
    if target not in SUPPORTED_AGENT_TARGETS:
        _fail("agent target must be 'claude' or 'opencode'", code=2)
    try:
        write_global_skill_default_agent(target)
    except AgentPreferenceError as exc:
        _fail(str(exc), code=exc.code)
    typer.echo(f"Set default global skill agent to {AGENT_LABELS[target]} ({target}).")


@skill_agent_app.command("clear", help="Clear the default agent for global skills.")
def skill_agent_clear() -> None:
    """Remove the saved default global skill agent."""
    try:
        removed = clear_global_skill_default_agent()
    except AgentPreferenceError as exc:
        _fail(str(exc), code=exc.code)
    if removed:
        typer.echo("Cleared default global skill agent.")
    else:
        typer.echo("No default global skill agent was set.")


def _echo_agent_show() -> None:
    try:
        preference = read_agent_preference()
    except AgentPreferenceError as exc:
        _fail(str(exc), code=exc.code)
    typer.echo(format_agent_preference(preference))
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


def _echo_user_detail(user: dict[str, Any]) -> None:
    typer.echo(f"User: {user.get('email', '')}")
    typer.echo(f"User ID: {user.get('id', '')}")
    typer.echo(f"Role: {user.get('role', '')}")
    typer.echo(f"Status: {_status_label(user)}")


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


def _echo_package_list(payload: dict[str, Any]) -> None:
    packages = payload.get("packages", [])
    if not packages:
        typer.echo("No packages found.")
        return
    _echo_table(
        ["PACKAGE_REF", "DESCRIPTION"],
        [
            [_package_ref(package), str(package.get("description", ""))]
            for package in packages
        ],
    )


def _package_ref(package: dict[str, Any]) -> str:
    if package.get("id"):
        return str(package["id"])
    return f"{package.get('domain', '')}/{package.get('name', '')}@{package.get('version', '')}"


def _echo_package_published(package: dict[str, Any]) -> None:
    typer.echo(f"Published {_package_ref(package)}.")
    if package.get("package_id"):
        typer.echo(f"Package ID: {package.get('package_id')}")
    if package.get("description"):
        typer.echo(f"Description: {package.get('description')}")
    if package.get("checksum"):
        typer.echo(f"Checksum: {package.get('checksum')}")


def _echo_project_package_list(payload: dict[str, Any]) -> None:
    assignments = payload.get("project_packages", [])
    if not assignments:
        typer.echo("No assigned packages found.")
        return
    _echo_table(
        ["ASSIGNMENT_ID", "PACKAGE_REF", "RESOLVED", "POSITION", "STATUS"],
        [
            [
                str(assignment.get("id", "")),
                str(assignment.get("package_ref", "")),
                str(
                    assignment.get("resolved_ref") or assignment.get("package_ref", "")
                ),
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


def _echo_project_package_assigned(payload: dict[str, Any], *, project_id: str) -> None:
    package_ref = str(payload.get("package_ref", ""))
    typer.echo(f"Assigned {package_ref} to project {project_id}.")
    typer.echo(f"Resolved: {payload.get('resolved_ref') or package_ref}")
    typer.echo(f"Assignment: {payload.get('id', '')}")


def _echo_project_package_updated(
    payload: dict[str, Any], *, project_id: str, assignment_id: str
) -> None:
    returned_assignment_id = str(payload.get("id") or assignment_id)
    package_ref = str(payload.get("package_ref", ""))
    typer.echo(f"Updated assignment {returned_assignment_id} on project {project_id}.")
    typer.echo(f"Package: {package_ref}")
    typer.echo(f"Resolved: {payload.get('resolved_ref') or package_ref}")
    typer.echo(f"Position: {payload.get('position', 0)}")
    typer.echo(f"Status: {_status_label(payload)}")


def _echo_project_package_removed(
    payload: dict[str, Any], *, project_id: str, assignment_id: str
) -> None:
    returned_assignment_id = str(payload.get("id") or assignment_id)
    typer.echo(
        f"Removed assignment {returned_assignment_id} from project {project_id}."
    )


def _stdin_is_interactive() -> bool:
    return sys.stdin.isatty()


def _prompt_selection_index(label: str, *, count: int) -> int:
    try:
        raw_choice = input(f"{label}: ").strip()
    except EOFError:
        _fail("selection requires input", code=USAGE_ERROR_EXIT_CODE)
    if not raw_choice:
        _fail("selection requires input", code=USAGE_ERROR_EXIT_CODE)
    try:
        choice = int(raw_choice)
    except ValueError:
        _fail("selection must be a number", code=USAGE_ERROR_EXIT_CODE)
    if choice < 1 or choice > count:
        _fail("selection is out of range", code=USAGE_ERROR_EXIT_CODE)
    return choice - 1


def _select_available_package_ref(project_id: str) -> str | None:
    if not _stdin_is_interactive():
        _fail_omitted_package_ref_requires_tty()
    payload = _api_request("GET", f"/projects/{project_id}/packages:available")
    packages = payload.get("packages", []) if isinstance(payload, dict) else []
    if not packages:
        typer.echo(f"No unassigned packages are available for project {project_id}.")
        typer.echo(
            f"Run `agh project package list {project_id}` to review assignments or "
            "`agh project package update` to change an existing assignment."
        )
        return None
    typer.echo("Available packages:")
    for index, package in enumerate(packages, start=1):
        package_ref = str(package.get("package_ref", ""))
        description = str(package.get("description", ""))
        suffix = f" - {description}" if description else ""
        typer.echo(f"{index}. {package_ref}{suffix}")

    choice_index = _prompt_selection_index("Select a package", count=len(packages))
    package_ref = str(packages[choice_index].get("package_ref", ""))
    if not package_ref:
        _fail("available package response did not include package_ref")
    if not typer.confirm(f"Assign {package_ref} to project {project_id}?"):
        typer.echo("Cancelled.")
        raise typer.Exit(COMMAND_CANCELLED_EXIT_CODE)
    return package_ref


def _select_visible_project_id() -> str | None:
    if not _stdin_is_interactive():
        _fail_omitted_package_ref_requires_tty()
    payload = _api_request("GET", "/projects")
    projects = payload.get("projects", []) if isinstance(payload, dict) else []
    if not projects:
        typer.echo("No projects found.")
        return None

    typer.echo("Visible projects:")
    for index, project in enumerate(projects, start=1):
        project_id = str(project.get("id", ""))
        name = str(project.get("name", ""))
        repo_url = str(project.get("repo_url_normalized", ""))
        suffix = f" - {repo_url}" if repo_url else ""
        typer.echo(f"{index}. {name} ({project_id}){suffix}")

    choice_index = _prompt_selection_index("Select a project", count=len(projects))
    project_id = str(projects[choice_index].get("id", ""))
    if not project_id:
        _fail("project response did not include project id")
    return project_id


def _fail_omitted_package_ref_requires_tty() -> None:
    _fail(
        "agh project package add without a package ref requires an "
        "interactive terminal",
        code=USAGE_ERROR_EXIT_CODE,
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


@user_app.command("show", help="Show one user by id or exact email.")
def user_show(
    user_id: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_user_id = _resolve_user_ref(user_id)
    _echo_user_detail(_api_request("GET", user_path(resolved_user_id)))


@user_app.command("update", help="Update user email, role, or active flag.")
def user_update(
    user_id: Annotated[str, typer.Argument(help=USER_REF_HELP)],
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
    resolved_user_id = _resolve_user_ref(user_id)
    _echo_user_updated(
        _api_request(
            "PATCH",
            user_path(resolved_user_id),
            body=_body_without_none(email=email, role=role, active=active),
        )
    )


@user_app.command("delete", help="Deactivate a user.")
def user_delete(
    user_id: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_user_id = _resolve_user_ref(user_id)
    _echo_user_deactivated(_api_request("DELETE", user_path(resolved_user_id)))


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
    user_id: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_user_id = _resolve_user_ref(user_id)
    _echo_token_issued(
        "Rotated",
        _api_request("POST", f"/users/{resolved_user_id}/token:rotate"),
        user_id=resolved_user_id,
    )


@token_app.command("reset", help="Reset a user's token and print the new token once.")
def token_reset(
    user_id: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_user_id = _resolve_user_ref(user_id)
    _echo_token_issued(
        "Reset",
        _api_request("POST", f"/users/{resolved_user_id}/token:reset"),
        user_id=resolved_user_id,
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
    cleaned_name = _clean_project_name_or_exit(name)
    _echo_project_success(
        "Created",
        _api_request(
            "POST", "/projects", body={"name": cleaned_name, "repo_url": repo_url}
        ),
    )


@project_app.command("get", help="Show one project by id or exact name.")
def project_get(
    project_id: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
) -> None:
    resolved_project_id = _resolve_project_ref(project_id)
    _echo_project_detail(_api_request("GET", project_path(resolved_project_id)))


@project_app.command(
    "update", help="Update project name, repo URL, or active flag by id or exact name."
)
def project_update(
    project_id: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
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
    cleaned_name = _clean_project_name_or_exit(name) if name is not None else None
    resolved_project_id = _resolve_project_ref(project_id)
    _echo_project_success(
        "Updated",
        _api_request(
            "PATCH",
            project_path(resolved_project_id),
            body=_body_without_none(
                name=cleaned_name,
                repo_url=repo_url,
                active=active,
            ),
        ),
    )


@project_app.command("delete", help="Deactivate a project by id or exact name.")
def project_delete(
    project_id: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
) -> None:
    resolved_project_id = _resolve_project_ref(project_id)
    _echo_project_deactivated(_api_request("DELETE", project_path(resolved_project_id)))


def project_path(project_id: str) -> str:
    return f"/projects/{project_id}"


@package_app.callback(invoke_without_command=True)
def package_main(ctx: typer.Context) -> None:
    """Package init/publish/list commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@package_app.command("list", help="List published package versions.")
def package_list() -> None:
    _echo_package_list(_api_request("GET", "/packages"))


@package_app.command("init", help="Create a local package template.")
def package_init(
    path: Annotated[Path, typer.Argument(help="Directory to create for the package.")],
    domain: Annotated[str, typer.Option("--domain", help="Package domain slug.")],
    name: Annotated[str, typer.Option("--name", help="Package name slug.")],
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
        result = init_package_template(
            path,
            domain=domain,
            name=name,
            version=version,
            description=description,
            with_agents=with_agents,
            with_claude=with_claude,
            skills=with_skill,
        )
    except PackageInitError as exc:
        _fail(str(exc), code=2)
    typer.echo(f"Initialized package template at {result.root}")
    typer.echo(f"Manifest: {result.manifest}")
    typer.echo(
        f"Next: add instructions or skills, then run agh package publish {result.root}"
    )


@package_app.command("publish", help="Publish a local package directory.")
def package_publish(
    path: Annotated[
        Path, typer.Argument(help="Directory containing agh.package.toml.")
    ],
) -> None:
    try:
        body = build_package_publish_payload(path)
    except PackagePublishBuildError as exc:
        _fail(str(exc), code=2)
    _echo_package_published(_api_request("POST", "/packages", body=body))


@project_member_app.callback(invoke_without_command=True)
def project_member_main(ctx: typer.Context) -> None:
    """Project developer membership commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@project_member_app.command("add", help="Add an active user as a project developer.")
def project_member_add(
    project_id: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
    user_id: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_project_id = _resolve_project_ref(project_id)
    resolved_user_id = _resolve_user_ref(user_id)
    _echo_project_member_success(
        "Added",
        _api_request(
            "PUT", f"/projects/{resolved_project_id}/members/{resolved_user_id}"
        ),
        project_id=resolved_project_id,
        user_id=resolved_user_id,
    )


@project_member_app.command("remove", help="Remove a project developer membership.")
def project_member_remove(
    project_id: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
    user_id: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_project_id = _resolve_project_ref(project_id)
    resolved_user_id = _resolve_user_ref(user_id)
    _echo_project_member_success(
        "Removed",
        _api_request(
            "DELETE", f"/projects/{resolved_project_id}/members/{resolved_user_id}"
        ),
        project_id=resolved_project_id,
        user_id=resolved_user_id,
    )


@project_package_app.callback(invoke_without_command=True)
def project_package_main(ctx: typer.Context) -> None:
    """Project package assignment commands."""
    if ctx.invoked_subcommand is None:
        typer.echo(APP_HELP)
        raise typer.Exit(0)


@project_package_app.command("list", help="List project package assignments.")
def project_package_list(
    project_id: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
) -> None:
    resolved_project_id = _resolve_project_ref(project_id)
    _echo_project_package_list(
        _api_request("GET", f"/projects/{resolved_project_id}/packages")
    )


@project_package_app.command("add", help="Assign a package to a project.")
def project_package_add(
    project_id: Annotated[str | None, typer.Argument(help=PROJECT_REF_HELP)] = None,
    package_ref: Annotated[
        str | None, typer.Argument(help=PACKAGE_VERSION_REF_HELP)
    ] = None,
    position: Annotated[int, typer.Option("--position", help="Assignment order.")] = 0,
) -> None:
    if package_ref is None and not _stdin_is_interactive():
        _fail_omitted_package_ref_requires_tty()
    if project_id is None:
        resolved_project_id = _select_visible_project_id()
        if resolved_project_id is None:
            return
    else:
        resolved_project_id = _resolve_project_ref(project_id)
    if package_ref is None:
        resolved_package_ref = _select_available_package_ref(resolved_project_id)
        if resolved_package_ref is None:
            return
    else:
        resolved_package_ref = _resolve_package_version_ref(package_ref)
    _echo_project_package_assigned(
        _api_request(
            "POST",
            f"/projects/{resolved_project_id}/packages",
            body={"package_ref": resolved_package_ref, "position": position},
        ),
        project_id=resolved_project_id,
    )


@project_package_app.command("update", help="Update a project package assignment.")
def project_package_update(
    project_id: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
    assignment_id: Annotated[str, typer.Argument(help="Assignment id, e.g. asn_...")],
    package_ref: Annotated[
        str | None, typer.Option("--package-ref", help=PACKAGE_VERSION_REF_HELP)
    ] = None,
    position: Annotated[
        int | None, typer.Option("--position", help="New order.")
    ] = None,
    active: Annotated[
        bool | None,
        typer.Option("--active/--inactive", help="Set whether assignment is active."),
    ] = None,
) -> None:
    resolved_project_id = _resolve_project_ref(project_id)
    resolved_package_ref = (
        _resolve_package_version_ref(package_ref) if package_ref is not None else None
    )
    _echo_project_package_updated(
        _api_request(
            "PATCH",
            f"/projects/{resolved_project_id}/packages/{assignment_id}",
            body=_body_without_none(
                package_ref=resolved_package_ref, position=position, active=active
            ),
        ),
        project_id=resolved_project_id,
        assignment_id=assignment_id,
    )


@project_package_app.command("remove", help="Deactivate a project package assignment.")
def project_package_remove(
    project_id: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
    assignment_id: Annotated[str, typer.Argument(help="Assignment id, e.g. asn_...")],
) -> None:
    resolved_project_id = _resolve_project_ref(project_id)
    _echo_project_package_removed(
        _api_request(
            "DELETE", f"/projects/{resolved_project_id}/packages/{assignment_id}"
        ),
        project_id=resolved_project_id,
        assignment_id=assignment_id,
    )


if __name__ == "__main__":
    app()
