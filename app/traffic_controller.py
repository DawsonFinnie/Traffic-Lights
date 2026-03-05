# app/traffic_controller.py
# =============================================================================
# TRAFFIC CONTROLLER - This file controls the light sequencing logic.
# It runs in a background thread (started in main.py) and loops forever,
# advancing through red → green → yellow → red → ...
#
# It reads state.running to decide whether to advance or hold.
# It writes state.current to tell the rest of the app which light is active.
# =============================================================================

import time                     # Standard Python library for time.sleep()
from app.state import state     # Import the shared state object

# How long each light stays on (in seconds)
CYCLE_TIMES = {
    "red":    5,      # Red stays on for 5 seconds
    "green":  5,      # Green stays on for 5 seconds
    "yellow": 2.5     # Yellow stays on for 2.5 seconds
}

# The order the lights cycle through
SEQUENCE = ["red", "green", "yellow"]

def run_traffic_loop():
    # This function runs forever in a background thread
    while True:
        for light in SEQUENCE:          # Loop through red → green → yellow

            if not state.running:       # If stopped (Start/Stop button was pressed)
                time.sleep(0.5)         # Wait 0.5s and check again instead of advancing
                continue                # Skip to next iteration without changing the light

            # If running, update the shared state to the current light
            state.current = light
            print(f'Light changed to: {light}"')

            # Hold this light for its defined duration before moving to the next
            # NOTE: time.sleep() blocks this thread only - Flask and BACnet keep running
            time.sleep(CYCLE_TIMES[light])
