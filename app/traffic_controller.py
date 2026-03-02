import time
from app.state import state

CYCLE_TIMES = { "red" : 5 , "green" : 5, "yellow" : 2.5}

SEQUENCE = ["red", "green", "yellow"]

def run_traffic_loop():
    while True:
        for light in SEQUENCE:
            if not state.running:
                time.sleep(0.5)
                continue
            state.current = light
            print(f'Light changed to: {light}"')
            time.sleep(CYCLE_TIMES[light])