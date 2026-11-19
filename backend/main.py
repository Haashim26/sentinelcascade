"""SentinelCascade decision engine service (Part B).
Receives POST /ingest from the ingestion service, runs the staged and baseline engines,
exposes /zones /events /override /ws and calls the alert service on Stage 2 and 3."""
import os, time, asyncio, threading, logging
from contextlib import asynccontextmanager
from typing import Literal

import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from engine import Engine

load_dotenv()
log = logging.getLogger("engine")
logging.basicConfig(level=logging.INFO)

ALERT_URL = os.getenv("ALERT_URL", "").rstrip("/")          # e.g. https://sential-alert-service.onrender.com
DATABASE_URL = os.getenv("DATABASE_URL", "")                # optional: Supabase Postgres for the events table

engine = Engine()
lock = threading.Lock()
clients = set()


# ---------- side effects (never allowed to crash the engine) ----------
def send_alert(ev):
    if not ALERT_URL:
        log.info("ALERT_URL not set, skipping alert for %s stage %s", ev["zone"], ev["to_stage"])
        return
    text = ("SentinelCascade FULL ALERT in %s: take protective action." if ev["to_stage"] == 3
            else "SentinelCascade WARNING in %s: officials please verify.") % ev["zone"]
    try:
        requests.post(ALERT_URL + "/alert", timeout=3,
                      json={"zone": ev["zone"], "stage": ev["to_stage"], "message": text, "ts": ev["ts"]}).raise_for_status()
    except Exception as e:
        log.warning("alert call failed: %s", e)


def store_event(ev):
    """Optional: insert into Supabase table events (see schema.sql). Untested without a database."""
    if not DATABASE_URL:
        return
    try:
        import psycopg2
        with psycopg2.connect(DATABASE_URL, connect_timeout=3) as c, c.cursor() as cur:
            cur.execute("insert into events (ts,zone,engine,from_stage,to_stage,reason,scenario,label,scenario_start_ts)"
                        " values (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (ev["ts"], ev["zone"], ev["engine"], ev["from_stage"], ev["to_stage"], ev["reason"],
                         ev["scenario"], ev["label"], ev["scenario_start_ts"]))
    except Exception as e:
        log.warning("store_event failed: %s", e)


def side_effects(events):
    for ev in events:
        threading.Thread(target=store_event, args=(ev,), daemon=True).start()
        if ev["engine"] == "staged" and ev["to_stage"] > ev["from_stage"] and ev["to_stage"] in (2, 3):
            threading.Thread(target=send_alert, args=(ev,), daemon=True).start()


async def broadcast():
    with lock:
        data = engine.snapshot()
    for ws in list(clients):
        try:
            await ws.send_json(data)
        except Exception:
            clients.discard(ws)


async def tick_loop():
    while True:
        await asyncio.sleep(1)
        with lock:
            evs = engine.tick(int(time.time()))
        if evs:
            side_effects(evs)
            await broadcast()


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(tick_loop())
    yield
    task.cancel()


app = FastAPI(title="SentinelCascade Decision Engine", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Override(BaseModel):
    zone: str
    action: Literal["escalate", "suppress", "clear"]


@app.get("/health")
def health():
    return {"status": "running", "service": "SentinelCascade Decision Engine", "zones": len(engine.zones),
            "alerts": bool(ALERT_URL), "events_db": bool(DATABASE_URL)}


@app.post("/ingest")
async def ingest(msg: dict):
    try:
        with lock:
            evs = engine.process(msg)
    except Exception as e:                      # bad message must not kill the service
        log.warning("bad message: %s", e)
        raise HTTPException(status_code=422, detail="message does not match the contract")
    if evs:
        side_effects(evs)
    await broadcast()
    return {"ok": True}


@app.get("/zones")
def zones():
    with lock:
        return engine.snapshot()


@app.get("/events")
def events(limit: int = 100):
    with lock:
        return list(reversed(engine.events[-max(1, min(limit, 5000)):]))


@app.post("/override")
async def override(o: Override):
    with lock:
        evs = engine.set_override(o.zone, o.action, int(time.time()))
    side_effects(evs)
    await broadcast()
    return {"ok": True, "zone": o.zone, "action": o.action}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        await websocket.send_json(engine.snapshot())
        while True:
            await websocket.receive_text()      # keep the connection open
    except WebSocketDisconnect:
        clients.discard(websocket)
