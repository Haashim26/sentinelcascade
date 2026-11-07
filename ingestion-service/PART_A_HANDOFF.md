# SentinelCascade — Part A Handoff

## 1. Responsibility

Part A handles:
- ESP32 hardware and sensor data acquisition.
- Edge-side message generation.
- MQTT publishing and ingestion.
- Incoming message validation.
- Raw message storage in Supabase.
- Forwarding valid messages to the Part B decision engine.

## 2. System architecture

ESP32 + Sensors  
↓ MQTT  
HiveMQ Public Broker  
↓ MQTT Subscription  
Part A — FastAPI Ingestion Service (Render)  
↓  
Message Validation  
↓  
Supabase PostgreSQL (`raw_readings`)  
↓  
Part B Decision Engine (when configured)

## 3. Hardware

- ESP32
- MPU6050 vibration sensor
- DS18B20 temperature sensor
- Rain/moisture sensor
- Push button

## 4. MQTT configuration

- Broker: `broker.hivemq.com`
- Port: `1883`
- Topic: `sentinel-4821/zone/+/data`
- Real hardware zone: `zone1`

## 5. Ingestion service

**Deployment:** Render

**Base URL:**  
https://sentinelcascade.onrender.com

Endpoints:

| Endpoint | Purpose |
|---|---|
| `/` | Service information |
| `/health` | Health and MQTT connection status |
| `/stats` | Message processing statistics |

## 6. Database

Supabase project with a PostgreSQL table:

`public.raw_readings`

Stored fields:
- `id`
- `created_at`
- `zone`
- `message_type`
- `payload`
- `valid`
- `validation_reason`

Both valid and invalid messages are recorded. Malformed JSON messages are also stored with an explanatory validation reason.

## 7. Environment variables

The deployment requires these configuration variables:

- `MQTT_BROKER`
- `MQTT_PORT`
- `MQTT_TOPIC`
- `SUPABASE_URL`
- `SUPABASE_KEY`

Keep secret keys in environment variables. Never commit `.env` or secret keys to GitHub.

`ENGINE_URL` can be configured when the actual Part B service is ready.

## 8. Testing completed

| Test | Result |
|---|---|
| ESP32 MQTT publishing | Passed |
| HiveMQ subscription | Passed |
| Render MQTT connection | Passed |
| JSON validation | Passed |
| Invalid message handling | Passed |
| Malformed JSON handling | Passed |
| Supabase storage | Passed |
| Health endpoint | Passed |
| Stats endpoint | Passed |
| Sensor reading ingestion | Passed |
| UptimeRobot monitoring setup | Created |

A real sensor record was verified in Supabase with:
- `type`: `reading`
- `zone`: `zone1`
- `vibration`: `273`
- `elevated.vibration`: `true`
- `simulated`: `false`

## 9. Part B integration status

The ingestion service currently stores valid messages in Supabase.

Forwarding to Part B is optional and remains unconfigured until the actual decision engine URL is available.

Once Part B is deployed, configure `ENGINE_URL` with its public `/ingest` endpoint and verify the response acknowledgement.

## 10. Important deployment notes

- Render free instances can sleep after inactivity.
- UptimeRobot monitors the `/health` endpoint.
- The MQTT service reconnects to the configured broker when started.
- The current processing queue is in memory; it is not durable across process restarts.
- Message statistics are in memory and reset when the service restarts.

## 11. Team handoff

Part A provides the MQTT ingestion service, database storage and health/statistics endpoints.

Part B should integrate using the agreed `/ingest` contract. Any changes to the shared MQTT topic or JSON message format must be coordinated with the team.
