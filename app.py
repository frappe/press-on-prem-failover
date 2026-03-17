import logging
import sys

from flask import Flask, render_template
from utils.setup_prerequisite import (
    BENCHES_DIRECTORY,
    REQUIRED_SERVICES,
    has_accessible_benches_dir,
    active_benches,
    active_images,
    is_service_active,
)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure global logging for the Flask app."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )


configure_logging()

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "Hello, World! This is the Press On-Prem Failover application."


@app.route("/start")
def start_failover():
    return "Starting failover process to on-premises server"


@app.route("/setup-status")
def failover_setup_status():
    services = {s: is_service_active(s) for s in REQUIRED_SERVICES}
    all_active_services = all(services.values())
    bench_ok = has_accessible_benches_dir(BENCHES_DIRECTORY)
    benches = active_benches(BENCHES_DIRECTORY) if bench_ok else {}
    images = active_images()

    missing_images = {
        bench: image for bench, image in benches.items() if image not in images
    }

    status = (
        "ok" if all_active_services and bench_ok and not missing_images else "error"
    )

    return render_template(
        "setup_status.html",
        status=status,
        services=services,
        bench_dir=BENCHES_DIRECTORY,
        bench_ok=bench_ok,
        benches=benches,
        images=images,
        missing_images=missing_images,
    ), 200 if status == "ok" else 503


if __name__ == "__main__":
    app.run(debug=True)
