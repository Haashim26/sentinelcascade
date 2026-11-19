PART B: Decision engine service (owner: Lalit Kishore)

Files
- `engine.py`: staged and baseline logic, no web code
- `test_engine.py`: 12 tests (spike stays Stage 1, two sensors reach Stage 3, button, decay, silence, baseline, overrides)
- `main.py`: FastAPI service with POST /ingest, /health, /zones, /events, /override, /ws
- `schema.sql`: optional events table for Supabase

Run locally
    pip install -r requirements.txt
    uvicorn main:app --port 9000
Run the tests: `python -m pytest -q`

Deploy on Render (free)
- Root Directory `backend`, Build `pip install -r requirements.txt`, Start `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment: ALERT_URL (alert service base URL), optional DATABASE_URL
- In the ingestion service set ENGINE_URL to `https://<this-service>.onrender.com/ingest`

Rules as implemented
- sustained: one sensor type elevated continuously for 10 s, judged at the last message time
- decay: one stage down per 15 s with nothing elevated
- silence: a zone at Stage 1 or higher with no message for 90 s counts one extra elevated type
- baseline engine: Stage 3 as soon as any sensor type or the button is on, back to 0 when clear
- alerts: one call per upward entry into Stage 2 or 3; a failed call is logged and never crashes the engine
