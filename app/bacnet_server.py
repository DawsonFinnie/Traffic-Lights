# app/bacnet_server.py
# =============================================================================
# BACNET SERVER - This file creates a BACnet device on the network.
# BACnet is a building automation protocol used by systems like Metasys (JCI),
# Niagara, and other BMS platforms to read sensor and device data.
#
# This file does three things:
#   1. Creates a BAC0 "lite" device (a lightweight BACnet server)
#   2. Registers four Binary Value objects that represent the light states
#   3. Runs a sync loop that keeps those BACnet objects in sync with state.py
#
# BMS tools like Metasys and YABE can then discover this device on the network
# and read (or subscribe to) the four binary values in real time.
# =============================================================================

import asyncio                  # Required for async/await - BAC0 is async
import os                       # Used to read environment variables (IP, device ID)
import BAC0                     # The BACnet library that creates the device
from BAC0.core.devices.local.factory import binary_value  # Factory function to create BACnet objects
from app.state import state     # Import the shared state object

# How often (in seconds) the sync loop checks state.py and updates BACnet objects
POLL_INTERVAL = 0.5


async def sync_loop(bacnet):
    # ==========================================================================
    # SYNC LOOP - Runs forever, keeping BACnet object values in sync with state.py
    # Uses await asyncio.sleep() instead of time.sleep() so the event loop
    # can handle incoming BACnet requests while waiting between updates
    # ==========================================================================
    last_state = None           # Track the last known light state to avoid redundant updates

    while True:
        current = state.current     # Read current light from shared state
        running = state.running     # Read running flag from shared state

        # Only update light objects if the state has actually changed
        # This avoids unnecessary BACnet writes every 500ms
        if current != last_state:
            # Set the appropriate light to "active", all others to "inactive"
            bacnet["red_light"].presentValue    = "active" if current == "red"    else "inactive"
            bacnet["yellow_light"].presentValue = "active" if current == "yellow" else "inactive"
            bacnet["green_light"].presentValue  = "active" if current == "green"  else "inactive"
            last_state = current
            print(f"BACnet updated: {current}")

        # Always update running flag (checked every poll interval)
        bacnet["running"].presentValue = "active" if running else "inactive"

        # Yield control back to the event loop for 500ms
        # During this time BAC0 can handle COV notifications, read requests, etc.
        await asyncio.sleep(POLL_INTERVAL)


async def run_bacnet_server():
    # ==========================================================================
    # STARTUP - Creates the BAC0 device and registers all BACnet objects
    # This is an async function because BAC0 2025.x requires an asyncio event loop
    # ==========================================================================
    print("Starting BACnet server...")

    # Read IP and device ID from environment variables
    # This allows the same code to work in Docker, LXC, and local development
    # without hardcoding network settings
    ip = os.environ.get("BACNET_IP", None)              # e.g. "192.168.30.12/24"
    device_id = int(os.environ.get("BACNET_DEVICE_ID", "3001"))  # BACnet device instance number

    if ip:
        # Use the IP specified in the environment (set in docker-compose.yml or /etc/environment)
        print(f"Using BACNET_IP from environment: {ip}")
        bacnet = BAC0.lite(ip=ip, deviceId=device_id)
    else:
        # Let BAC0 auto-detect the machine's IP address
        print("No BACNET_IP set, letting BAC0 auto-detect...")
        bacnet = BAC0.lite(deviceId=device_id)

    # Wait 2 seconds for BAC0 to fully initialize before registering objects
    # Without this delay, BMS tools like YABE cannot read the object list
    await asyncio.sleep(2)

    # Import GenericCriteria here - used to fix COV for binary value objects
    # GenericCriteria triggers a COV notification on ANY value change (correct for binary)
    # The default COVIncrementCriteria is designed for analog values and breaks on binary
    from bacpypes3.local.cov import GenericCriteria

    # --- REGISTER BINARY VALUE OBJECTS ---
    # Each binary_value() call creates a BACnet Binary Value object and adds it to the device
    # Binary Values have two states: "active" (true/1) and "inactive" (false/0)
    # instance= is the BACnet object instance number (must be unique per device)
    # is_commandable=True adds a priority array, allowing BMS tools to write to the object

    binary_value(
        name="red_light",
        instance=1,
        description="Red Light Active",
        is_commandable=True,            # Allows BMS tools to write to this object
        presentValue="inactive",        # Starting value
        bacnet_properties={"objectIdentifier": ("binaryValue", 1)},
    ).add_objects_to_application(bacnet)

    binary_value(
        name="yellow_light",
        instance=2,
        description="Yellow Light Active",
        is_commandable=True,
        presentValue="inactive",
        bacnet_properties={"objectIdentifier": ("binaryValue", 2)},
    ).add_objects_to_application(bacnet)

    binary_value(
        name="green_light",
        instance=3,
        description="Green Light Active",
        is_commandable=True,
        presentValue="inactive",
        bacnet_properties={"objectIdentifier": ("binaryValue", 3)},
    ).add_objects_to_application(bacnet)

    binary_value(
        name="running",
        instance=4,
        description="Simulator Running",
        is_commandable=True,
        presentValue="active",          # Starts as active because the cycle runs on startup
        bacnet_properties={"objectIdentifier": ("binaryValue", 4)},
    ).add_objects_to_application(bacnet)

    # --- FIX COV FOR BINARY VALUES ---
    # Replace the default COV criteria (COVIncrementCriteria) with GenericCriteria
    # on each binary value object. This is required because:
    #   - COVIncrementCriteria is for analog values - it does math to check if value
    #     changed by more than a threshold, which crashes on "active"/"inactive" strings
    #   - GenericCriteria simply triggers a notification whenever presentValue changes
    # This fix allows Metasys/SNE to successfully subscribe to COV on these objects
    for obj_name in ["red_light", "yellow_light", "green_light", "running"]:
        obj = bacnet.this_application.app.get_object_name(obj_name)
        if obj:
            obj._cov_criteria = GenericCriteria     # Replace with correct COV class
            obj._object_supports_cov = True         # Explicitly flag as COV-capable
            print(f"COV enabled on {obj_name}")

    print(f"BACnet device online. Device ID: {device_id}")

    # Start the sync loop - this runs forever and never returns
    # It keeps the BACnet objects in sync with state.py
    await sync_loop(bacnet)