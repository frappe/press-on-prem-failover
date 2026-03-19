document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('startBtn');
    const errorContainer = document.getElementById('errorContainer');

    if (startBtn) {
        startBtn.addEventListener('click', async () => {
            // Reset UI state
            startBtn.disabled = true;
            startBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Starting...`;
            if (errorContainer) errorContainer.classList.add('d-none');

            try {
                const response = await fetch('/api/start-benches', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });

                if (!response.ok) {
                    const data = await response.json().catch(() => ({}));
                    throw new Error(data.message || 'System not ready for failover.');
                }

                // Success: Redirect to monitoring
                window.location.href = '/site-mapping';

            } catch (err) {
                // Re-enable button and show simple error
                startBtn.disabled = false;
                startBtn.innerHTML = `<i class="bi bi-play-fill me-1"></i> Start Failover`;
                
                if (errorContainer) {
                    errorContainer.textContent = err.message;
                    errorContainer.classList.remove('d-none');
                } else {
                    alert(err.message); // Fallback if container is missing
                }
            }
        });
    }
});
