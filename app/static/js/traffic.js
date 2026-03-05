/// app/static/js/traffic.js
// =============================================================================
// FRONTEND JAVASCRIPT - Runs in the browser, not on the server.
// Responsible for:
//   1. Polling the Flask /status endpoint every 500ms
//   2. Updating the traffic light bulb display based on the response
//   3. Handling the Start/Stop button click
//
// This file is served as a static file by Flask and loaded by index.html
// =============================================================================

// --- GET REFERENCES TO HTML ELEMENTS ---
// These grab the actual DOM elements from index.html so we can update them
const bulbs = {
    red:    document.getElementById("bulb-red"),     // The red circle div
    yellow: document.getElementById("bulb-yellow"),  // The yellow circle div
    green:  document.getElementById("bulb-green"),   // The green circle div
};
const statusLabel = document.getElementById("status-label");  // The text below the light
const toggleBtn   = document.getElementById("toggle-btn");    // The Start/Stop button


// --- UPDATE DISPLAY ---
// Called every time we get a response from /status
// Takes the current light state ("red"/"yellow"/"green") and running (true/false)
function updateLight(state, running) {

    // First reset all bulbs to their dim/off state by setting just the base class
    bulbs.red.className    = "bulb";
    bulbs.yellow.className = "bulb";
    bulbs.green.className  = "bulb";

    // If running and the state matches a known bulb, light it up
    // Adding "red-on", "yellow-on", or "green-on" class triggers the CSS glow effect
    if (running && bulbs[state]) {
        bulbs[state].className = `bulb ${state}-on`;
    }

    // Update the status text below the light housing
    statusLabel.textContent = running ? state.toUpperCase() : "STOPPED";

    // Update the status text color to match the active light
    statusLabel.style.color = !running        ? "#888"     // grey when stopped
                            : state === "red"    ? "#ff2200"  // red
                            : state === "yellow" ? "#ffcc00"  // yellow
                            :                     "#00cc44";  // green

    // Update the button text and color based on current running state
    toggleBtn.textContent   = running ? "Stop"    : "Start";
    toggleBtn.style.background = running ? "#cc0000" : "#007700";  // red button when running, green when stopped
}


// --- POLL STATUS ---
// This function runs every 500ms (set at the bottom with setInterval)
// It asks the Flask server for the current state and updates the UI
// Uses async/await so the browser doesn't freeze while waiting for the response
async function pollStatus() {
    try {
        const response = await fetch("/status");        // HTTP GET request to Flask /status route
        const data     = await response.json();         // Parse the JSON response: {state, running}
        updateLight(data.state, data.running);          // Update the UI with the new data
    } catch (error) {
        // If the server is unreachable (e.g. container stopped), show connection lost
        statusLabel.textContent   = "Connection lost";
        statusLabel.style.color   = "#888";
    }
}


// --- TOGGLE BUTTON HANDLER ---
// Called when the Start/Stop button is clicked
// Sends a POST request to either /start or /stop depending on current state
async function toggleTraffic() {
    // Determine which endpoint to call based on the button's current text
    const endpoint = toggleBtn.textContent === "Stop" ? "/stop" : "/start";

    // Send the POST request to Flask - no body needed, just the URL
    await fetch(endpoint, { method: "POST" });

    // No need to manually update the UI here
    // pollStatus() will pick up the change within 500ms automatically
}


// --- EVENT LISTENERS AND TIMERS ---
toggleBtn.addEventListener("click", toggleTraffic);  // Wire up the button click handler
setInterval(pollStatus, 500);