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
from typer.core import TyperCommand, TyperGroup

from agh import __version__
from agh.cli.agent_integrations import (
    AGENT_LABELS,
    SUPPORTED_AGENT_TARGETS,
    AgentPreferenceError,
    clear_agent_preference,
    clear_global_skill_default_agent,
    detect_agent_availability,
    format_agent_availability,
    read_agent_preference,
    read_global_skill_default_agent,
    write_agent_preference,
    write_global_skill_default_agent,
)
from agh.cli import global_skills as global_skills_module
from agh.cli.global_skills import GlobalSkillError
from agh.cli.config import (
    ConfigCorruptError,
    ConfigError,
    LoginValidationError,
    clear_credentials,
    clear_instance_url,
    corrupt_config_recovery_message,
    get_config_path,
    load_config,
    load_instance_url,
    mask_token,
    save_credentials,
    save_instance_url,
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
from agh.cli.collection_refs import (
    CollectionRefResolutionError,
    resolve_collection_ref,
)
from agh.cli.project_refs import ProjectRefResolutionError, resolve_project_ref
from agh.cli.user_refs import UserRefResolutionError, resolve_user_ref
from agh.cli.workspace_pull import (
    WorkspacePullError,
    WorkspacePullResult,
    pull_workspace,
)
from agh.cli.workspace_sync import SyncResult, WorkspaceSyncError, sync_workspace
from agh.common.validation import parse_package_ref, validate_project_name

APP_HELP = """Agent Guidance Hub — manage and distribute agent guidance packages.

Usage:
  agh [--help] [--version] COMMAND [ARGS]...

Commands:
  config              Show the configured AGH instance URL.
    config set INSTANCE_URL  Configure the AGH instance URL.
    config clear      Clear the configured AGH instance URL.
  login               Validate credentials for the configured instance.
  whoami              Show the authenticated user.
  logout              Clear stored credentials.
  user                Manage users.
    user token        Rotate user API tokens.
  project             Manage projects and developer memberships.
    project member    Manage project developer memberships (list/add/remove).
  collection          Manage collections.
  package             Manage guidance packages and assignments.
  target              Show and manage local target selection.
  skill               Discover, install, and remove collection-backed global skills.
    skill agent       Manage the default agent for global skills.
  sync                Link this git repository to its matching AGH project.
  pull                Pull assigned guidance packages into this repository.

Global options:
  --help              Show this help page.
  --version           Show the AGH version.

Arguments:
  Run `agh <command> --help` for command-specific options and arguments.
"""
USAGE_ERROR_EXIT_CODE = 2
COMMAND_CANCELLED_EXIT_CODE = 130
HELP_OPTION_TEXT = "Show this help page."
PROJECT_REF_HELP = "Project ref: prj_..., numeric id, or exact project name."
USER_REF_HELP = "User ref: usr_... or exact email."
COLLECTION_REF_HELP = "Collection ref: col_... or exact active collection name."
PACKAGE_VERSION_REF_HELP = (
    "Package ref: pkgv_..., domain/name@version, or name@version."
)


def _exit_on_unknown_command(group: TyperGroup, ctx: Any, args: list[str]) -> None:
    if not args:
        return

    command_name = args[0]
    command = group.get_command(ctx, command_name)
    if command is None and not command_name.startswith("-"):
        # Show the help for the group that was invoked, so `agh user wrong`
        # surfaces user help instead of the root command map.
        typer.echo(group.get_help(ctx))
        raise typer.Exit(USAGE_ERROR_EXIT_CODE)


def _show_local_help(ctx: Any) -> None:
    """Render the LOCAL group/command help for `ctx`, never the root map."""
    typer.echo(ctx.get_help())
    raise typer.Exit(0)


class AghHelpGroup(TyperGroup):
    """Root group: renders the maintained full command-map help string."""

    def get_help(self, ctx: Any) -> str:
        return APP_HELP

    def get_help_option(self, ctx: Any) -> Any:
        option = super().get_help_option(ctx)
        if option is not None:
            option.help = HELP_OPTION_TEXT
        return option

    def resolve_command(self, ctx: Any, args: list[str]) -> Any:
        _exit_on_unknown_command(self, ctx, args)
        return super().resolve_command(ctx, args)


class AghSubcommandGroup(TyperGroup):
    """Subgroup: keeps real local help and routes unknown commands to it."""

    def get_help_option(self, ctx: Any) -> Any:
        option = super().get_help_option(ctx)
        if option is not None:
            option.help = HELP_OPTION_TEXT
        return option

    def resolve_command(self, ctx: Any, args: list[str]) -> Any:
        _exit_on_unknown_command(self, ctx, args)
        return super().resolve_command(ctx, args)


class AghCommand(TyperCommand):
    """Leaf command with AGH's concise help-option wording."""

    def get_help_option(self, ctx: Any) -> Any:
        option = super().get_help_option(ctx)
        if option is not None:
            option.help = HELP_OPTION_TEXT
        return option


def _use_agh_command_help_text(typer_app: typer.Typer) -> None:
    """Apply AGH help-option wording to every Typer leaf command."""
    for command_info in typer_app.registered_commands:
        if command_info.cls is None or command_info.cls is TyperCommand:
            command_info.cls = AghCommand
    for group_info in typer_app.registered_groups:
        if group_info.typer_instance is not None:
            _use_agh_command_help_text(group_info.typer_instance)


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
    cls=AghSubcommandGroup,
    help="Inspect and manage local AGH CLI configuration.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
user_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Manage AGH users.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
user_token_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Rotate user API tokens.",
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
collection_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Manage AGH collections.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
package_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Manage guidance packages and assignments.",
    no_args_is_help=False,
    rich_markup_mode=None,
)
target_app = typer.Typer(
    cls=AghSubcommandGroup,
    help="Show and manage local target selection.",
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
app.add_typer(project_app, name="project")
app.add_typer(collection_app, name="collection")
app.add_typer(package_app, name="package")
app.add_typer(target_app, name="target")
app.add_typer(skill_app, name="skill")
user_app.add_typer(user_token_app, name="token")
project_app.add_typer(project_member_app, name="member")
skill_app.add_typer(skill_agent_app, name="agent")


def _fail(message: str, *, code: int = 1) -> NoReturn:
    typer.secho(f"Error: {message}", fg=typer.colors.RED, err=False)
    raise typer.Exit(code)


def _fail_corrupt_config(exc: ConfigCorruptError) -> NoReturn:
    """Surface a corrupt config with recovery guidance instead of a traceback."""
    _fail(corrupt_config_recovery_message(exc.path, exc.reason), code=1)


def _api_request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
) -> Any:
    try:
        config = load_config()
    except ConfigCorruptError as exc:
        _fail_corrupt_config(exc)
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


def _resolve_collection_ref(collection_ref: str) -> str:
    try:
        return resolve_collection_ref(collection_ref, _api_request)
    except CollectionRefResolutionError as exc:
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
    except ConfigCorruptError as exc:
        _fail_corrupt_config(exc)
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


@target_app.callback(invoke_without_command=True)
def target(
    ctx: typer.Context,
    global_scope: Annotated[
        bool,
        typer.Option(
            "--global",
            help="Operate on the global target instead of the workspace target.",
        ),
    ] = False,
) -> None:
    """Show the current target selection (workspace by default, or global)."""
    if ctx.invoked_subcommand is not None:
        return
    _echo_target_show(global_scope=global_scope)


@target_app.command("set", help="Set the workspace or global target.")
def target_set(
    ctx: typer.Context,
    target_name: Annotated[
        str,
        typer.Argument(help="Target: claude or opencode."),
    ],
    global_scope: Annotated[
        bool,
        typer.Option(
            "--global",
            help="Set the global target instead of the workspace target.",
        ),
    ] = False,
) -> None:
    """Persist the workspace (.agh-cache/preferences.toml) or global target."""
    if target_name not in SUPPORTED_AGENT_TARGETS:
        _fail("target must be 'claude' or 'opencode'", code=2)
    label = AGENT_LABELS[target_name]
    effective_global_scope = _target_global_scope(ctx, global_scope=global_scope)
    if effective_global_scope:
        try:
            write_global_skill_default_agent(target_name)
        except AgentPreferenceError as exc:
            _fail(str(exc), code=exc.code)
        typer.echo(f"Set global target to {label} ({target_name}).")
        return
    try:
        preference = write_agent_preference(target_name)
    except AgentPreferenceError as exc:
        _fail(str(exc), code=exc.code)
    typer.echo(f"Set workspace target to {label} ({target_name}).")
    typer.echo(f"Preferences: {_format_cli_path(preference.path)}")


@target_app.command("clear", help="Clear the workspace or global target.")
def target_clear(
    ctx: typer.Context,
    global_scope: Annotated[
        bool,
        typer.Option(
            "--global",
            help="Clear the global target instead of the workspace target.",
        ),
    ] = False,
) -> None:
    """Remove the workspace or global target selection if present."""
    effective_global_scope = _target_global_scope(ctx, global_scope=global_scope)
    if effective_global_scope:
        try:
            removed = clear_global_skill_default_agent()
        except AgentPreferenceError as exc:
            _fail(str(exc), code=exc.code)
        if removed:
            typer.echo("Cleared global target.")
        else:
            typer.echo("No global target was set.")
        return
    try:
        removed = clear_agent_preference()
    except AgentPreferenceError as exc:
        _fail(str(exc), code=exc.code)
    if removed:
        typer.echo("Cleared workspace target.")
    else:
        typer.echo("No workspace target was set.")


def _target_global_scope(ctx: typer.Context, *, global_scope: bool) -> bool:
    """Return whether target commands should use the global target scope."""
    parent_params = ctx.parent.params if ctx.parent is not None else {}
    return global_scope or bool(parent_params.get("global_scope"))


def _echo_target_show(*, global_scope: bool) -> None:
    if global_scope:
        try:
            default = read_global_skill_default_agent()
        except AgentPreferenceError as exc:
            _fail(str(exc), code=exc.code)
        if default is None:
            typer.echo("Global target: not set")
        else:
            typer.echo(f"Global target: {AGENT_LABELS[default]} ({default}).")
        return
    try:
        preference = read_agent_preference()
    except AgentPreferenceError as exc:
        _fail(str(exc), code=exc.code)
    if preference is None:
        typer.echo("Workspace target: not set")
    else:
        typer.echo(f"Workspace target: {preference.label} ({preference.target}).")
    typer.echo(format_agent_availability(detect_agent_availability()))


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
    except ConfigCorruptError as exc:
        _fail_corrupt_config(exc)
    except WorkspaceSyncError as exc:
        _fail(str(exc), code=exc.code)

    _echo_sync_success(result)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option("--version", help="Show the AGH version."),
    ] = None,
) -> None:
    """Agent Guidance Hub CLI."""
    if version:
        typer.echo(f"agh {__version__}")
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        _show_local_help(ctx)


@app.command("login", help="Validate credentials for the configured AGH instance.")
def login(
    email: Annotated[
        str | None,
        typer.Option(
            "--email",
            help="Email expected from GET /api/v1/me. Prompted when omitted.",
        ),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option(
            "--token",
            hide_input=True,
            help="AGH API token. Validated against the configured instance.",
        ),
    ] = None,
) -> None:
    """Authenticate against the configured instance and store credentials.

    The instance URL comes from `agh config set`; login never prompts for it.
    Email and token are prompted interactively when the flags are omitted.
    """
    try:
        instance_url = load_instance_url()
    except ConfigCorruptError as exc:
        _fail_corrupt_config(exc)
    except ConfigError as exc:
        _fail(str(exc))

    email_value: str = email if email is not None else typer.prompt("Email")
    token_value: str = (
        token if token is not None else typer.prompt("Token", hide_input=True)
    )

    try:
        validate_login(instance_url=instance_url, email=email_value, token=token_value)
        save_credentials(email=email_value, token=token_value)
    except (ConfigError, LoginValidationError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=False)
        raise typer.Exit(1) from exc

    typer.echo(
        f"Logged in to {instance_url} as {email_value}. "
        f"Credentials saved to {get_config_path()}."
    )


@app.command("whoami", help="Show the authenticated user.")
def whoami() -> None:
    """Show the user identified by GET /api/v1/me for the stored credentials."""
    _echo_user_detail(_api_request("GET", "/me"))


@app.command("logout", help="Clear stored credentials.")
def logout() -> None:
    """Remove stored credentials, keeping the configured instance URL."""
    try:
        cleared = clear_credentials()
    except ConfigCorruptError as exc:
        _fail_corrupt_config(exc)
    if cleared:
        typer.echo("Logged out (cleared credentials).")
    else:
        typer.echo("No credentials were saved.")


@config_app.callback(invoke_without_command=True)
def config_main(ctx: typer.Context) -> None:
    """Show the configured AGH instance, or manage it with set/clear."""
    if ctx.invoked_subcommand is not None:
        return
    try:
        instance_url = load_instance_url()
    except ConfigCorruptError as exc:
        _fail_corrupt_config(exc)
    except ConfigError:
        typer.echo("Instance URL: not set")
        raise typer.Exit(0)
    typer.echo(f"Instance URL: {instance_url}")


@config_app.command("set", help="Configure the AGH instance URL.")
def config_set(
    instance_url: Annotated[
        str,
        typer.Argument(help="AGH instance URL, e.g. http://localhost:8912."),
    ],
) -> None:
    """Configure the instance URL, clearing credentials when the instance changes."""
    try:
        result = save_instance_url(instance_url)
    except ConfigCorruptError as exc:
        _fail_corrupt_config(exc)
    except ConfigError as exc:
        _fail(str(exc), code=2)
    typer.echo(f"Set instance URL: {result.instance_url}")
    if result.credentials_cleared:
        typer.echo(
            "Instance changed: cleared stored credentials. "
            "Run: agh login to authenticate against the new instance."
        )


@config_app.command("clear", help="Clear the configured AGH instance URL.")
def config_clear() -> None:
    """Remove only the instance URL, preserving any stored credentials."""
    try:
        cleared = clear_instance_url()
    except ConfigCorruptError as exc:
        _fail_corrupt_config(exc)
    if cleared:
        typer.echo("Cleared instance URL.")
    else:
        typer.echo("No instance URL was set.")


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


def _echo_user_updated(user: dict[str, Any], *, verb: str = "Updated") -> None:
    typer.echo(f"{verb} user {user.get('email', '')} ({user.get('id', '')}).")
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


def _echo_package_detail(package: dict[str, Any]) -> None:
    typer.echo(f"Package: {_package_ref(package)}")
    if package.get("package_id"):
        typer.echo(f"Package ID: {package.get('package_id')}")
    if package.get("description"):
        typer.echo(f"Description: {package.get('description')}")
    if package.get("checksum"):
        typer.echo(f"Checksum: {package.get('checksum')}")


def _assignment_payload_key(scope: str) -> str:
    return "project_packages" if scope == "project" else "collection_packages"


def _echo_package_assignments(scope: str, payload: dict[str, Any]) -> None:
    assignments = payload.get(_assignment_payload_key(scope), [])
    if not assignments:
        typer.echo("No assigned packages found.")
        return
    _echo_table(
        ["PACKAGE_REF", "RESOLVED", "STATUS"],
        [
            [
                str(assignment.get("package_ref", "")),
                str(
                    assignment.get("resolved_ref") or assignment.get("package_ref", "")
                ),
                _status_label(assignment),
            ]
            for assignment in assignments
        ],
    )


def _echo_package_assigned(
    payload: dict[str, Any], *, scope: str, scope_id: str
) -> None:
    package_ref = str(payload.get("package_ref", ""))
    typer.echo(f"Assigned {package_ref} to {scope} {scope_id}.")
    typer.echo(f"Resolved: {payload.get('resolved_ref') or package_ref}")


def _echo_package_status(
    payload: dict[str, Any], *, scope: str, scope_id: str, verb: str
) -> None:
    package_ref = str(payload.get("package_ref", ""))
    typer.echo(f"{verb} {package_ref} on {scope} {scope_id}.")
    typer.echo(f"Resolved: {payload.get('resolved_ref') or package_ref}")


def _echo_package_removed(*, scope: str, scope_id: str, package_ref: str) -> None:
    typer.echo(f"Removed {package_ref} from {scope} {scope_id}.")


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


def _echo_collection_list(payload: dict[str, Any]) -> None:
    collections = payload.get("collections", [])
    if not collections:
        typer.echo("No collections found.")
        return
    _echo_table(
        ["COLLECTION_ID", "NAME", "DESCRIPTION", "STATUS"],
        [
            [
                str(collection.get("id", "")),
                str(collection.get("name", "")),
                str(collection.get("description", "")),
                _status_label(collection),
            ]
            for collection in collections
        ],
    )


def _echo_collection_detail(collection: dict[str, Any]) -> None:
    typer.echo(f"Collection: {collection.get('name', '')}")
    typer.echo(f"Collection ID: {collection.get('id', '')}")
    typer.echo(f"Description: {collection.get('description', '')}")
    typer.echo(f"Status: {_status_label(collection)}")


def _echo_collection_success(verb: str, collection: dict[str, Any]) -> None:
    typer.echo(
        f"{verb} collection {collection.get('name', '')} ({collection.get('id', '')})."
    )
    typer.echo(f"Status: {_status_label(collection)}")


def _echo_collection_deactivated(collection: dict[str, Any]) -> None:
    typer.echo(
        f"Deactivated collection {collection.get('name', '')} ({collection.get('id', '')})."
    )


def _echo_project_member_success(
    verb: str, payload: dict[str, Any], *, project_id: str, user_id: str
) -> None:
    returned_project_id = str(payload.get("project_id") or project_id)
    returned_user_id = str(payload.get("user_id") or user_id)
    typer.echo(
        f"{verb} user {returned_user_id} {'to' if verb == 'Added' else 'from'} project {returned_project_id}."
    )


def _echo_project_member_list(payload: dict[str, Any]) -> None:
    members = payload.get("members", [])
    if not members:
        typer.echo("No project members found.")
        return
    _echo_table(
        ["USER_ID", "EMAIL", "STATUS"],
        [
            [
                str(member.get("id", "")),
                str(member.get("email", "")),
                _status_label(member),
            ]
            for member in members
        ],
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


@user_app.callback(invoke_without_command=True)
def user_main(ctx: typer.Context) -> None:
    """User administration commands."""
    if ctx.invoked_subcommand is None:
        _show_local_help(ctx)


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


@user_app.command("describe", help="Describe one user by USER_REF.")
def user_describe(
    user_ref: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_user_id = _resolve_user_ref(user_ref)
    _echo_user_detail(_api_request("GET", user_path(resolved_user_id)))


@user_app.command("update", help="Update user email, role, or active flag.")
def user_update(
    user_ref: Annotated[str, typer.Argument(help=USER_REF_HELP)],
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
    resolved_user_id = _resolve_user_ref(user_ref)
    _echo_user_updated(
        _api_request(
            "PATCH",
            user_path(resolved_user_id),
            body=_body_without_none(email=email, role=role, active=active),
        )
    )


@user_app.command("activate", help="Activate a user by USER_REF.")
def user_activate(
    user_ref: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_user_id = _resolve_user_ref(user_ref)
    _echo_user_updated(
        _api_request("PATCH", user_path(resolved_user_id), body={"active": True}),
        verb="Activated",
    )


@user_app.command("deactivate", help="Deactivate a user by USER_REF.")
def user_deactivate(
    user_ref: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_user_id = _resolve_user_ref(user_ref)
    _echo_user_deactivated(_api_request("DELETE", user_path(resolved_user_id)))


def user_path(user_id: str) -> str:
    return f"/users/{user_id}"


@user_token_app.callback(invoke_without_command=True)
def token_main(ctx: typer.Context) -> None:
    """Token lifecycle commands."""
    if ctx.invoked_subcommand is None:
        _show_local_help(ctx)


@user_token_app.command(
    "rotate", help="Rotate a user's token and print the new token once."
)
def token_rotate(
    user_ref: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_user_id = _resolve_user_ref(user_ref)
    _echo_token_issued(
        "Rotated",
        _api_request("POST", f"/users/{resolved_user_id}/token:rotate"),
        user_id=resolved_user_id,
    )


@project_app.callback(invoke_without_command=True)
def project_main(ctx: typer.Context) -> None:
    """Project administration commands."""
    if ctx.invoked_subcommand is None:
        _show_local_help(ctx)


@project_app.command("list", help="List projects visible to the authenticated user.")
def project_list() -> None:
    _echo_project_list(_api_request("GET", "/projects"))


@project_app.command("create", help="Create a project.")
def project_create(
    name: Annotated[str, typer.Argument(help="Project display name.")],
    repo_url: Annotated[
        str,
        typer.Option("--git-url", help="Git repository URL linked to the project."),
    ],
) -> None:
    cleaned_name = _clean_project_name_or_exit(name)
    _echo_project_success(
        "Created",
        _api_request(
            "POST", "/projects", body={"name": cleaned_name, "repo_url": repo_url}
        ),
    )


@project_app.command("describe", help="Describe one project by PROJECT_REF.")
def project_describe(
    project_ref: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
) -> None:
    resolved_project_id = _resolve_project_ref(project_ref)
    _echo_project_detail(_api_request("GET", project_path(resolved_project_id)))


@project_app.command(
    "update", help="Update project name, repo URL, or active flag by id or exact name."
)
def project_update(
    project_ref: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
    name: Annotated[
        str | None, typer.Option("--name", help="New project name.")
    ] = None,
    repo_url: Annotated[
        str | None,
        typer.Option("--git-url", help="New linked Git repository URL."),
    ] = None,
    active: Annotated[
        bool | None,
        typer.Option("--active/--inactive", help="Set whether the project is active."),
    ] = None,
) -> None:
    cleaned_name = _clean_project_name_or_exit(name) if name is not None else None
    resolved_project_id = _resolve_project_ref(project_ref)
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


@project_app.command("activate", help="Activate a project by PROJECT_REF.")
def project_activate(
    project_ref: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
) -> None:
    resolved_project_id = _resolve_project_ref(project_ref)
    _echo_project_success(
        "Activated",
        _api_request("PATCH", project_path(resolved_project_id), body={"active": True}),
    )


@project_app.command("deactivate", help="Deactivate a project by PROJECT_REF.")
def project_deactivate(
    project_ref: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
) -> None:
    resolved_project_id = _resolve_project_ref(project_ref)
    _echo_project_deactivated(_api_request("DELETE", project_path(resolved_project_id)))


def project_path(project_id: str) -> str:
    return f"/projects/{project_id}"


@collection_app.callback(invoke_without_command=True)
def collection_main(ctx: typer.Context) -> None:
    """Collection administration commands."""
    if ctx.invoked_subcommand is None:
        _show_local_help(ctx)


@collection_app.command(
    "list", help="List collections visible to the authenticated user."
)
def collection_list() -> None:
    _echo_collection_list(_api_request("GET", "/collections"))


@collection_app.command("create", help="Create a collection.")
def collection_create(
    name: Annotated[str, typer.Argument(help="Collection display name.")],
    description: Annotated[
        str | None,
        typer.Option("--description", help="Optional collection description."),
    ] = None,
) -> None:
    _echo_collection_success(
        "Created",
        _api_request(
            "POST",
            "/collections",
            body=_body_without_none(name=name, description=description),
        ),
    )


@collection_app.command("describe", help="Describe one collection by COLLECTION_REF.")
def collection_describe(
    collection_ref: Annotated[str, typer.Argument(help=COLLECTION_REF_HELP)],
) -> None:
    resolved_collection_id = _resolve_collection_ref(collection_ref)
    _echo_collection_detail(
        _api_request("GET", collection_path(resolved_collection_id))
    )


@collection_app.command(
    "update", help="Update collection name, description, or active flag by id or name."
)
def collection_update(
    collection_ref: Annotated[str, typer.Argument(help=COLLECTION_REF_HELP)],
    name: Annotated[
        str | None, typer.Option("--name", help="New collection name.")
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New collection description."),
    ] = None,
    active: Annotated[
        bool | None,
        typer.Option(
            "--active/--inactive", help="Set whether the collection is active."
        ),
    ] = None,
) -> None:
    resolved_collection_id = _resolve_collection_ref(collection_ref)
    _echo_collection_success(
        "Updated",
        _api_request(
            "PATCH",
            collection_path(resolved_collection_id),
            body=_body_without_none(
                name=name,
                description=description,
                active=active,
            ),
        ),
    )


@collection_app.command("activate", help="Activate a collection by COLLECTION_REF.")
def collection_activate(
    collection_ref: Annotated[str, typer.Argument(help=COLLECTION_REF_HELP)],
) -> None:
    resolved_collection_id = _resolve_collection_ref(collection_ref)
    _echo_collection_success(
        "Activated",
        _api_request(
            "PATCH", collection_path(resolved_collection_id), body={"active": True}
        ),
    )


@collection_app.command("deactivate", help="Deactivate a collection by COLLECTION_REF.")
def collection_deactivate(
    collection_ref: Annotated[str, typer.Argument(help=COLLECTION_REF_HELP)],
) -> None:
    resolved_collection_id = _resolve_collection_ref(collection_ref)
    _echo_collection_deactivated(
        _api_request("DELETE", collection_path(resolved_collection_id))
    )


def collection_path(collection_id: str) -> str:
    return f"/collections/{collection_id}"


@package_app.callback(invoke_without_command=True)
def package_main(ctx: typer.Context) -> None:
    """Package init/publish/list/describe and assignment commands."""
    if ctx.invoked_subcommand is None:
        _show_local_help(ctx)


PACKAGE_ASSIGN_TARGET_REQUIRED_MESSAGE = (
    "package assignment requires exactly one of --project or --collection"
)


def _fail_package_assign_target_required() -> None:
    _fail(PACKAGE_ASSIGN_TARGET_REQUIRED_MESSAGE, code=USAGE_ERROR_EXIT_CODE)


def _resolve_package_assignment_target(
    *, project: str | None, collection: str | None
) -> tuple[str, str]:
    """Resolve the mutually exclusive assignment target to ``(scope, scope_id)``.

    ``scope`` is ``"project"`` or ``"collection"``. Exits with usage guidance when
    both or neither target flag is supplied.
    """
    if project is not None and collection is not None:
        _fail_package_assign_target_required()
    if project is None and collection is None:
        _fail_package_assign_target_required()
    if project is not None:
        return "project", _resolve_project_ref(project)
    assert collection is not None
    return "collection", _resolve_collection_ref(collection)


def _package_identity(package_ref: str) -> tuple[str, str]:
    """Return the ``(domain, name)`` identity for a canonical package ref."""
    parsed = parse_package_ref(package_ref, allow_latest=True)
    return parsed.domain, parsed.name


def _find_package_assignment_id(*, scope: str, scope_id: str, package_ref: str) -> str:
    """Look up the assignment id for a package within a project/collection target.

    Matches by package identity (domain + name); the server enforces a single
    assignment per package per target. Exits naming the package ref and target
    when no assignment exists, so users know what to list.
    """
    domain, name = _package_identity(package_ref)
    payload = _api_request("GET", f"/{scope}s/{scope_id}/packages")
    assignments = payload.get(_assignment_payload_key(scope), [])
    for assignment in assignments:
        if (
            str(assignment.get("domain")) == domain
            and str(assignment.get("name")) == name
        ):
            assignment_id = str(assignment.get("id", ""))
            if assignment_id:
                return assignment_id
    _fail(
        f"package {package_ref} is not assigned to {scope} {scope_id}; "
        f"run `agh package list --{scope} {scope_id}` to review assignments"
    )


def _semver_sort_key(version: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in version.split("."))  # type: ignore[return-value]


def _find_describe_package(package_ref: str) -> dict[str, Any]:
    """Resolve PACKAGE_REF to the published package record for describe.

    Fetches ``/packages`` once. ``@latest`` resolves to the highest published
    SemVer version (SemVer-aware, not string sort: ``1.10.0`` beats ``1.2.0``);
    ``pkgv_`` ids and ``name@version`` refs resolve through the package version
    resolver to their canonical ``domain/name@version`` first.
    """
    resolved = _resolve_package_version_ref(package_ref)
    parsed = parse_package_ref(resolved, allow_latest=True)
    payload = _api_request("GET", "/packages")
    packages = payload.get("packages", []) if isinstance(payload, dict) else []
    if parsed.version == "latest":
        candidates = [
            package
            for package in packages
            if str(package.get("domain")) == parsed.domain
            and str(package.get("name")) == parsed.name
        ]
        if not candidates:
            _fail(f"package {resolved} not found")
        return max(
            candidates,
            key=lambda package: _semver_sort_key(str(package.get("version"))),
        )
    for package in packages:
        if _package_ref(package) == resolved:
            return package
    _fail(f"package {resolved} not found")


@package_app.command("list", help="List packages or scoped assignments.")
def package_list(
    project: Annotated[
        str | None,
        typer.Option("--project", help=PROJECT_REF_HELP),
    ] = None,
    collection: Annotated[
        str | None,
        typer.Option("--collection", help=COLLECTION_REF_HELP),
    ] = None,
) -> None:
    if project is not None and collection is not None:
        _fail_package_assign_target_required()
    if project is not None:
        scope_id = _resolve_project_ref(project)
        _echo_package_assignments(
            "project",
            _api_request("GET", f"/projects/{scope_id}/packages"),
        )
        return
    if collection is not None:
        scope_id = _resolve_collection_ref(collection)
        _echo_package_assignments(
            "collection",
            _api_request("GET", f"/collections/{scope_id}/packages"),
        )
        return
    _echo_package_list(_api_request("GET", "/packages"))


@package_app.command("describe", help="Describe a package version by PACKAGE_REF.")
def package_describe(
    package_ref: Annotated[str, typer.Argument(help=PACKAGE_VERSION_REF_HELP)],
) -> None:
    _echo_package_detail(_find_describe_package(package_ref))


@package_app.command("assign", help="Assign a package to a project or collection.")
def package_assign(
    package_ref: Annotated[str, typer.Argument(help=PACKAGE_VERSION_REF_HELP)],
    project: Annotated[
        str | None,
        typer.Option("--project", help=PROJECT_REF_HELP),
    ] = None,
    collection: Annotated[
        str | None,
        typer.Option("--collection", help=COLLECTION_REF_HELP),
    ] = None,
) -> None:
    scope, scope_id = _resolve_package_assignment_target(
        project=project, collection=collection
    )
    resolved_package_ref = _resolve_package_version_ref(package_ref)
    _echo_package_assigned(
        _api_request(
            "POST",
            f"/{scope}s/{scope_id}/packages",
            body={"package_ref": resolved_package_ref},
        ),
        scope=scope,
        scope_id=scope_id,
    )


@package_app.command(
    "activate", help="Activate a package assignment on a project or collection."
)
def package_activate(
    package_ref: Annotated[str, typer.Argument(help=PACKAGE_VERSION_REF_HELP)],
    project: Annotated[
        str | None,
        typer.Option("--project", help=PROJECT_REF_HELP),
    ] = None,
    collection: Annotated[
        str | None,
        typer.Option("--collection", help=COLLECTION_REF_HELP),
    ] = None,
) -> None:
    scope, scope_id = _resolve_package_assignment_target(
        project=project, collection=collection
    )
    resolved_package_ref = _resolve_package_version_ref(package_ref)
    assignment_id = _find_package_assignment_id(
        scope=scope, scope_id=scope_id, package_ref=resolved_package_ref
    )
    _echo_package_status(
        _api_request(
            "PATCH",
            f"/{scope}s/{scope_id}/packages/{assignment_id}",
            body={"active": True},
        ),
        scope=scope,
        scope_id=scope_id,
        verb="Activated",
    )


@package_app.command(
    "deactivate", help="Deactivate a package assignment on a project or collection."
)
def package_deactivate(
    package_ref: Annotated[str, typer.Argument(help=PACKAGE_VERSION_REF_HELP)],
    project: Annotated[
        str | None,
        typer.Option("--project", help=PROJECT_REF_HELP),
    ] = None,
    collection: Annotated[
        str | None,
        typer.Option("--collection", help=COLLECTION_REF_HELP),
    ] = None,
) -> None:
    scope, scope_id = _resolve_package_assignment_target(
        project=project, collection=collection
    )
    resolved_package_ref = _resolve_package_version_ref(package_ref)
    assignment_id = _find_package_assignment_id(
        scope=scope, scope_id=scope_id, package_ref=resolved_package_ref
    )
    _echo_package_status(
        _api_request(
            "PATCH",
            f"/{scope}s/{scope_id}/packages/{assignment_id}",
            body={"active": False},
        ),
        scope=scope,
        scope_id=scope_id,
        verb="Deactivated",
    )


@package_app.command(
    "unassign", help="Remove a package assignment from a project or collection."
)
def package_unassign(
    package_ref: Annotated[str, typer.Argument(help=PACKAGE_VERSION_REF_HELP)],
    project: Annotated[
        str | None,
        typer.Option("--project", help=PROJECT_REF_HELP),
    ] = None,
    collection: Annotated[
        str | None,
        typer.Option("--collection", help=COLLECTION_REF_HELP),
    ] = None,
) -> None:
    scope, scope_id = _resolve_package_assignment_target(
        project=project, collection=collection
    )
    resolved_package_ref = _resolve_package_version_ref(package_ref)
    assignment_id = _find_package_assignment_id(
        scope=scope, scope_id=scope_id, package_ref=resolved_package_ref
    )
    _api_request("DELETE", f"/{scope}s/{scope_id}/packages/{assignment_id}")
    _echo_package_removed(
        scope=scope, scope_id=scope_id, package_ref=resolved_package_ref
    )


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
        _show_local_help(ctx)


@project_member_app.command("add", help="Add an active user as a project developer.")
def project_member_add(
    project_ref: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
    user_ref: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_project_id = _resolve_project_ref(project_ref)
    resolved_user_id = _resolve_user_ref(user_ref)
    _echo_project_member_success(
        "Added",
        _api_request(
            "PUT", f"/projects/{resolved_project_id}/members/{resolved_user_id}"
        ),
        project_id=resolved_project_id,
        user_id=resolved_user_id,
    )


@project_member_app.command("list", help="List project developer memberships.")
def project_member_list(
    project_ref: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
) -> None:
    resolved_project_id = _resolve_project_ref(project_ref)
    _echo_project_member_list(
        _api_request("GET", f"/projects/{resolved_project_id}/members")
    )


@project_member_app.command("remove", help="Remove a project developer membership.")
def project_member_remove(
    project_ref: Annotated[str, typer.Argument(help=PROJECT_REF_HELP)],
    user_ref: Annotated[str, typer.Argument(help=USER_REF_HELP)],
) -> None:
    resolved_project_id = _resolve_project_ref(project_ref)
    resolved_user_id = _resolve_user_ref(user_ref)
    _echo_project_member_success(
        "Removed",
        _api_request(
            "DELETE", f"/projects/{resolved_project_id}/members/{resolved_user_id}"
        ),
        project_id=resolved_project_id,
        user_id=resolved_user_id,
    )


_use_agh_command_help_text(app)


if __name__ == "__main__":
    app()
