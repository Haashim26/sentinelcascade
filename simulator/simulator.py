"""SentinelCascade data simulator (zone2 to zone4).

Modes
  offline : no network, virtual clock; runs the real engine in-process (fast, used for the experiment)
  http    : real time, POST {ENGINE_URL}/ingest
  mqtt    : real time, publish to broker (topic <prefix>/zone/<zone>/data), the ingestion service picks it up

Examples
  python simulator.py --mode offline --n 40 --seed 7
  python simulator.py --mode http --n 6 --seed 1
  python simulator.py --mode mqtt --n 6 --seed 1

Writes scenarios.csv (ground truth) and, in offline mode, events.csv (engine events).
"""
import argparse, csv, os, random, sys, threading, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

SCENARIOS = ["normal", "false_alarm", "genuine_event", "silent_failure"]
LABEL = {"normal": "normal", "false_alarm": "false_alarm",
         "genuine_event": "genuine_event", "silent_failure": "genuine_event"}
SENSORS = ["vibration", "temp", "rain"]
ZONES = ["zone2", "zone3", "zone4"]


def make_msg(zone, ts, elevated, scenario, start_ts, kind=None):
    """One contract-format message. `elevated` is a set of sensor names."""
    anyel = bool(elevated)
    vib = random.randint(1500, 4000) if "vibration" in elevated else random.randint(5, 60)
    rain = random.randint(900, 2500) if "rain" in elevated else random.randint(3600, 4000)
    temp = round(random.uniform(36, 44), 1) if "temp" in elevated else round(random.uniform(28, 31), 1)
    return {"type": kind or ("reading" if anyel else "heartbeat"), "zone": zone, "node": zone.replace("zone", "sim"),
            "ts": ts, "vibration": vib, "temp_c": temp, "rain": rain,
            "elevated": {s: (s in elevated) for s in SENSORS}, "button": False, "simulated": True,
            "scenario": scenario, "label": LABEL[scenario], "scenario_start_ts": start_ts}


def build(scenario, zone, start_ts, rng):
    """Return a list of (offset_seconds, message) for one scenario."""
    m = lambda off, el: (off, make_msg(zone, start_ts + off, el, scenario, start_ts))
    out = []
    if scenario == "normal":
        for off in range(0, rng.randint(40, 70), 30):
            out.append(m(off, set()))
    elif scenario == "false_alarm":                      # one sensor spikes 3 to 5 s
        s, d = rng.choice(SENSORS), rng.randint(3, 5)
        out += [m(o, {s}) for o in range(d)]
        out.append(m(d + rng.randint(1, 5), set()))       # node reports clear shortly after
    elif scenario == "genuine_event":                    # two sensors stay elevated > 15 s
        pair, d = set(rng.sample(SENSORS, rng.choice([2, 2, 3]))), rng.randint(20, 40)
        out += [m(o, pair) for o in range(d)]
        out.append(m(d + rng.randint(1, 5), set()))
    elif scenario == "silent_failure":                   # sensor elevated, then the node stops sending
        s, d = rng.choice(SENSORS), rng.randint(12, 20)
        out += [m(o, {s}) for o in range(d)]
    return out


def plan(n, seed):
    rng = random.Random(seed)
    random.seed(seed)                                    # sensor values reproducible too
    return [(i, rng.choice(SCENARIOS), ZONES[i % len(ZONES)]) for i in range(n)], rng


# ---------------- offline ----------------
def run_offline(n, seed, out_dir):
    from engine import Engine
    items, rng = plan(n, seed)
    base, rows, all_events = 1_760_000_000, [], []
    for i, scenario, zone in items:
        start = base + i * 1000                          # unique start per scenario
        msgs = build(scenario, zone, start, rng)
        eng, last = Engine(), msgs[-1][1]["ts"]
        mi = 0
        for t in range(start, last + 150):               # keep ticking past 90 s silence and decay
            while mi < len(msgs) and msgs[mi][1]["ts"] == t:
                eng.process(msgs[mi][1]); mi += 1
            eng.tick(t)
        all_events += eng.events
        rows.append({"scenario_id": i + 1, "zone": zone, "scenario": scenario, "label": LABEL[scenario],
                     "start_ts": start, "end_ts": last})
    for k, ev in enumerate(all_events, 1):
        ev["id"] = k
    write_csv(os.path.join(out_dir, "scenarios.csv"), rows)
    write_csv(os.path.join(out_dir, "events.csv"), all_events)
    print("offline run: %d scenarios, %d events" % (len(rows), len(all_events)))


# ---------------- live (real time) ----------------
def run_live(mode, n, seed, out_dir, gap):
    items, rng = plan(n, seed)
    engine_url = os.getenv("ENGINE_URL", "http://localhost:9000").rstrip("/")
    prefix = os.getenv("MQTT_PREFIX", "sentinel-4821")
    send = None
    if mode == "http":
        import requests
        send = lambda msg: requests.post(engine_url + "/ingest", json=msg, timeout=5)
    else:
        import json
        import paho.mqtt.client as mqtt
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            client = mqtt.Client()
        client.connect(os.getenv("MQTT_BROKER", "broker.hivemq.com"), int(os.getenv("MQTT_PORT", "1883")), 60)
        client.loop_start()
        send = lambda msg: client.publish("%s/zone/%s/data" % (prefix, msg["zone"]), json.dumps(msg))
    rows, lock = [], threading.Lock()

    def zone_worker(zone, my_items):                     # zones run in parallel, scenarios in sequence
        for i, scenario in my_items:
            start = int(time.time())
            msgs = build(scenario, zone, start, rng_for[i])
            t0 = time.time()
            for off, msg in msgs:
                time.sleep(max(0, t0 + off - time.time()))
                msg["ts"] = int(time.time())             # live clock
                try: send(msg)
                except Exception as e: print("send failed:", e)
            with lock:
                rows.append({"scenario_id": i + 1, "zone": zone, "scenario": scenario, "label": LABEL[scenario],
                             "start_ts": start, "end_ts": int(time.time())})
            time.sleep(gap)                              # let the zone settle (silent_failure needs ~100 s)

    rng_for = {i: random.Random(seed * 1000 + i) for i, _, _ in items}
    threads = []
    for z in ZONES:
        mine = [(i, s) for i, s, zz in items if zz == z]
        th = threading.Thread(target=zone_worker, args=(z, mine)); th.start(); threads.append(th)
    for th in threads: th.join()
    rows.sort(key=lambda r: r["scenario_id"])
    write_csv(os.path.join(out_dir, "scenarios.csv"), rows)
    print("live run finished; scenarios.csv written. Download /events from the engine for the analysis.")


def write_csv(path, rows):
    if not rows: return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["offline", "http", "mqtt"], default="offline")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=".")
    ap.add_argument("--gap", type=int, default=20, help="seconds between scenarios in live modes")
    a = ap.parse_args()
    if a.mode == "offline": run_offline(a.n, a.seed, a.out)
    else: run_live(a.mode, a.n, a.seed, a.out, a.gap)
