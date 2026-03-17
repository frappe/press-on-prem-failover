import json
import logging
import os
import shlex
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)
REQUIRED_SERVICES = ["docker", "mysql", "nginx"]
BENCHES_DIRECTORY = "/home/frappe/benches"


@dataclass
class ServerStatus:
    services: dict[str, bool]
    benches: dict[str, str]
    images: list[str]
    missing_images: dict[str, str]
    bench_ok: bool
    status: str


class MissingBenchFilesError(Exception):
    pass


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


def active_benches(benches_directory: str) -> dict[str, str]:
    """Return a dict of bench_name -> docker_image for all valid active benches."""
    result = {}
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
            raise MissingBenchFilesError(
                f"Bench {entry} is missing required files or directories."
            )

        config_path = os.path.join(full_path, "config.json")
        with open(config_path) as f:
            image = json.load(f).get("docker_image")

        result[entry] = image

    return result


def active_images() -> int:
    """Check docker images present"""
    output = execute("docker images --format '{{.Repository}}:{{.Tag}}'")
    return output.splitlines() if output else []


def has_accessible_benches_dir(benches_directory: str) -> bool:
    """Check if file is present and user has r/w access."""
    return os.path.exists(benches_directory) and os.access(
        benches_directory, os.R_OK | os.W_OK
    )


def check_server_status() -> ServerStatus:
    """Check the status of required services, benches, and images."""
    services = {s: is_service_active(s) for s in REQUIRED_SERVICES}
    bench_ok = has_accessible_benches_dir(BENCHES_DIRECTORY)
    benches = active_benches(BENCHES_DIRECTORY) if bench_ok else {}
    images = active_images()
    missing_images = {
        bench: image for bench, image in benches.items() if image not in images
    }
    status = (
        "ok" if all(services.values()) and bench_ok and not missing_images else "error"
    )
    return ServerStatus(services, benches, images, missing_images, bench_ok, status)
