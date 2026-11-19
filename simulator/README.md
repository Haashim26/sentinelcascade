PART B: Data simulator (owner: Lalit Kishore)

`simulator.py` generates zone2 to zone4 scenarios: normal, false_alarm (one sensor 3 to 5 s), genuine_event (2 or 3 sensors for 20 to 40 s) and silent_failure (one sensor elevated 12 to 20 s, then the node stops sending). Seeded and reproducible; zones run in parallel in live modes. Writes `scenarios.csv` (ground truth).

    python simulator.py --mode offline --n 40 --seed 7 --out ../analysis   # fast, no network, also writes events.csv
    python simulator.py --mode http --n 6 --seed 1                         # real time, POST ENGINE_URL/ingest
    python simulator.py --mode mqtt --n 6 --seed 1                         # real time, via the broker and ingestion service

Use `offline` for the 40-scenario experiment (clean, repeatable). Use `http` or `mqtt` for the live demo; the `--gap` option (default 20 s) is the pause between scenarios on a zone, so use at least 150 for clean results after a silent_failure.
Settings come from `.env` (ENGINE_URL, MQTT_BROKER, MQTT_PORT, MQTT_PREFIX).
