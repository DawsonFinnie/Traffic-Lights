# app/main.py
# =============================================================================
# ENTRY POINT - This is the first file Python runs when the app starts.
# It is responsible for:
#   1. Creating the Flask web server
#   2. Defining all the URL routes (what happens when the browser visits a URL)
#   3. Starting the traffic loop and Flask in background threads
#   4. Starting the BACnet server on the main thread (required by asyncio)
# =============================================================================

import asyncio                          # Python's async library - needed to run the BACnet server
from flask import Flask, jsonify, render_template  # Flask web framework tools
from threading import Thread            # Allows running multiple things at once in the background
from app.state import state             # Imports the shared state object (current light + running flag)
from app.traffic_controller import run_traffic_loop  # The function that cycles the lights
from app.bacnet_server import run_bacnet_server      # The async function that runs the BACnet server

app = Flask(__name__)                   # Creates the Flask web application instance


# --- URL ROUTES ---
# Each @app.route decorator maps a URL to a Python function.
# When a browser or script visits that URL, Flask calls the function and returns the result.

@app.route("/")                         # When browser visits http://<ip>:8500/
def home():
    return render_template("index.html")  # Serve the HTML page (the traffic light UI)

@app.route("/status")                   # When browser visits http://<ip>:8500/status
def status():
    # Returns current light state and running flag as JSON
    # JavaScript polls this every 500ms to update the UI
    # Example response: {"state": "red", "running": true}
    return jsonify({"state": state.current, "running": state.running})

@app.route("/start", methods=["POST"])  # Only accepts POST requests (button click sends POST)
def start():
    state.running = True                # Set the shared running flag to True
    return jsonify({"running": True})   # Confirm back to the browser

@app.route("/stop", methods=["POST"])   # Only accepts POST requests
def stop():
    state.running = False               # Set the shared running flag to False
    return jsonify({"running": False})  # Confirm back to the browser


# --- STARTUP ---
# This block only runs when you execute main.py directly (not when imported)
if __name__ == "__main__":

    # Start the traffic light loop in a background thread
    # daemon=True means this thread will die automatically when the main program exits
    Thread(target=run_traffic_loop, daemon=True).start()

    # Start Flask web server in a background thread
    # host="0.0.0.0" means accept connections from any IP (not just localhost)
    # port=8500 is the port the web UI is served on
    # daemon=True means this thread dies when the main program exits
    Thread(target=lambda: app.run(host="0.0.0.0", port=8500), daemon=True).start()

    # BAC0 (BACnet library) requires the main thread's asyncio event loop
    # asyncio.run() creates that event loop and hands it to run_bacnet_server()
    # This MUST be last - it blocks here and keeps the program alive
    asyncio.run(run_bacnet_server())