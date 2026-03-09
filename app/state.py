# app/state.py
# =============================================================================
# SHARED STATE - This is the "single source of truth" for the whole application.
# It holds two pieces of information:
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
# This is called the Singleton pattern — one shared instance, everyone uses it.
#
# RABBITMQ INTEGRATION:
# We've added RabbitMQ publishing to this file because state.py is the single
# point where ALL state changes happen. Instead of adding publish calls to
# traffic_controller.py AND main.py separately, we override Python's
# __setattr__ to intercept every write to self.current or self.running
# and automatically publish to RabbitMQ.
#
# __setattr__ is a special Python method called automatically whenever
# you set an attribute on an object:
#   state.current = "green"   → Python calls state.__setattr__("current", "green")
#   state.running = False     → Python calls state.__setattr__("running", False)
#
# This means we get automatic RabbitMQ publishing with zero changes needed
# in traffic_controller.py or main.py — they keep working exactly as before.
# =============================================================================

import logging
logger = logging.getLogger(__name__)


class TrafficState:

    def __init__(self):
        # Use object.__setattr__ here instead of self.current = "red"
        # because our custom __setattr__ below would fire during __init__
        # before the object is fully set up, causing errors.
        # object.__setattr__ bypasses our override and sets values directly.
        object.__setattr__(self, 'current', "red")   # Start on red
        object.__setattr__(self, 'running', True)    # Start running automatically


    def __setattr__(self, name, value):
        """
        Called automatically by Python whenever any attribute is set on this object.
        e.g. state.current = "green" triggers this with name="current", value="green"

        We use this to:
          1. Set the value normally
          2. Automatically publish the new state to RabbitMQ after every change

        WHY object.__setattr__ instead of self.name = value?
        Writing "self.current = value" inside __setattr__ would call __setattr__
        again, which would call itself again — infinite recursion.
        object.__setattr__ sets the value directly, bypassing our override.
        """

        # Set the value on the object normally first
        object.__setattr__(self, name, value)

        # After any change to current or running, publish the new state to RabbitMQ
        # We only publish on these two attributes — Python sets many other internal
        # attributes internally that we don't want to trigger publishing
        if name in ("current", "running"):
            self._publish()


    def _publish(self):
        """
        Publishes the current state to RabbitMQ.
        Called automatically after every state change via __setattr__.

        We import publisher inside this method rather than at the top of the file
        to avoid a circular import issue during Python's startup sequence.
        Importing inside a method is safe and only slightly less efficient.
        """
        try:
            from app.rabbitmq import publisher
            publisher.publish_state(self.current, self.running)
        except Exception as e:
            # Never let a RabbitMQ error affect the traffic light
            logger.warning(f"State publish failed: {e}")


# Create the single shared instance
# All other files import THIS object: from app.state import state
state = TrafficState()
