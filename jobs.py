from utils.setup_prerequisite import execute


def initialize_and_start_benches(benches: dict[str, str]) -> None:
    """Extract assets from image and start all available benches in the background"""
    for bench, image in benches.items():
        execute(
            "docker run -uroot --rm --net none "
            f"-v /home/frappe/benches/{bench}/sites/assets:/home/frappe/frappe-bench/sitesmount "
            f"{image} "
            "bash -c 'cp -LR sites/assets/. sitesmount && chown -R frappe:frappe sitesmount'",
            timeout=500,
        )
        execute(f"docker start {bench}", raises=False, timeout=500)
