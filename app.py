import logging
import os
import sys

from flask import Flask, g, redirect, render_template, request, send_file
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.registry import StartedJobRegistry

from jobs import initialize_and_start_benches, start_backup
from utils.setup_prerequisite import (
    BENCHES_DIRECTORY,
    SITE_BACKUP_JOB_ID,
    START_BENCHES_JOB_ID,
    check_server_status,
)
from utils.site_mapping import get_nginx_config, get_sites_with_available_backups


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


@app.before_request
def check_setup_status():
    s = check_server_status()
    g.server_state = s


@app.errorhandler(404)
def page_not_found(_):
    return redirect("/")


@app.route("/")
def index():
    return render_template(
        "index.html",
        overall_status=g.server_state.status,
    )


# Route for the main page that shows the setup status
@app.route("/setup-status")
def failover_setup_status():
    return render_template(
        "setup_status.html",
        status=g.server_state.status,
        services=g.server_state.services,
        bench_dir=BENCHES_DIRECTORY,
        bench_ok=g.server_state.bench_ok,
        benches=g.server_state.benches,
        malformed_benches=g.server_state.malformed_benches,
    ), 200 if g.server_state.status == "ok" else 503


# Skipping the start benches page, the button on status page should all the api
@app.route("/site-mapping")
def site_mapping_page():
    try:
        job = Job.fetch(START_BENCHES_JOB_ID, connection=queue.connection)
        bench_job_status = job.get_status().value
    except NoSuchJobError:
        bench_job_status = "not started"

    nginx_config = get_nginx_config(bench_job_status)
    backup_available = get_sites_with_available_backups(nginx_config)

    return render_template(
        "site_mapping.html",
        status=g.server_state.status,
        benches=g.server_state.benches,
        bench_job_status=bench_job_status,
        backup_available=backup_available,
        nginx_config=nginx_config,
    )


@app.route("/api/job-status")
def job_status_api():
    try:
        job = Job.fetch(START_BENCHES_JOB_ID, connection=queue.connection)
        bench_job_status = job.get_status().value
    except NoSuchJobError:
        bench_job_status = "not started"

    nginx_config = get_nginx_config(bench_job_status)
    backup_available = get_sites_with_available_backups(nginx_config)

    return {"status": bench_job_status, "backup_available": backup_available}


@app.route("/api/start-benches", methods=["POST"])
def start_benches_api():
    try:
        existing_job = Job.fetch(START_BENCHES_JOB_ID, connection=queue.connection)
        if existing_job.get_status().value in ("queued", "started"):
            return {"status": "already running"}, 202
    except NoSuchJobError:
        pass

    queue.enqueue(
        initialize_and_start_benches,
        benches=g.server_state.benches,
        job_id=START_BENCHES_JOB_ID,
    )

    return {
        "status": "queued",
        "benches": list(g.server_state.benches.keys()),
        "job_id": START_BENCHES_JOB_ID,
    }, 202


@app.route("/api/site-backup/download")
def site_backup_download_api():
    site = request.args.get("site")
    bench_name = request.args.get("bench_name")

    if not site or not bench_name:
        return {"error": "Site name and bench name is required"}, 400

    backup_path = os.path.join(
        f"{BENCHES_DIRECTORY}/{bench_name}/sites/{site}/private/backup.tar.gz"
    )
    if not os.path.exists(backup_path):
        return {"error": "No backups found"}

    return send_file(backup_path, as_attachment=True, mimetype="application/zip")


@app.route("/api/site-backup", methods=["POST"])
def site_backup_api():
    data = request.get_json()
    site = data.get("site")
    bench_name = data.get("bench_name")

    if not site or not bench_name:
        return {"error": "Site name and bench name is required"}, 400

    registry = StartedJobRegistry(queue=queue)

    for job in registry.get_job_ids():
        if SITE_BACKUP_JOB_ID.replace("-{}", "") in job:
            return {"status": "Only one backup can run at a time"}, 400

    try:
        existing_job = Job.fetch(
            SITE_BACKUP_JOB_ID.format(site), connection=queue.connection
        )
        if existing_job.get_status().value in ("queued", "started"):
            return {"status": "already running"}, 202
    except NoSuchJobError:
        pass

    queue.enqueue(
        start_backup,
        site=site,
        bench_name=bench_name,
        job_id=SITE_BACKUP_JOB_ID.format(site),
    )

    return {
        "status": "queued",
        "job_id": SITE_BACKUP_JOB_ID.format(site),
    }, 202


if __name__ == "__main__":
    app.run(debug=True)
