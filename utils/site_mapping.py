import json
import os

from utils.types import BenchSiteMapping

from .setup_prerequisite import BENCHES_DIRECTORY

BASE_PORT = 8000


def is_site_dir(path: str) -> bool:
    """Check if a directory is a valid site directory."""
    essential_site_files = {"private", "public", "site_config.json"}

    if not os.path.isdir(path):
        return False

    return essential_site_files.issubset(set(os.listdir(path)))


def get_port_for_site(site_name: str) -> int:
    """Derive a port number for a site based on its name."""
    return BASE_PORT + (hash(site_name) % 1000)


def get_port_mapping_for_sites(
    benches: list[str],
) -> dict[str, BenchSiteMapping]:
    """Map sites in benches to their respective ports.
        Example: {
        "bench1": {"sites": {"site1.local": 8001, "site2.local": 8002}},
        "bench2": {"sites": {"site3.local": 8003}},
    }

    """
    result = {}

    for bench in benches:
        sites = {}
        sites_dir = os.path.join(BENCHES_DIRECTORY, bench, "sites")

        for site in os.listdir(sites_dir):
            site_path = os.path.join(sites_dir, site)

            if is_site_dir(site_path):
                sites[site] = get_port_for_site(site)

        if sites:
            result[bench] = {"sites": sites}

    return result


def get_nginx_config(job_status: str) -> dict:
    """Return nginx config unless a job is currently running (it'll replace it anyway)."""
    if job_status in ("started", "queued"):
        return {}

    nginx_config_path = "nginx_configs.json"
    if os.path.exists(nginx_config_path):
        with open(nginx_config_path) as f:
            return json.load(f)

    return {}


def is_backup_available(bench_name: str, site: str) -> bool:
    """Check if backup folder is populated for site"""
    backup_path = os.path.join(
        BENCHES_DIRECTORY, bench_name, "sites", site, "private", "backups"
    )
    return os.path.exists(backup_path) and len(os.listdir(backup_path)) > 0


def get_sites_with_available_backups(nginx_config: dict) -> dict[str, bool]:
    """Get all sites that have backup available and are present in the nginx config (mapped)"""
    sites_with_backup = {}

    for bench, site_info in nginx_config.items():
        for sites in site_info.values():
            for site in sites:
                sites_with_backup[site] = is_backup_available(bench, site)

    return sites_with_backup
