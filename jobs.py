import json
import os

from jinja2 import Environment, FileSystemLoader
from utils.setup_prerequisite import (
    BENCHES_DIRECTORY,
    DATABASE_CONTAINER_NAME,
    DOCKER_NETWORK_NAME,
    execute,
)
from utils.site_mapping import get_port_mapping_for_sites
from utils.types import BenchInfo


def bench_container_exists(bench_name: str) -> bool:
    """Check if a Docker container for the bench already exists"""
    result = execute(
        f"docker ps -a --filter name=^{bench_name}$ --format '{{{{.Names}}}}'",
        timeout=30,
    )
    return bench_name in result.splitlines()


def generate_bench_nginx_configs(benches: dict[str, BenchInfo]):
    """Generate nginx config snippets for each bench and its sites"""
    mappings = get_port_mapping_for_sites(list(benches.keys()))
    template_env = Environment(loader=FileSystemLoader("templates"))
    for bench_name, site_mapping in mappings.items():
        rendered_config = template_env.get_template("bench_nginx.conf.j2").render(
            bench_name=bench_name,
            sites=site_mapping["sites"],
            web_port=benches[bench_name]["web_port"],
            socketio_port=benches[bench_name]["socketio_port"],
            benches_directory=BENCHES_DIRECTORY,
        )
        config_path = f"{BENCHES_DIRECTORY}/{bench_name}/nginx.conf"
        with open(config_path, "w") as config_file:
            config_file.write(rendered_config)

    with open("nginx_configs.json", "w") as f:
        import json

        json.dump(mappings, f, indent=4)


def deploy_bench_container(bench_name: str, port_offset: int, image: str) -> None:
    """Run a command inside the bench's Docker container"""
    webport = 18000 + port_offset
    socketio_port = 19000 + port_offset
    metrics_port = 16000 + port_offset
    redis_port = 13000 + port_offset
    cache_port = 11000 + port_offset
    ssh_port = 22000 + port_offset

    command = (
        f"docker run -d --init -u frappe --restart always --hostname {bench_name} "
        f"--security-opt seccomp=unconfined "
        f"-p 127.0.0.1:{webport}:8000 -p 127.0.0.1:{socketio_port}:9000 -p 127.0.0.1:{metrics_port}:8088 "
        f"-p 0.0.0.0:{redis_port}:13000 -p 0.0.0.0:{cache_port}:11000 -p 0.0.0.0:{ssh_port}:2200 "
        f"-v {BENCHES_DIRECTORY}/{bench_name}/sites:/home/frappe/frappe-bench/sites "
        f"-v {BENCHES_DIRECTORY}/{bench_name}/logs:/home/frappe/frappe-bench/logs "
        f"-v {BENCHES_DIRECTORY}/{bench_name}/config:/home/frappe/frappe-bench/config "
        f"--network {DOCKER_NETWORK_NAME} "  # Attach to the same network as the database container for internal communication
        f"--name {bench_name} {image}"
    )
    execute(command, timeout=300)


def update_database_host(bench_name: str):
    """Change database host in common_site_config.json to point to the database container's private IP"""
    common_site_config_path = (
        f"{BENCHES_DIRECTORY}/{bench_name}/sites/common_site_config.json"
    )

    if not os.path.exists(common_site_config_path):
        return

    with open(common_site_config_path, "r") as f:
        config = json.load(f)

    config["db_host"] = execute(
        f"docker inspect -f '{{ .NetworkSettings.Networks.{DOCKER_NETWORK_NAME}.IPAddress }}' {DATABASE_CONTAINER_NAME}"
    ).strip()

    with open(common_site_config_path, "w") as f:
        json.dump(config, f, indent=4)


def initialize_and_start_benches(benches: dict[str, BenchInfo]):
    """Extract assets from image and start all available benches in the background"""
    generate_bench_nginx_configs(benches=benches)

    for bench_name, bench_info in benches.items():
        update_database_host(bench_name)

        execute(
            "docker run -uroot --rm --net none "
            f"-v /home/frappe/benches/{bench_name}/sites/assets:/home/frappe/frappe-bench/sitesmount "
            f"{bench_info['image']} "
            "bash -c 'cp -LR sites/assets/. sitesmount && chown -R frappe:frappe sitesmount'",
            timeout=500,
        )
        if bench_container_exists(bench_name):
            execute(f"docker start {bench_name}", raises=False, timeout=500)
        else:
            port_offset = (
                int(bench_info["web_port"]) - 18000
            )  # We know the starting point of the web ports, so we can calculate the offset for other ports
            deploy_bench_container(
                bench_name, port_offset=port_offset, image=bench_info["image"]
            )
