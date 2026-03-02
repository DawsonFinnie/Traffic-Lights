# app/main.py

import asyncio
from flask import Flask, jsonify, render_template
from threading import Thread
from app.state import state
from app.traffic_controller import run_traffic_loop
from app.bacnet_server import run_bacnet_server

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/status")
def status():
    return jsonify({"state": state.current, "running": state.running})


@app.route("/start", methods=["POST"])
def start():
    state.running = True
    return jsonify({"running": True})


@app.route("/stop", methods=["POST"])
def stop():
    state.running = False
    return jsonify({"running": False})


if __name__ == "__main__":
    # Traffic loop in background thread
    Thread(target=run_traffic_loop, daemon=True).start()

    # Flask in background thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=8500), daemon=True).start()

    # BAC0 needs to own the main thread's event loop - run it last
    asyncio.run(run_bacnet_server())