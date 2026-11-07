from fastapi import FastAPI
from mqtt_client import start_mqtt, stop_mqtt
from stats import get_stats
app = FastAPI(
    title="SentinelCascade Ingestion Service",
    description="Receives, validates and stores MQTT sensor messages",
    version="1.0.0"
)

mqtt_client = None


@app.on_event("startup")
def startup_event():
    global mqtt_client

    print("Starting SentinelCascade Ingestion Service...")
    mqtt_client = start_mqtt()


@app.on_event("shutdown")
def shutdown_event():
    global mqtt_client

    if mqtt_client:
        stop_mqtt(mqtt_client)

    print("Ingestion Service stopped.")


@app.get("/health")
def health():
    mqtt_connected = (
        mqtt_client is not None
        and mqtt_client.is_connected()
    )

    return {
        "status": "running",
        "mqtt_connected": mqtt_connected,
        "service": "SentinelCascade Ingestion Service"
    }


@app.get("/")
def home():
    return {
        "message": "SentinelCascade Ingestion Service is running"
    }

@app.get("/stats")
def statistics():
    return get_stats()