import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install.sh"


def _write_fake_bin(bin_dir: Path) -> Path:
    log = bin_dir / "uv.log"
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/bin/sh\n"
        'echo "$@" >> "$UV_LOG"\n'
        'if [ "$1 $2" = "tool dir" ]; then echo /tmp/uv-tools; fi\n',
        encoding="utf-8",
    )
    uv.chmod(0o755)

    agh = bin_dir / "agh"
    agh.write_text(
        '#!/bin/sh\nif [ "$1" = "--help" ]; then echo agh help; exit 0; fi\nexit 1\n',
        encoding="utf-8",
    )
    agh.chmod(0o755)
    return log


def _run_installer(
    *, bin_dir: Path, log: Path, package: str | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["UV_LOG"] = str(log)
    if package is not None:
        env["AGH_INSTALL_PACKAGE"] = package
    return subprocess.run(
        ["sh", str(SCRIPT)],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def _run_installer_from_stdin(
    *, bin_dir: Path, log: Path, cwd: Path
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["UV_LOG"] = str(log)
    return subprocess.run(
        ["sh"],
        cwd=cwd,
        input=SCRIPT.read_text(encoding="utf-8"),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def test_install_script_installs_agh_package(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _write_fake_bin(bin_dir)

    result = _run_installer(bin_dir=bin_dir, log=log)

    assert "Installing agh CLI package: agh" in result.stdout
    assert "tool install --force agh" in log.read_text(encoding="utf-8")


def test_install_script_installs_package_when_piped_to_sh_near_checkout(
    tmp_path: Path,
) -> None:
    parent = tmp_path / "parent"
    cwd = parent / "work"
    cwd.mkdir(parents=True)
    (parent / "pyproject.toml").write_text(
        "[project]\nname = 'not-agh'\n", encoding="utf-8"
    )
    (parent / "agh").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _write_fake_bin(bin_dir)

    result = _run_installer_from_stdin(bin_dir=bin_dir, log=log, cwd=cwd)

    assert "Installing agh CLI package: agh" in result.stdout
    log_text = log.read_text(encoding="utf-8")
    assert "tool install --force agh" in log_text
    assert str(parent) not in log_text


def test_install_script_allows_package_override(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _write_fake_bin(bin_dir)
    package = "agh-test-package"

    result = _run_installer(bin_dir=bin_dir, log=log, package=package)

    assert f"Installing agh CLI package: {package}" in result.stdout
    assert f"tool install --force {package}" in log.read_text(encoding="utf-8")
