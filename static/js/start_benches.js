async function startBenches() {
    const statusDiv = document.getElementById("jobStatus");
  
    statusDiv.innerHTML = `
      <div class="alert alert-info d-flex gap-2 align-items-center">
        <span class="spinner-border spinner-border-sm"></span> Checking and starting benches...
      </div>`;
  
    try {
      const response = await fetch("/api/start-benches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();
  
      if (!response.ok && data.error) {
        statusDiv.innerHTML = `
          <div class="alert alert-danger d-flex gap-2 align-items-center">
            <i class="bi bi-x-circle"></i> Setup not ready — check the
            <a href="/setup-status" class="alert-link ms-1">status page</a> before starting.
          </div>`;
        return;
      }
  
      if (data.status === "already running") {
        statusDiv.innerHTML = `
          <div class="alert alert-warning d-flex gap-2 align-items-center">
            <i class="bi bi-hourglass-split"></i> A bench start job is already running.
          </div>`;
        return;
      }
  
      if (data.status === "queued") {
        statusDiv.innerHTML = `
          <div class="alert alert-success d-flex gap-2 align-items-center">
            <i class="bi bi-check-circle"></i>
            Job queued for: <strong class="ms-1">${data.benches.join(", ")}</strong>
          </div>`;
      }
  
    } catch (err) {
      statusDiv.innerHTML = `
        <div class="alert alert-danger d-flex gap-2 align-items-center">
          <i class="bi bi-wifi-off"></i> Could not reach the server.
        </div>`;
    }
  }
  
  // Auto-trigger on page load
  document.addEventListener("DOMContentLoaded", () => {
    startBenches();
  });