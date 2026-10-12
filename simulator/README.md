PART B: Data simulator (owner: Lalit Kishore)

Generates zone2 to zone4 scenarios (normal, false_alarm, genuine_event, silent_failure) in two modes: `mqtt` (publish to the broker) and `http` (POST to ENGINE_URL/ingest). Writes `scenarios.csv` with the ground truth for the experiment.

Milestone:
- [ ] B7 simulator with both modes, seeded random scenarios, parallel zones

Copy `.env.example` to `.env` to run locally.
