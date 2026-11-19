"""C5 experiment analysis: staged engine vs single-threshold baseline.

Usage
  python analyze.py --scenarios scenarios.csv --events events.csv
  python analyze.py --scenarios scenarios.csv --events-url https://<engine>.onrender.com/events?limit=5000

Outputs: results.csv, per_scenario.csv, false_alarms.png, time_to_alert.png
Definitions
  false alarm   : Stage 3 entered during a scenario labelled false_alarm or normal
  missed event  : scenario labelled genuine_event where the engine never reached Stage 3
  time to Stage 3 : first Stage 3 event ts minus scenario_start_ts (genuine events only)
"""
import argparse, json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument("--scenarios", default="scenarios.csv")
ap.add_argument("--events", default=None)
ap.add_argument("--events-url", default=None)
a = ap.parse_args()

sc = pd.read_csv(a.scenarios)
if a.events_url:
    import requests
    ev = pd.DataFrame(requests.get(a.events_url, timeout=20).json())
else:
    ev = pd.read_csv(a.events or "events.csv")

rows = []
for _, s in sc.iterrows():
    for eng in ["staged", "baseline"]:
        hit = ev[(ev["engine"] == eng) & (ev["to_stage"] == 3) & (ev["zone"] == s["zone"])
                 & (ev["scenario_start_ts"] == s["start_ts"])]
        reached = not hit.empty
        t3 = (hit["ts"].min() - s["start_ts"]) if reached else None
        genuine = s["label"] == "genuine_event"
        rows.append({"scenario_id": s["scenario_id"], "zone": s["zone"], "scenario": s["scenario"],
                     "label": s["label"], "engine": eng, "reached_stage3": reached,
                     "false_alarm": reached and not genuine,
                     "missed": (not reached) and genuine,
                     "time_to_stage3_s": t3 if genuine else None})
per = pd.DataFrame(rows)
per.to_csv("per_scenario.csv", index=False)

res = []
for eng, g in per.groupby("engine"):
    non_genuine = g[g["label"] != "genuine_event"]
    genuine = g[g["label"] == "genuine_event"]
    t = genuine["time_to_stage3_s"].dropna()
    res.append({"engine": eng, "scenarios": len(g),
                "non_genuine_scenarios": len(non_genuine), "false_alarms": int(g["false_alarm"].sum()),
                "false_alarm_rate_%": round(100 * g["false_alarm"].sum() / max(1, len(non_genuine)), 1),
                "genuine_scenarios": len(genuine), "missed_events": int(g["missed"].sum()),
                "median_time_to_stage3_s": float(t.median()) if len(t) else None,
                "mean_time_to_stage3_s": round(float(t.mean()), 1) if len(t) else None,
                "max_time_to_stage3_s": float(t.max()) if len(t) else None})
res = pd.DataFrame(res).set_index("engine").loc[["baseline", "staged"]].reset_index()
res.to_csv("results.csv", index=False)
print(res.to_string(index=False))

by_type = per[per["label"] == "genuine_event"].groupby(["scenario", "engine"])["time_to_stage3_s"].median().unstack()
print("\nMedian time to Stage 3 by genuine scenario type (s):\n", by_type)

colors = {"baseline": "#d9534f", "staged": "#2a7f62"}
fig, ax = plt.subplots(figsize=(5, 4))
ax.bar(res["engine"], res["false_alarms"], color=[colors[e] for e in res["engine"]])
for i, v in enumerate(res["false_alarms"]): ax.text(i, v + 0.1, str(v), ha="center", fontsize=12)
ax.set_ylabel("False Stage 3 alerts"); ax.set_title("False alarms per engine (H1)")
plt.tight_layout(); plt.savefig("false_alarms.png", dpi=200); plt.close()

fig, ax = plt.subplots(figsize=(6, 4))
data = [per[(per.engine == e) & per.time_to_stage3_s.notna()]["time_to_stage3_s"] for e in res["engine"]]
ax.boxplot(data, patch_artist=True, boxprops=dict(facecolor="#cfe8dd"), medianprops=dict(color="black"))
ax.set_xticks(range(1, len(res) + 1)); ax.set_xticklabels(list(res["engine"]))
ax.set_ylabel("Seconds from event start to Stage 3"); ax.set_title("Time to alert, genuine events (H2)")
plt.tight_layout(); plt.savefig("time_to_alert.png", dpi=200); plt.close()
print("\nSaved results.csv, per_scenario.csv, false_alarms.png, time_to_alert.png")
