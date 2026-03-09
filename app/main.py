# app/main.py
# =============================================================================
# ENTRY POINT - This is the first file Python runs when the app starts.
# It is responsible for:
#   1. Creating the Flask web server
#   2. Defining all the URL routes (what happens when the browser visits a URL)
#   3. Connecting to RabbitMQ (new — DAWS_BAS integration)
#   4. Starting the traffic loop and Flask in background threads
#   5. Starting the BACnet server on the main thread (required by asyncio)
#
# RABBITMQ CHANGE:
# We import the publisher singleton from rabbitmq.py and call publisher.connect()
# before starting any threads. This ensures the RabbitMQ connection is ready
# before the traffic loop starts changing state and triggering publish calls.
# If RabbitMQ is unreachable, connect() logs a warning and the app continues
# normally — RabbitMQ is non-critical to the traffic light's core function.
# =============================================================================

import asyncio                                         # Needed to run the BACnet server
from flask import Flask, jsonify, render_template     # Flask web framework
from threading import Thread                          # For running things in background threads
from app.state import state                           # Shared state singleton
from app.traffic_controller import run_traffic_loop  # Light sequencing loop
from app.bacnet_server import run_bacnet_server       # BACnet server (async)
from app.rabbitmq import publisher                    # RabbitMQ publisher singleton (NEW)

app = Flask(__name__)


# --- URL ROUTES ---
# Each @app.route decorator maps a URL to a Python function.
# When a browser visits that URL, Flask calls the function and returns the result.

@app.route("/")
def home():
    # Serve the traffic light web UI (index.html)
    return render_template("index.html")


@app.route("/status")
def status():
    # Returns current state as JSON — polled every 500ms by the browser
    # Example response: {"state": "red", "running": true}
    return jsonify({"state": state.current, "running": state.running})


@app.route("/start", methods=["POST"])
def start():
    # Setting state.running triggers __setattr__ in state.py
    # which automatically publishes the change to RabbitMQ
    state.running = True
    return jsonify({"running": True})


@app.route("/stop", methods=["POST"])
def stop():
    # Same — __setattr__ publishes the stopped state to RabbitMQ automatically
    state.running = False
    return jsonify({"running": False})


# --- STARTUP ---
# This block only runs when you execute main.py directly (not when imported)
if __name__ == "__main__":

    # Step 1: Connect to RabbitMQ (NEW)
    # Must be done before starting threads so the publisher is ready
    # when the traffic loop immediately starts changing state.
    # If RabbitMQ is down, this logs a warning and continues.
    publisher.connect()

    # Step 2: Start the traffic light loop in a background thread
    # daemon=True means this thread dies automatically when the main program exits
    Thread(target=run_traffic_loop, daemon=True).start()

    # Step 3: Start Flask web server in a background thread
    # host="0.0.0.0" = accept connections from any IP (not just localhost)
    # port=8500 = the web UI port
    Thread(target=lambda: app.run(host="0.0.0.0", port=8500), daemon=True).start()

    # Step 4: Start BACnet server on the main thread
    # BAC0 requires the main thread's asyncio event loop — must be last
    # asyncio.run() blocks here and keeps the whole program alive
    asyncio.run(run_bacnet_server())
