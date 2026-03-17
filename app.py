import logging
import sys

from flask import Flask, render_template
from jobs import start_benches_in_background
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from utils.setup_prerequisite import (
    BENCHES_DIRECTORY,
    check_server_status,
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
queue = Queue(connection=Redis.from_url("redis://localhost:6379/0"))
START_BENCHES_JOB_ID = "start-benches"


@app.errorhandler(404)
def page_not_found(_):
    return render_template("404.html"), 404


@app.route("/setup-status")
def failover_setup_status():
    s = check_server_status()
    return render_template(
        "setup_status.html",
        status=s.status,
        services=s.services,
        bench_dir=BENCHES_DIRECTORY,
        bench_ok=s.bench_ok,
        benches=s.benches,
        images=s.images,
        missing_images=s.missing_images,
    ), 200 if s.status == "ok" else 503


@app.route("/start-benches")
def start_benches_page():
    s = check_server_status()
    return render_template(
        "start_benches.html",
        status=s.status,
        benches=s.benches,
        missing_images=s.missing_images,
    )


@app.route("/api/start-benches", methods=["POST"])
def start_benches_api():
    s = check_server_status()
    if s.status != "ok":
        return {"error": True, "reason": "setup not ready"}, 400

    try:
        existing_job = Job.fetch(START_BENCHES_JOB_ID, connection=queue.connection)
        if existing_job.get_status() in ("queued", "started"):
            return {"status": "already running"}, 202
    except NoSuchJobError:
        pass

    queue.enqueue(
        start_benches_in_background,
        benches=list(s.benches.keys()),
        job_id=START_BENCHES_JOB_ID,
    )
    return {
        "status": "queued",
        "benches": list(s.benches.keys()),
        "job_id": START_BENCHES_JOB_ID,
    }, 202


if __name__ == "__main__":
    app.run(debug=True)
