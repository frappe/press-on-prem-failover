const currentJobStatus = document.currentScript.dataset.jobStatus;

document.getElementById("refreshBtn")?.addEventListener("click", async () => {
  const btn = document.getElementById("refreshBtn");

  btn.disabled = true;
  btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Checking...`;

  try {
    const response = await fetch("/api/job-status");
    const data = await response.json();

    btn.disabled = false;
    btn.innerHTML = `<i class="bi bi-arrow-repeat"></i> Check Status`;

    if (data.status !== currentJobStatus) {
      window.location.reload();
    }

  } catch (err) {
    btn.disabled = false;
    btn.innerHTML = `<i class="bi bi-arrow-repeat"></i> Check Status`;
    console.error("Failed to fetch job status:", err);
  }
});