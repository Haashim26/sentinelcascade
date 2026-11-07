
from threading import Lock

stats = {
    "received": 0,
    "valid": 0,
    "invalid": 0,
    "forwarded": 0,
    "failed": 0,
    "last_message_ts": {}
}

stats_lock = Lock()


def record_received():
    with stats_lock:
        stats["received"] += 1


def record_validation(valid, data=None):
    with stats_lock:
        if valid:
            stats["valid"] += 1
        else:
            stats["invalid"] += 1

        if isinstance(data, dict):
            zone = data.get("zone")
            timestamp = data.get("ts")

            if (
                isinstance(zone, str)
                and zone.strip()
                and isinstance(timestamp, int)
                and not isinstance(timestamp, bool)
                and timestamp >= 0
            ):
                stats["last_message_ts"][zone] = timestamp


def record_forwarded():
    with stats_lock:
        stats["forwarded"] += 1


def record_failed():
    with stats_lock:
        stats["failed"] += 1


def get_stats():
    with stats_lock:
        return {
            **stats,
            "last_message_ts": dict(stats["last_message_ts"])
        }
