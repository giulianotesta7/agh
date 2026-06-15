"""Docker-backed runtime hardening checks for the AGH image."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn

import pytest


IMAGE = "agh-runtime-pytest:local"
RUNTIME_USER = "10001:10001"
STRICT_DOCKER_RUNTIME_ENV = "AGH_STRICT_DOCKER_RUNTIME"
DOCKER_UNAVAILABLE_MESSAGE = (
    "Docker daemon is not available for runtime hardening tests"
)


def test_strict_docker_runtime_mode_fails_when_docker_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(STRICT_DOCKER_RUNTIME_ENV, "1")

    with pytest.raises(pytest.fail.Exception, match="Docker daemon is not available"):
        _require_docker_runtime_available(docker_available=False)


def test_local_docker_runtime_mode_skips_when_docker_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(STRICT_DOCKER_RUNTIME_ENV, raising=False)

    with pytest.raises(pytest.skip.Exception, match="Docker daemon is not available"):
        _require_docker_runtime_available(docker_available=False)


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _docker_available() -> bool:
    return _run("docker", "info", check=False).returncode == 0


def _strict_docker_runtime_enabled() -> bool:
    value = os.getenv(STRICT_DOCKER_RUNTIME_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _skip_or_fail(message: str) -> NoReturn:
    if _strict_docker_runtime_enabled():
        pytest.fail(message)
    pytest.skip(message)


def _require_docker_runtime_available(docker_available: bool | None = None) -> None:
    if docker_available is None:
        docker_available = _docker_available()
    if docker_available:
        return
    _skip_or_fail(DOCKER_UNAVAILABLE_MESSAGE)


@pytest.fixture(scope="session")
def docker_image() -> str:
    _require_docker_runtime_available()
    _run("docker", "build", "--build-arg", "AGH_VERSION=0.0.0", "-t", IMAGE, ".")
    return IMAGE


def docker_image_contract(docker_image: str) -> dict[str, str]:
    format_expr = "{{.Config.User}}\n{{json .Config.Entrypoint}}\n{{json .Config.Cmd}}"
    user, entrypoint, cmd = _run(
        "docker", "image", "inspect", "--format", format_expr, docker_image
    ).stdout.splitlines()
    return {"user": user, "entrypoint": entrypoint, "cmd": cmd}


@pytest.fixture
def docker_volume() -> Iterator[str]:
    name = f"agh-runtime-pytest-{time.time_ns()}"
    _run("docker", "volume", "create", name)
    try:
        yield name
    finally:
        _run("docker", "volume", "rm", "-f", name, check=False)


@pytest.fixture
def running_container(docker_image: str, docker_volume: str) -> Iterator[str]:
    container = _run(
        "docker",
        "run",
        "-d",
        "-e",
        "AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com",
        "-v",
        f"{docker_volume}:/data",
        docker_image,
    ).stdout.strip()
    try:
        _wait_for_health(container)
        yield container
    finally:
        _run("docker", "rm", "-f", container, check=False)


def _wait_for_health(container: str) -> None:
    command = (
        "import urllib.request; "
        "urllib.request.urlopen('http://127.0.0.1:8912/api/v1/health')"
    )
    for _ in range(30):
        result = _run("docker", "exec", container, "python", "-c", command, check=False)
        if result.returncode == 0:
            return
        time.sleep(1)

    diagnostics = _run("docker", "logs", container, check=False).stderr
    pytest.fail(f"Health endpoint did not become ready. Logs:\n{diagnostics}")


def _proc_status(container: str) -> dict[str, list[str]]:
    status = _run("docker", "exec", container, "cat", "/proc/1/status").stdout
    fields: dict[str, list[str]] = {}
    for line in status.splitlines():
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        fields[name] = value.split()
    return fields


def test_image_uses_direct_non_root_uvicorn_command(docker_image: str) -> None:
    contract = docker_image_contract(docker_image)

    assert contract == {
        "user": RUNTIME_USER,
        "entrypoint": "null",
        "cmd": '["uvicorn","agh.server.app:app","--host","0.0.0.0","--port","8912"]',
    }


def test_container_pid_1_runs_as_non_root_without_root_group(
    running_container: str,
) -> None:
    status = _proc_status(running_container)

    assert status["Uid"][0] == "10001"
    assert status["Gid"][0] == "10001"
    assert "0" not in status["Groups"]


def test_runtime_user_can_write_required_data_paths(running_container: str) -> None:
    command = (
        "touch /data/.pytest-runtime "
        "/data/logs/.pytest-runtime "
        "/data/secrets/.pytest-runtime "
        "/data/packs/.pytest-runtime"
    )

    _run(
        "docker", "exec", "--user", RUNTIME_USER, running_container, "sh", "-c", command
    )


def test_named_volume_is_initialized_from_image_owned_data_tree(
    running_container: str,
) -> None:
    ownership = _run(
        "docker",
        "exec",
        running_container,
        "sh",
        "-c",
        "stat -c '%u:%g %F' /data /data/logs /data/secrets /data/packs /data/agh.sqlite3",
    ).stdout.splitlines()

    assert ownership == [
        "10001:10001 directory",
        "10001:10001 directory",
        "10001:10001 directory",
        "10001:10001 directory",
        "10001:10001 regular file",
    ]


def _prepare_bind_mount(image: str, bind_mount: Path, owner: str) -> None:
    _run(
        "docker",
        "run",
        "--rm",
        "--user",
        "0:0",
        "--entrypoint",
        "sh",
        "-v",
        f"{bind_mount}:/data",
        image,
        "-c",
        "mkdir -p /data/logs /data/secrets /data/packs && "
        "touch /data/agh.sqlite3 && "
        f"chown -R {owner} /data && chmod -R u+rwX,g+rwX /data",
    )


@pytest.fixture
def owned_bind_mount(tmp_path: Path, docker_image: str) -> Iterator[Path]:
    bind_mount = tmp_path / "data"
    bind_mount.mkdir()
    try:
        _prepare_bind_mount(docker_image, bind_mount, RUNTIME_USER)
    except subprocess.CalledProcessError as exc:
        _skip_or_fail(
            "Docker environment cannot chown bind-mounted host paths from a container: "
            f"{exc.stderr.strip()}"
        )
    try:
        yield bind_mount
    finally:
        _prepare_bind_mount(docker_image, bind_mount, f"{os.getuid()}:{os.getgid()}")


def test_pre_owned_bind_mount_is_operator_responsibility(
    docker_image: str,
    owned_bind_mount: Path,
) -> None:
    container = _run(
        "docker",
        "run",
        "-d",
        "-e",
        "AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com",
        "-v",
        f"{owned_bind_mount}:/data",
        docker_image,
    ).stdout.strip()
    try:
        _wait_for_health(container)
        _run(
            "docker",
            "exec",
            container,
            "sh",
            "-c",
            "touch /data/.pytest-bind /data/logs/.pytest-bind "
            "/data/secrets/.pytest-bind /data/packs/.pytest-bind",
        )
    finally:
        _run("docker", "rm", "-f", container, check=False)


def test_root_owned_bind_mount_is_not_repaired_by_container(
    docker_image: str,
    tmp_path: Path,
) -> None:
    bind_mount = tmp_path / "root-owned-data"
    (bind_mount / "logs").mkdir(parents=True)
    (bind_mount / "secrets").mkdir()
    (bind_mount / "packs").mkdir()
    (bind_mount / "agh.sqlite3").touch()
    if os.getuid() == 10001:
        _skip_or_fail("Host user already matches the container runtime UID")
    try:
        _prepare_bind_mount(docker_image, bind_mount, "0:0")
    except subprocess.CalledProcessError:
        for path in [bind_mount, *bind_mount.iterdir()]:
            path.chmod(0o755 if path.is_dir() else 0o644)

    container = _run(
        "docker",
        "run",
        "-d",
        "-e",
        "AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com",
        "-v",
        f"{bind_mount}:/data",
        docker_image,
    ).stdout.strip()
    try:
        command = (
            "import urllib.request; "
            "urllib.request.urlopen('http://127.0.0.1:8912/api/v1/health')"
        )
        for _ in range(5):
            result = _run(
                "docker", "exec", container, "python", "-c", command, check=False
            )
            assert result.returncode != 0
            time.sleep(1)
    finally:
        _run("docker", "rm", "-f", container, check=False)
        try:
            _prepare_bind_mount(
                docker_image, bind_mount, f"{os.getuid()}:{os.getgid()}"
            )
        except subprocess.CalledProcessError:
            pass
