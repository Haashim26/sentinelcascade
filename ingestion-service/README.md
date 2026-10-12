PART A: Ingestion service (owner: Haashim Aslam)

Cloud service that subscribes to the MQTT topic, validates every message against `docs/CONTRACT.md`, stores all messages in a Supabase `raw_readings` table, and forwards valid ones to the engine (`POST ENGINE_URL/ingest`).

Endpoints: `GET /health`, `GET /stats`.

Milestones:
- [ ] A6 service running locally with validation, raw storage and forwarding
- [ ] A7 deployed on Render, kept awake with an uptime pinger

Copy `.env.example` to `.env` to run locally.
