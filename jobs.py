from jinja2 import Environment, FileSystemLoader
from utils.setup_prerequisite import BENCHES_DIRECTORY, execute
from utils.site_mapping import get_port_mapping_for_sites
from utils.types import BenchInfo


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


def initialize_and_start_benches(benches: dict[str, BenchInfo]):
    """Extract assets from image and start all available benches in the background"""
    generate_bench_nginx_configs(benches=benches)

    for bench_name, bench_info in benches.items():
        execute(
            "docker run -uroot --rm --net none "
            f"-v /home/frappe/benches/{bench_name}/sites/assets:/home/frappe/frappe-bench/sitesmount "
            f"{bench_info['image']} "
            "bash -c 'cp -LR sites/assets/. sitesmount && chown -R frappe:frappe sitesmount'",
            timeout=500,
        )
        execute(f"docker start {bench_name}", raises=False, timeout=500)
