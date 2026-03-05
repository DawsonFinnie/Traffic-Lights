# app/state.py
# =============================================================================
# SHARED STATE - This is the "single source of truth" for the whole application.
# It is a simple class that holds two pieces of information:
#   1. current  - which light is active right now ("red", "yellow", or "green")
#   2. running  - whether the light cycle is active (True) or stopped (False)
#
# WHY A SEPARATE FILE?
# Three different parts of the app need to read and write this data:
#   - traffic_controller.py  writes current (advances the light sequence)
#   - bacnet_server.py       reads current and running (to update BACnet objects)
#   - main.py (Flask)        reads and writes running (start/stop button)
#
# By putting state in its own file, all three can import the SAME object.
# This is called the Singleton pattern - one shared instance, everyone uses it.
# =============================================================================

class TrafficState:
    def __init__(self):
        self.current = "red"    # The light starts on red when the app launches
        self.running = True     # The cycle starts automatically (True = running)

# Create a single instance of TrafficState
# All other files import THIS object, not the class itself
# So when traffic_controller writes state.current = "green",
# bacnet_server immediately sees "green" when it reads state.current
state = TrafficState()