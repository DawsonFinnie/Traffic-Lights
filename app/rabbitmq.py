# app/rabbitmq.py
# =============================================================================
# RABBITMQ PUBLISHER - Sends traffic light state changes to DAWS_BAS.
#
# WHAT IS THIS FILE?
# This file is the bridge between the Traffic Light simulator and the
# DAWS_BAS infrastructure. Every time the light changes state, this file
# publishes a message to RabbitMQ so the rest of DAWS_BAS can see it.
#
# WHY ADD THIS?
# The traffic light already speaks BACnet — the SNE and Metasys can see it.
# Adding RabbitMQ creates a second, independent data path:
#
#   BACnet path:    Traffic Light → BACnet → SNE → Metasys   (BMS/control)
#   RabbitMQ path:  Traffic Light → RabbitMQ → InfluxDB → Grafana (analytics)
#
# Both paths run simultaneously. Adding RabbitMQ has no effect on BACnet.
#
# MESSAGE FORMAT:
# We use the same normalized format as the DAWS_BAS Protocol Gateway
# normalizer.py — this means Telegraf, InfluxDB, and Grafana handle this
# data identically to data coming from any other field device.
#
# RESILIENCE:
# If RabbitMQ is unreachable (not deployed, network issue, etc.),
# this file logs a warning and sets connected=False. The traffic light
# continues running normally — RabbitMQ publishing is non-critical.
#
# HOW IT FITS IN THE SYSTEM:
#   traffic_controller.py changes state.current
#       state.py detects the change and calls publisher.publish_state()
#           this file sends JSON to RabbitMQ exchange "daws.bas"
#               routing key: "point.traffic.red_light" etc.
#                   Telegraf picks it up → writes to InfluxDB
#                       Grafana shows it on dashboard
#
# =============================================================================

import pika      # RabbitMQ AMQP client library (pip install pika)
import json      # For converting Python dicts to JSON strings
import time      # For generating Unix millisecond timestamps
import logging   # For writing log messages
import os        # For reading environment variables

logger = logging.getLogger(__name__)


class TrafficLightPublisher:
    """
    Manages the RabbitMQ connection and publishes traffic light state changes.

    Used as a singleton — one instance created at the bottom of this file,
    imported and used by state.py and main.py.
    """

    def __init__(self):
        # Read connection settings from environment variables
        # On the LXC these are set in /etc/environment
        # Defaults point to the DAWS_BAS RabbitMQ LXC at 192.168.30.13
        self.host     = os.environ.get("RABBITMQ_HOST",     "192.168.30.13")
        self.user     = os.environ.get("RABBITMQ_USER",     "daws")
        self.password = os.environ.get("RABBITMQ_PASS",     "changeme")
        self.vhost    = os.environ.get("RABBITMQ_VHOST",    "bas")
        self.exchange = os.environ.get("RABBITMQ_EXCHANGE", "daws.bas")

        # Connection objects — None until connect() is called
        self.connection = None
        self.channel    = None

        # Whether we currently have a working RabbitMQ connection
        # If False, publish_state() skips silently so the traffic light keeps running
        self.connected  = False


    def connect(self):
        """
        Opens a connection to RabbitMQ and declares the exchange.
        Called once at startup from main.py.

        If RabbitMQ is unreachable, logs a warning and sets connected=False.
        The traffic light continues running without RabbitMQ.
        """
        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters  = pika.ConnectionParameters(
                host         = self.host,
                virtual_host = self.vhost,
                credentials  = credentials,
                heartbeat    = 60   # Send keep-alive ping every 60 seconds
                                    # Prevents the connection timing out between light changes
            )

            # Open the TCP connection to RabbitMQ
            self.connection = pika.BlockingConnection(parameters)

            # Open a channel within the connection
            # A channel is like a lane within the TCP connection
            self.channel = self.connection.channel()

            # Declare the exchange
            # Must match the exchange name used by DAWS_BAS (publisher.py)
            # durable=True means the exchange survives RabbitMQ restarts
            # If the exchange already exists with these settings, this is a no-op
            self.channel.exchange_declare(
                exchange      = self.exchange,
                exchange_type = "topic",    # Routes by routing key patterns
                durable       = True
            )

            self.connected = True
            logger.info(f"RabbitMQ connected: {self.host}/{self.vhost}/{self.exchange}")

        except Exception as e:
            self.connected = False
            logger.warning(f"RabbitMQ unavailable at {self.host} — running without it: {e}")


    def publish_state(self, light_state: str, running: bool):
        """
        Publishes the current traffic light state to RabbitMQ.

        Sends four messages — one per point — matching how the DAWS_BAS
        Protocol Gateway publishes BACnet binary values. Each light and the
        running flag gets its own message with its own routing key.

        Parameters:
            light_state - "red", "green", or "yellow"
            running     - True if the cycle is running, False if stopped

        Messages published:
            routing key: point.traffic.red_light    value: "active" or "inactive"
            routing key: point.traffic.yellow_light value: "active" or "inactive"
            routing key: point.traffic.green_light  value: "active" or "inactive"
            routing key: point.traffic.running      value: "active" or "inactive"

        Telegraf subscribes to "point.#" so it receives all four messages
        and writes them to InfluxDB with their timestamps.
        """

        # Skip silently if not connected — traffic light keeps running normally
        if not self.connected:
            return

        try:
            # Unix milliseconds timestamp — matches normalizer.py in DAWS_BAS
            timestamp = int(time.time() * 1000)

            # Four points to publish, matching the four BACnet objects on the device
            # "active"/"inactive" matches BACnet binary value convention
            points = {
                "red_light":    "active" if light_state == "red"    else "inactive",
                "yellow_light": "active" if light_state == "yellow" else "inactive",
                "green_light":  "active" if light_state == "green"  else "inactive",
                "running":      "active" if running                  else "inactive",
            }

            for point_name, value in points.items():

                # Normalized message — identical format to DAWS_BAS normalizer.py
                # This means InfluxDB stores this in the same schema as all other devices
                message = {
                    "protocol":   "traffic",
                    "device_id":  "traffic-light:3001",
                    "point_name": point_name,
                    "value":      value,
                    "unit":       "",
                    "timestamp":  timestamp,
                    "metadata": {
                        "bacnet_device_id": 3001,
                        "ip": "192.168.30.12"
                    }
                }

                # Routing key: point.<protocol>.<point_name>
                # e.g. "point.traffic.red_light"
                # Telegraf binding key "point.#" matches all of these
                routing_key = f"point.traffic.{point_name}"

                self.channel.basic_publish(
                    exchange    = self.exchange,
                    routing_key = routing_key,
                    body        = json.dumps(message),
                    properties  = pika.BasicProperties(
                        delivery_mode = 2,                  # Persistent message
                        content_type  = "application/json"
                    )
                )

            logger.debug(f"Published: state={light_state} running={running}")

        except Exception as e:
            # Publishing failed — likely connection dropped
            logger.warning(f"RabbitMQ publish failed: {e}")
            self.connected = False


    def disconnect(self):
        """Cleanly close the RabbitMQ connection on shutdown."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ disconnected")


# =============================================================================
# SINGLETON INSTANCE
# One shared publisher for the whole application.
# Import this in other files with:  from app.rabbitmq import publisher
# =============================================================================
publisher = TrafficLightPublisher()
