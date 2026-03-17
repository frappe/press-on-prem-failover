import json
import os

from .setup_prerequisite import BENCHES_DIRECTORY

BASE_PORT = 8000


def is_site_dir(path: str) -> bool:
    """A site dir should have a set of files"""
    essential_site_files = ["private", "public", "site_config.json"]
    for essential_site_file in essential_site_files:
        if not os.path.exists(os.path.join(path, essential_site_file)):
            return False


def get_port_for_site(site_name: str) -> int:
    """Derive a port number for a site based on its name"""
    return BASE_PORT + (hash(site_name) % 1000)


def get_port_mapping_for_sites(benches: list[str]):
    """Benches passed here will be ready to deploy map their sites to ports"""
    result = {}
    for bench in benches:
        sites_dir = os.path.join(BENCHES_DIRECTORY, bench, "sites")
        if os.path.isdir(sites_dir):
            result[bench] = {
                site: get_port_for_site(site)
                for site in os.listdir(sites_dir)
                if is_site_dir(os.path.join(sites_dir, site))
            }

    return result
