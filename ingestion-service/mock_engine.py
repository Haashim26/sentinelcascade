from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI(title="SentinelCascade Mock Decision Engine")

received_messages = []


@app.get("/health")
def health():
    return {
        "status": "running",
        "service": "Mock Decision Engine"
    }


@app.post("/ingest")
def ingest(data: dict):
    received_messages.append(data)

    print("\nMESSAGE RECEIVED FROM PART A")
    print("Zone:", data.get("zone"))
    print("Node:", data.get("node"))
    print("Timestamp:", data.get("ts"))

    return {
        "ok": True,
        "message": "Successfully received by mock engine"
    }


@app.get("/messages")
def get_messages():
    return {
        "total_received": len(received_messages),
        "messages": received_messages
    }