import logging
import sys

from flask import Flask, render_template, request
from jobs import initialize_and_start_benches
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from utils.setup_prerequisite import BENCHES_DIRECTORY, check_server_status


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


@app.before_request
def check_setup_status():
    s = check_server_status()
    if s.status != "ok":
        return {"error": True, "reason": "setup not ready"}, 400

    request.environ["server_state"] = s


@app.errorhandler(404)
def page_not_found(_):
    return render_template("404.html"), 404


# Route for the main page that shows the setup status
@app.route("/setup-status")
def failover_setup_status():
    server_state = request.environ.get("server_state")
    return render_template(
        "setup_status.html",
        status=server_state.status,
        services=server_state.services,
        bench_dir=BENCHES_DIRECTORY,
        bench_ok=server_state.bench_ok,
        benches=server_state.benches,
        malformed_benches=server_state.malformed_benches,
    ), 200 if server_state.status == "ok" else 503

# Route for page that shows bench start status (fires the start benches api)
@app.route("/start-benches")
def start_benches_page():
    server_state = request.environ.get("server_state")
    return render_template(
        "start_benches.html",
        status=server_state.status,
        benches=server_state.benches,
    )


@app.route("/api/start-benches", methods=["POST"])
def start_benches_api():
    server_state = request.environ.get("server_state")
    try:
        existing_job = Job.fetch(START_BENCHES_JOB_ID, connection=queue.connection)
        if existing_job.get_status() in ("queued", "started"):
            return {"status": "already running"}, 202
    except NoSuchJobError:
        pass

    queue.enqueue(
        initialize_and_start_benches,
        benches=server_state.benches,
        job_id=START_BENCHES_JOB_ID,
    )
    return {
        "status": "queued",
        "benches": list(server_state.benches.keys()),
        "job_id": START_BENCHES_JOB_ID,
    }, 202


if __name__ == "__main__":
    app.run(debug=True)
