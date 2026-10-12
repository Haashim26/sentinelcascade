# SentinelCascade Shared Contract

This is the single source of truth for how the three parts talk to each other. All three teammates must follow it exactly. If anything needs to change, agree it together first, update this file, and tell everyone to update their Claude chats.

```text
PROJECT: SentinelCascade, a staged-confidence emergency alert system (college cloud and edge computing project, 3-person team).
HOW IT WORKS: An ESP32 node reads a vibration sensor, a DS18B20 temperature sensor and a rain sensor. It filters noise on the device (edge), then sends JSON messages over MQTT. A cloud ingestion service validates and stores every message and forwards valid ones to a decision engine service, which decides an alert stage (0 to 3) for each zone. Stage 2 and 3 call an alert service that sends SMS. An officer dashboard shows all zones live.
FLOW: ESP32 and simulator -> MQTT broker -> [Part A] ingestion service -> [Part B] decision engine -> [Part C] alert service and dashboard.
TEAM: Part A = hardware and edge firmware, plus the cloud ingestion service. Part B = cloud decision engine service, plus the data simulator. Part C = alert service (SMS), officer dashboard, experiment analysis. Each part owns one deployed cloud service with its own free database or store, so the work is equal.

SHARED CONTRACT (do not change):
MQTT: broker broker.hivemq.com, port 1883, no password (public demo broker, so never send personal data; if it is down, all three switch together to broker.emqx.io port 1883). Topic: sentinel-4821/zone/<zone_id>/data . Zones: zone1 = the real ESP32, zone2 to zone4 = simulated.
MESSAGE: one JSON object per MQTT message. Example:
{"type":"reading","zone":"zone1","node":"node1","ts":1760000000,"vibration":1240,"temp_c":26.5,"rain":3890,"elevated":{"vibration":false,"temp":false,"rain":true},"button":false,"simulated":false,"scenario":null,"label":null,"scenario_start_ts":null}
Fields: type is reading or heartbeat; ts is unix seconds; vibration and rain are raw ESP32 analog values 0-4095; elevated says which sensor types the edge filter flagged; button is true when an officer pressed the confirm button; simulated is true for fake nodes; scenario, label (normal, genuine_event or false_alarm) and scenario_start_ts are filled only by the simulator and are null on the real node. A node sends a reading every second while any sensor is elevated and a heartbeat every 30 seconds otherwise.
INGESTION SERVICE API (Part A builds, deployed on Render, own Supabase table raw_readings): subscribes to sentinel-4821/zone/+/data; checks every message against the message format (required fields, types, ranges); stores every message with valid true or false and a reason; forwards valid messages to the engine with POST {ENGINE_URL}/ingest (3 retries, then log the failure). GET /health; GET /stats returns counts of received, valid, invalid, forwarded and failed, plus last_message_ts per zone.
STAGE RULES (engine): SUSTAINED_SECONDS=10 (one sensor type elevated continuously this long is sustained), DECAY_SECONDS=15, SILENCE_SECONDS=90.
Stage 0 Normal: no sensor type elevated.
Stage 1 Local Notice: something is elevated but it is not sustained and only one sensor type is elevated. Log only, show on dashboard.
Stage 2 Corroborated Warning: any sensor type sustained OR two or more sensor types elevated at the same time. SMS to officials only.
Stage 3 Full Alert: (sustained AND two or more sensor types elevated at the same time) OR button is true OR an officer override of escalate. SMS to all residents and officials, automatically, once per entry into Stage 3.
Decay: after DECAY_SECONDS with nothing elevated, the stage drops one level, repeating until 0.
Silence: if a zone was at Stage 1 or higher and sends nothing for SILENCE_SECONDS, count the silence as one extra elevated sensor type.
The engine runs two engines on every message: staged (the rules above) and baseline (Stage 3 immediately when any sensor type is elevated). Both log every stage change so the team can compare false alarms and speed.
ENGINE SERVICE API (Part B builds; it does NOT read MQTT, it only receives POST /ingest): POST /ingest (body = the message JSON, returns ok true); GET /health; GET /zones (zone, stage, baseline_stage, elevated_types, score 0-100, last_seen_ts, silent, simulated); GET /events?limit=100 (id, ts, zone, engine, from_stage, to_stage, reason, scenario, label, scenario_start_ts); POST /override (zone, action = escalate, suppress or clear); WebSocket /ws pushes the full /zones list on any change. When the staged engine enters Stage 2 or 3 the engine calls the alert service.
ALERT SERVICE API (Part C builds, Part B calls): POST /alert (zone, stage 2 or 3, message, ts) sends the SMS and logs it; GET /alerts lists alerts sent.
RULES: free tiers only. Never paste passwords, API keys or tokens into this chat; keep them in a .env file listed in .gitignore. If you think the contract must change, tell me clearly so I can agree it with my teammates first.
```
