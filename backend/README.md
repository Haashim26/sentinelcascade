PART B: Decision engine service (owner: Lalit Kishore)

Receives messages on `POST /ingest`, runs the staged and baseline engines, keeps live state in Redis, logs stage changes to a Supabase `events` table, and exposes `/zones`, `/events`, `/override` and the `/ws` WebSocket. Calls the alert service on Stage 2 and 3.

Milestones:
- [ ] B1 FastAPI app with /health
- [ ] B2 POST /ingest
- [ ] B3 staged and baseline engines with pytest tests
- [ ] B4 Redis state + Postgres events
- [ ] B5 /zones, /events, /override, /ws
- [ ] B6 alert service calls
- [ ] B8 deployed on Render

Copy `.env.example` to `.env` to run locally.
