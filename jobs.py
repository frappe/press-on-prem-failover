from utils.setup_prerequisite import execute


def start_benches_in_background(benches: list[str]) -> None:
    """Start all available benches in the background"""
    for bench in benches:
        execute(f"docker start {bench}", raises=False)
