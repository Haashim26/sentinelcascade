
import math

REQUIRED_FIELDS = [
    "type",
    "zone",
    "node",
    "ts",
    "vibration",
    "rain",
    "temp_c",
    "elevated",
    "button",
    "simulated",
]


def validate_message(data):

    if not isinstance(data, dict):
        return False, "Message must be a JSON object"

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            return False, f"Missing field: {field}"

    # Check message type
    if data["type"] not in ["reading", "heartbeat"]:
        return False, "Invalid message type"

    # Check zone and node
    if not isinstance(data["zone"], str) or not data["zone"].strip():
        return False, "Zone must be a non-empty string"

    if not isinstance(data["node"], str) or not data["node"].strip():
        return False, "Node must be a non-empty string"

    # Check timestamp
    if (
        not isinstance(data["ts"], int)
        or isinstance(data["ts"], bool)
        or data["ts"] < 0
    ):
        return False, "Timestamp must be a non-negative integer"

    # Check sensor values
    for field in ["vibration", "rain"]:
        value = data[field]

        if not isinstance(value, int) or isinstance(value, bool):
            return False, f"{field} must be an integer"

        if not 0 <= value <= 4095:
            return False, f"{field} must be between 0 and 4095"

    # Check temperature
    temperature = data["temp_c"]

    if (
        not isinstance(temperature, (int, float))
        or isinstance(temperature, bool)
        or not math.isfinite(temperature)
    ):
        return False, "Temperature must be a finite number"

    # Check elevated object
    if not isinstance(data["elevated"], dict):
        return False, "Elevated must be an object"

    for field in ["vibration", "temp", "rain"]:
        if field not in data["elevated"]:
            return False, f"Missing elevated field: {field}"

        if not isinstance(data["elevated"][field], bool):
            return False, f"Elevated {field} must be boolean"

    # Check button and simulated flags
    if not isinstance(data["button"], bool):
        return False, "Button must be boolean"

    if not isinstance(data["simulated"], bool):
        return False, "Simulated must be boolean"

    # Check optional simulator metadata
    if "scenario" in data and data["scenario"] is not None:
        if not isinstance(data["scenario"], str):
            return False, "Scenario must be a string or null"

    if "label" in data and data["label"] is not None:
        if not isinstance(data["label"], str):
            return False, "Label must be a string or null"

    if "scenario_start_ts" in data and data["scenario_start_ts"] is not None:
        value = data["scenario_start_ts"]

        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return False, "Scenario start timestamp must be a non-negative integer or null"

    return True, "Valid message"
