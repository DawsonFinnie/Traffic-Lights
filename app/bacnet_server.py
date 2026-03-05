# app/bacnet_server.py

import asyncio
import os
import BAC0
from BAC0.core.devices.local.factory import binary_value
from app.state import state

POLL_INTERVAL = 0.5


async def sync_loop(bacnet):
    last_state = None
    while True:
        current = state.current
        running = state.running

        if current != last_state:
            bacnet["red_light"].presentValue    = "active" if current == "red"    else "inactive"
            bacnet["yellow_light"].presentValue = "active" if current == "yellow" else "inactive"
            bacnet["green_light"].presentValue  = "active" if current == "green"  else "inactive"
            last_state = current
            print(f"BACnet updated: {current}")

        bacnet["running"].presentValue = "active" if running else "inactive"
        await asyncio.sleep(POLL_INTERVAL)


async def run_bacnet_server():
    print("Starting BACnet server...")

    # Use environment variables so this works in Docker and on any machine
    # Set BACNET_IP in docker-compose.yml to control which IP BAC0 binds to
    ip = os.environ.get("BACNET_IP", None)
    device_id = int(os.environ.get("BACNET_DEVICE_ID", "3001"))

    if ip:
        print(f"Using BACNET_IP from environment: {ip}")
        bacnet = BAC0.lite(ip=ip, deviceId=device_id)
    else:
        print("No BACNET_IP set, letting BAC0 auto-detect...")
        bacnet = BAC0.lite(deviceId=device_id)

    # Wait for BAC0 to fully initialize before registering objects
    # Without this delay, YABE cannot read the object list
    await asyncio.sleep(2)
    from bacpypes3.local.cov import GenericCriteria

    binary_value(
        name="red_light",
        instance=1,
        description="Red Light Active",
        is_commandable=True,
        presentValue="inactive",
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
        presentValue="active",
        bacnet_properties={"objectIdentifier": ("binaryValue", 4)},
    ).add_objects_to_application(bacnet)
    # Explicitly enable COV on all binary value objects

    for obj_name in ["red_light", "yellow_light", "green_light", "running"]:
        obj = bacnet.this_application.app.get_object_name(obj_name)
        if obj:
            obj._cov_criteria = GenericCriteria
            obj._object_supports_cov = True
            print(f"COV enabled on {obj_name}")
    

    print(f"BACnet device online. Device ID: {device_id}")
    await sync_loop(bacnet)