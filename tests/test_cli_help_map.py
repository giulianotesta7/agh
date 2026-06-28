"""PR1: Root help map, command-local help, and unknown-command behavior.

Pins the ``cli-command-ux`` "Discoverable root and help output" requirement for
the help/root infrastructure slice:

* root help shows the full command tree and advertises ``--version``
* subgroups show LOCAL help (never the root map) when invoked without a
  subcommand, with ``--help``, or with an unknown subcommand
* unknown commands exit 2

Later slices extend the tree (target/link/whoami/logout) and remove legacy
names; this slice only fixes help rendering and the root command map.
"""

from __future__ import annotations

from typer.testing import CliRunner

from agh.cli.main import app as cli_app

# PR2b root command map. The auth slice adds `whoami` and `logout` and
# rewrites `login` to use the configured instance (no `--url`). `agent` is
# still present (renamed to `target` in PR2c). Legacy names still awaiting their
# own slices (sync, token, show/get/delete verbs, nested project/collection
# package) are retained until those slices land. This pins what PR2b advertises.
PR2B_TOP_LEVEL_COMMANDS = [
    "config",
    "login",
    "whoami",
    "logout",
    "user",
    "token",
    "project",
    "collection",
    "package",
    "agent",
    "skill",
    "sync",
    "pull",
]
PR2B_NESTED_COMMANDS = [
    "config set",
    "config clear",
    "project member",
    "project package",
    "collection package",
    "skill agent",
]
# Names promised by the final redesign that are NOT backed by any PR2b command
# yet, and therefore MUST NOT be advertised from root help.
NOT_YET_IMPLEMENTED_COMMANDS = ["target", "link"]


def _root_help(runner: CliRunner) -> str:
    return runner.invoke(cli_app, ["--help"]).stdout


def _root_command_rows(help_output: str) -> tuple[list[str], list[str]]:
    """Parse the maintained root command map into ``(top_level, nested)`` rows.

    The maintained ``APP_HELP`` block is the only part of root help indented as
    a command map: top-level rows use two leading spaces and nested rows use
    four. Parsing these rows pins the *intended* advertised tree instead of
    matching loose tokens (e.g. ``member`` or ``link``) that may appear inside
    unrelated description prose.
    """
    top_level: list[str] = []
    nested: list[str] = []
    in_commands = False
    for line in help_output.splitlines():
        stripped = line.strip()
        if stripped == "Commands:":
            in_commands = True
            continue
        if not in_commands or not stripped:
            continue
        # Leave the command map once a non-indented section (Global options:)
        # begins.
        if not line.startswith("  "):
            break
        tokens = stripped.split()
        if line.startswith("    ") and len(tokens) >= 2:
            nested.append(f"{tokens[0]} {tokens[1]}")
        elif line.startswith("  "):
            top_level.append(tokens[0])
    return top_level, nested


def test_root_help_lists_command_tree_and_version_flag() -> None:
    runner = CliRunner()
    help_output = _root_help(runner)

    assert "Agent Guidance Hub" in help_output
    assert "--version" in help_output
    for command in [
        "login",
        "config",
        "whoami",
        "logout",
        "user",
        "project",
        "collection",
        "package",
        "agent",
        "skill",
        "pull",
    ]:
        assert command in help_output, command
    # nested subcommands are advertised as exact root-map rows, not as loose
    # tokens such as "member" that could match unrelated prose.
    _, nested_rows = _root_command_rows(help_output)
    assert "project member" in nested_rows
    assert "skill agent" in nested_rows


def test_root_no_args_matches_root_help() -> None:
    runner = CliRunner()
    no_args = runner.invoke(cli_app, [])
    help_output = _root_help(runner)

    assert no_args.exit_code == 0
    assert no_args.stdout == help_output


def test_subgroup_no_args_shows_local_help_not_root_map() -> None:
    runner = CliRunner()
    root_help = _root_help(runner)

    cases = (
        (runner.invoke(cli_app, ["user"]), "Manage AGH users."),
        (
            runner.invoke(cli_app, ["package"]),
            "Create, publish, and list guidance packages.",
        ),
    )

    for result, local_marker in cases:
        assert result.exit_code == 0, (local_marker, result.stdout)
        assert local_marker in result.stdout, (local_marker, result.stdout)
        assert result.stdout != root_help, local_marker


def test_config_help_flag_shows_local_help_not_root_map() -> None:
    """config used to leak the root map on --help; it must show local config help."""
    runner = CliRunner()
    root_help = _root_help(runner)
    config_help = runner.invoke(cli_app, ["config", "--help"])

    assert config_help.exit_code == 0, config_help.stdout
    assert "local AGH CLI configuration" in config_help.stdout
    assert config_help.stdout != root_help


def test_help_options_avoid_redundant_exit_wording() -> None:
    runner = CliRunner()

    config_help = runner.invoke(cli_app, ["config", "--help"])
    login_help = runner.invoke(cli_app, ["login", "--help"])

    assert config_help.exit_code == 0, config_help.stdout
    assert login_help.exit_code == 0, login_help.stdout
    assert "and exit" not in config_help.stdout
    assert "and exit" not in login_help.stdout
    assert "--help  Show this help page." in config_help.stdout
    assert "--help" in login_help.stdout
    assert "Show this help page." in login_help.stdout


def test_subgroup_help_flag_shows_local_help_not_root_map() -> None:
    runner = CliRunner()
    root_help = _root_help(runner)

    project_help = runner.invoke(cli_app, ["project", "--help"])
    collection_help = runner.invoke(cli_app, ["collection", "--help"])

    assert project_help.exit_code == 0, project_help.stdout
    assert "Manage AGH projects." in project_help.stdout
    assert "member" in project_help.stdout
    assert project_help.stdout != root_help

    assert collection_help.exit_code == 0, collection_help.stdout
    assert "Manage AGH collections." in collection_help.stdout
    assert collection_help.stdout != root_help


def test_package_help_describes_package_only_commands() -> None:
    """Spec scenario: command help is local and specific (agh package --help)."""
    runner = CliRunner()
    root_help = _root_help(runner)
    package_help = runner.invoke(cli_app, ["package", "--help"])

    assert package_help.exit_code == 0, package_help.stdout
    assert "Create, publish, and list guidance packages." in package_help.stdout
    assert package_help.stdout != root_help


def test_root_unknown_command_exits_2_with_root_help() -> None:
    runner = CliRunner()
    root_help = _root_help(runner)
    result = runner.invoke(cli_app, ["frobnicate"])

    assert result.exit_code == 2
    assert result.stdout == root_help


def test_subgroup_unknown_command_exits_2_with_local_help() -> None:
    runner = CliRunner()
    root_help = _root_help(runner)

    user_unknown = runner.invoke(cli_app, ["user", "frobnicate"])
    assert user_unknown.exit_code == 2
    assert "Manage AGH users." in user_unknown.stdout
    assert user_unknown.stdout != root_help

    member_unknown = runner.invoke(cli_app, ["project", "member", "frobnicate"])
    assert member_unknown.exit_code == 2
    assert "developer membership" in member_unknown.stdout.lower()
    assert member_unknown.stdout != root_help


def test_root_map_pins_intended_current_command_rows() -> None:
    """Strongest practical PR1 pin of the maintained root command map.

    Asserts the exact advertised rows by parsing the command map rather than
    matching loose tokens, so renaming a command or accidentally advertising a
    future name fails loudly. A full dynamic parity / golden snapshot test is
    tracked as a follow-up in apply-progress.md.
    """
    runner = CliRunner()
    top_level, nested = _root_command_rows(_root_help(runner))

    assert top_level == PR2B_TOP_LEVEL_COMMANDS
    assert nested == PR2B_NESTED_COMMANDS


def test_root_help_does_not_advertise_not_yet_implemented_commands() -> None:
    """PR1 must not advertise future names that no command backs yet.

    These names are checked against parsed command rows only, so description
    prose (e.g. ``sync`` describing itself as "Link this git repository...")
    cannot produce a false positive for ``link``.
    """
    runner = CliRunner()
    top_level, nested = _root_command_rows(_root_help(runner))
    advertised = set(top_level) | set(nested)

    for name in NOT_YET_IMPLEMENTED_COMMANDS:
        assert name not in advertised, name


def test_nested_leaf_help_uses_concise_wording() -> None:
    """Nested leaf ``--help`` must use AGH's concise wording.

    Covers deeper nested leaves than the top-level config/login checks: the
    help option must read "Show this help page." and must never append the
    Typer default "and exit".
    """
    runner = CliRunner()
    cases = (
        ["config", "set", "--help"],
        ["project", "member", "add", "--help"],
    )
    for argv in cases:
        result = runner.invoke(cli_app, argv)
        assert result.exit_code == 0, (argv, result.stdout)
        assert "and exit" not in result.stdout, argv
        assert "--help  Show this help page." in result.stdout, argv
