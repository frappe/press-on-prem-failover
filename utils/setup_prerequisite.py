import json
import logging
import os
import shlex
import subprocess
from dataclasses import dataclass

from utils.types import BenchInfo

logger = logging.getLogger(__name__)
REQUIRED_SERVICES = ["docker", "nginx"]
BENCHES_DIRECTORY = "/root/frappe-cloud/benches/home/frappe/benches"
DATABASE_CONTAINER_NAME = "fc-dr-db-replica"
DOCKER_NETWORK_NAME = "on_prem_replica_net"
START_BENCHES_JOB_ID = "start-benches"
DATABASE_BASE_DIRECTORY = "/root/frappe-cloud/database"

@dataclass
class ServerStatus:
    services: dict[str, bool]
    benches: dict[str, str]
    malformed_benches: list[str]
    bench_ok: bool
    status: str


def execute(cmd: str, raises: bool = True, timeout: int = 5) -> str | None:
    """Execute a shell command and return the output"""
    try:
        result = subprocess.run(
            shlex.split(cmd),
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        msg = f"Command timed out after {timeout}s: {cmd!r}"
        logger.error(msg)
        if raises:
            raise RuntimeError(msg)
        return None

    except subprocess.CalledProcessError as e:
        msg = f"Command failed (exit {e.returncode}): {cmd!r}\n{e.stderr.strip()}"
        logger.error(msg)
        if raises:
            raise RuntimeError(msg)
        return None

    except Exception as e:
        msg = f"Unexpected error executing command: {cmd!r}\n{str(e)}"
        logger.error(msg)
        if raises:
            raise RuntimeError(msg)
        return None


def is_service_active(service: str) -> bool:
    """Check if a systemd service is active."""
    return execute(f"systemctl is-active {service}", raises=False) == "active"


def active_images() -> list[str]:  # was `int`, wrong
    """Return list of docker images present on the host."""
    output = execute("docker images --format '{{.Repository}}:{{.Tag}}'")
    return output.splitlines() if output else []


def active_benches(benches_directory: str) -> tuple[dict[str, BenchInfo], list[str]]:
    """Return (valid_benches, malformed_benches).

    A bench is malformed if it's missing required files or its docker image
    is not present on the host. Only valid benches will be started.
    """
    result = {}
    malformed = []
    images = active_images()

    for entry in os.listdir(benches_directory):
        full_path = os.path.join(benches_directory, entry)

        if not entry.startswith("bench-") or not os.path.isdir(full_path):
            continue

        required_paths = [
            "config",
            "config.json",
            "nginx.conf",
            "sites",
            "sites/common_site_config.json",
        ]

        if not all(os.path.exists(os.path.join(full_path, p)) for p in required_paths):
            malformed.append(entry)
            continue

        config_path = os.path.join(full_path, "config.json")
        with open(config_path) as f:
            config = json.load(f)
            image = config.get("docker_image")
            web_port = config.get("web_port")
            socketio_port = config.get("socketio_port")

        if not image or image not in images:
            malformed.append(entry)
            continue

        result[entry] = {
            "image": image,
            "web_port": web_port,
            "socketio_port": socketio_port,
        }

    return result, malformed


def has_accessible_benches_dir(benches_directory: str) -> bool:
    """Check if directory is present and user has r/w access."""
    return os.path.exists(benches_directory) and os.access(
        benches_directory, os.R_OK | os.W_OK
    )


def check_server_status() -> ServerStatus:
    """Check the status of required services and benches."""
    services = {s: is_service_active(s) for s in REQUIRED_SERVICES}
    bench_ok = has_accessible_benches_dir(BENCHES_DIRECTORY)
    benches, malformed_benches = (
        active_benches(BENCHES_DIRECTORY) if bench_ok else ({}, [])
    )
    is_database_container_running = (
        execute(
            f"docker ps --filter 'name={DATABASE_CONTAINER_NAME}' --filter 'network={DOCKER_NETWORK_NAME}' --format '{{{{.Names}}}}'"
        )
        == DATABASE_CONTAINER_NAME
    )
    status = (
        "ok"
        if all(services.values())
        and bench_ok
        and benches
        and is_database_container_running
        else "error"
    )
    return ServerStatus(services, benches, malformed_benches, bench_ok, status)
