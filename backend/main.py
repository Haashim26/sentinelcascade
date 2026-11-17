import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
import paho.mqtt.client as mqtt

# Free public test broker & channel name (we can swap these later if Haashim uses different ones)
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "sentinelcascade/sensors/#"

# Store the latest reading received for each zone
latest_readings = {}

# Runs automatically when we connect to the MQTT broker
def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected to MQTT Broker! Listening for sensor data...")
    client.subscribe(MQTT_TOPIC)

# Runs automatically every time a sensor message arrives
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
        zone_id = data.get("zone_id", "unknown")
        latest_readings[zone_id] = data
        print(f"New reading from {zone_id}: {data}")
    except Exception as e:
        print(f"Error reading message: {e}")

# Setup the MQTT listener
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Start listening when FastAPI turns on, and stop cleanly when it turns off
@asynccontextmanager
async def lifespan(app: FastAPI):
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
    yield
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

app = FastAPI(title="SentinelCascade Backend", lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "sentinelcascade-backend"}

@app.get("/latest")
def get_latest():
    return {"zones": latest_readings}