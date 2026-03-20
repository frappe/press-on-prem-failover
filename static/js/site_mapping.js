const currentJobStatus = document.currentScript.dataset.jobStatus;

function hideDownloadButton(site) {
  const downloadButton = document.getElementById(`download-backup-${site}`);
  if (downloadButton) {
    downloadButton.style.display = "none";
  }
}

function showDownloadButton(site) {
  const downloadButton = document.getElementById(`download-backup-${site}`);
  if (downloadButton) {
    console.log("Showing download button: ", site)
    downloadButton.style.display = "";
  }
}

document.getElementById("refreshBtn")?.addEventListener("click", async () => {
  const btn = document.getElementById("refreshBtn");

  btn.disabled = true;
  btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Checking...`;

  try {
    const response = await fetch("/api/job-status");
    const data = await response.json();


    Object.entries(data.backup_available).forEach(([site, available]) => {
      if (available) {
        showDownloadButton(site)
      };
    })

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

document.querySelectorAll(".backup-btn").forEach(btn => {
  btn.addEventListener("click", async function (event) {
    const site = this.dataset.site;
    const bench = this.dataset.bench;

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Starting...`;

    try {
      const response = await fetch("/api/site-backup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          site: site,
          bench_name: bench,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        if (data.status == "already running") {
          hideDownloadButton(site)
          alert(`Backup for site ${site} is already running`)
        } else {
          hideDownloadButton(site)
          alert(`Backup started for site: ${site}`);
        }
      } else {
        const errorData = await response.json();
        alert(`Failed to start backup: ${errorData.error}`);
      }
    } catch (err) {
      console.error("Failed to start backup:", err);
      alert("An error occurred while starting the backup.");
    } finally {
      btn.disabled = false;
      btn.innerHTML = "Backup";
    }
  });
});
