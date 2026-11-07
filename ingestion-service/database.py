from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY


# Create Supabase connection
supabase = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )



def save_message(data, valid, reason):
    """Store a parsed MQTT message with its validation result."""

    if supabase is None:
        print("Supabase connection is not configured.")
        return False

    try:
        record = {
            "zone": data.get("zone") if isinstance(data, dict) else None,
            "message_type": data.get("type", "unknown") if isinstance(data, dict) else "unknown",
            "payload": data,
            "valid": valid,
            "validation_reason": reason
        }

        supabase.table("raw_readings").insert(record).execute()

        print("Message saved to Supabase.")
        return True

    except Exception as error:
        print(f"Database error: {error}")
        return False


def save_malformed_message(raw_payload, reason):
    """Store the original text of a message that is not valid JSON."""

    if supabase is None:
        print("Supabase connection is not configured.")
        return False

    try:
        record = {
            "zone": None,
            "message_type": "malformed_json",
            "payload": {"raw": raw_payload},
            "valid": False,
            "validation_reason": reason
        }

        supabase.table("raw_readings").insert(record).execute()

        print("Malformed message saved to Supabase.")
        return True

    except Exception as error:
        print(f"Database error: {error}")
        return False
