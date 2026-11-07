
import json
import requests
import queue
import threading
import paho.mqtt.client as mqtt

from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, ENGINE_URL
from validator import validate_message
from database import save_message, save_malformed_message
from stats import (
    record_received,
    record_validation,
    record_forwarded,
    record_failed
)


# Bounded queue prevents unlimited memory usage
message_queue = queue.Queue(maxsize=1000)

worker_thread = None
STOP_WORKER = object()


def forward_message(data):
    """Forward valid messages to the decision engine."""

    for attempt in range(4):  # Initial attempt + 3 retries
        try:
            response = requests.post(
                ENGINE_URL,
                json=data,
                timeout=5
            )

            response.raise_for_status()

            result = response.json()

            if result.get("ok") is True:
                print("Successfully forwarded to Part B!")
                record_forwarded()
                return True

            print("Engine did not acknowledge the message.")

        except requests.RequestException as error:
            print(f"Forwarding attempt {attempt + 1} failed: {error}")

        except ValueError as error:
            print(f"Invalid engine response: {error}")

    print("Forwarding failed after 3 retries.")
    record_failed()
    return False


def process_message(raw_payload):
    """Validate, store and forward a queued MQTT message."""

    try:
        payload = json.loads(raw_payload)

        print("\nMQTT MESSAGE RECEIVED")

        valid, reason = validate_message(payload)
        record_validation(valid, payload)

        print("Validation:", reason)

        saved = save_message(payload, valid, reason)

        if saved:
            print("Stored in Supabase:", valid)
        else:
            print("Could not store message in Supabase.")

        # Forward only valid messages successfully stored
        if valid and saved:
            forward_message(payload)

    except json.JSONDecodeError as error:
        print("\nMALFORMED JSON MESSAGE")
        print("Validation: Invalid JSON")

        record_validation(False)

        saved = save_malformed_message(
            raw_payload,
            f"Invalid JSON: {error}"
        )

        if saved:
            print("Malformed message stored in Supabase.")
        else:
            print("Could not store malformed message.")

    except Exception as error:
        print(f"Message processing error: {error}")


def background_worker():
    """Process MQTT messages outside the MQTT network callback."""

    print("Background message worker started.")

    while True:
        item = message_queue.get()

        try:
            if item is STOP_WORKER:
                return

            raw_payload = item
            process_message(raw_payload)

        finally:
            message_queue.task_done()


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to HiveMQ!")
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to: {MQTT_TOPIC}")
    else:
        print(f"MQTT connection failed: {reason_code}")


def on_message(client, userdata, message):
    """Receive MQTT messages and enqueue them for processing."""

    record_received()

    raw_payload = message.payload.decode(
        "utf-8",
        errors="replace"
    )

    try:
        message_queue.put_nowait(raw_payload)
        print("Message added to processing queue.")

    except queue.Full:
        print("WARNING: Processing queue full. Message dropped.")


def start_mqtt():
    global worker_thread

    worker_thread = threading.Thread(
        target=background_worker,
        daemon=True
    )

    worker_thread.start()

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="sentinel_ingestion_service"
    )

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connecting to {MQTT_BROKER}...")

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    return client


def stop_mqtt(client):
    """Stop MQTT reception and shut down the worker."""

    client.loop_stop()
    client.disconnect()

    if worker_thread and worker_thread.is_alive():
        try:
            message_queue.put(STOP_WORKER, timeout=2)
            worker_thread.join(timeout=5)
        except queue.Full:
            print("Worker queue is full; worker will stop with the process.")
