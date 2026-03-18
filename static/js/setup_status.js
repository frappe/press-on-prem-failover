document.getElementById("startBtn")?.addEventListener("click", async () => {
    const btn = document.getElementById("startBtn");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Starting...`;

    try {
        const response = await fetch("/api/start-benches", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });
        const data = await response.json();

        if (!response.ok) {
            btn.disabled = false;
            btn.innerHTML = `<i class="bi bi-play-fill"></i> Configure Sites And Start Benches`;
            alert("Failed to start benches. Please check the setup status.");
            return;
        }

        // job queued or already running — go to site mapping page
        window.location.href = "/site-mapping";

    } catch (err) {
        btn.disabled = false;
        btn.innerHTML = `<i class="bi bi-play-fill"></i> Configure Sites And Start Benches`;
        alert("Could not reach the server.");
    }
});