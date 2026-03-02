/// app/static/js/traffic.js

const bulbs = {
    red: document.getElementById("bulb-red"),
    yellow: document.getElementById("bulb-yellow"),
    green: document.getElementById("bulb-green"),
};

const statusLabel = document.getElementById("status-label");
const toggleBtn = document.getElementById("toggle-btn");

// Update the light display and button based on what the server returns
function updateLight(state, running) {
    bulbs.red.className = "bulb";
    bulbs.yellow.className = "bulb";
    bulbs.green.className = "bulb";

    if (running && bulbs[state]) {
        bulbs[state].className = `bulb ${state}-on`;
    }

    statusLabel.textContent = running ? state.toUpperCase() : "STOPPED";
    statusLabel.style.color = !running ? "#888"
                            : state === "red" ? "#ff2200"
                            : state === "yellow" ? "#ffcc00"
                            : "#00cc44";

    // Update button appearance
    toggleBtn.textContent = running ? "Stop" : "Start";
    toggleBtn.style.background = running ? "#cc0000" : "#007700";
}

// Poll for current status every 500ms
async function pollStatus() {
    try {
        const response = await fetch("/status");
        const data = await response.json();
        updateLight(data.state, data.running);
    } catch (error) {
        statusLabel.textContent = "Connection lost";
        statusLabel.style.color = "#888";
    }
}

// Called when button is clicked
async function toggleTraffic() {
    const endpoint = toggleBtn.textContent === "Stop" ? "/stop" : "/start";
    await fetch(endpoint, { method: "POST" });
    // No need to do anything else — pollStatus will pick up the change
}

toggleBtn.addEventListener("click", toggleTraffic);

setInterval(pollStatus, 500);
pollStatus();