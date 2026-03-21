from __future__ import annotations

import json
import os
import typing

from rq.exceptions import NoSuchJobError
from rq.job import Job

from utils.types import BenchSiteMapping

from .setup_prerequisite import BENCHES_DIRECTORY, SITE_BACKUP_JOB_ID

if typing.TYPE_CHECKING:
    from rq import Queue

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


def is_backup_available(bench_name: str, site: str, queue: Queue) -> bool:
    """Check if the backup has been archived already & ensure this site is not being backup again"""
    backup_path = os.path.join(
        BENCHES_DIRECTORY, bench_name, "sites", site, "private", "backup.tar.gz"
    )
    has_archived_path = os.path.isfile(backup_path)
    try:
        job_status = (
            Job.fetch(SITE_BACKUP_JOB_ID.format(site), connection=queue.connection)
            .get_status()
            .value
        )
        is_being_backed_up = job_status in ("started", "queued")
    except NoSuchJobError:
        is_being_backed_up = False

    return has_archived_path and not is_being_backed_up


def get_sites_with_available_backups(
    nginx_config: dict, queue: Queue
) -> dict[str, bool]:
    """Get all sites that have backup available and are present in the nginx config (mapped)"""
    return {
        site: is_backup_available(bench, site, queue)
        for bench, site_info in nginx_config.items()
        for site in site_info.get("sites", {})
    }
