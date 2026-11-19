"""SentinelCascade decision engines (pure Python, no web code).
Time is always passed in (unix seconds), so the logic is deterministic and testable.
Rules follow docs/CONTRACT.md exactly."""
from dataclasses import dataclass, field

SUSTAINED_SECONDS = 10
DECAY_SECONDS = 15
SILENCE_SECONDS = 90
TYPES = ("vibration", "temp", "rain")


@dataclass
class Zone:
    zone: str
    stage: int = 0                # staged engine
    baseline_stage: int = 0       # baseline engine
    since: dict = field(default_factory=dict)   # sensor type -> ts it became elevated (continuous)
    elevated: set = field(default_factory=set)  # last known elevated types
    button: bool = False
    last_ts: int = 0              # ts of last message
    last_elev_ts: int = 0         # last time anything was elevated
    last_change_ts: int = 0       # last staged stage change
    silent: bool = False
    simulated: bool = False
    override: str = None          # None | "escalate" | "suppress"
    scenario: str = None
    label: str = None
    scenario_start_ts: int = None
    score: int = 0


class Engine:
    def __init__(self):
        self.zones = {}
        self.events = []
        self._next_id = 1

    def _log(self, z, ts, engine, old, new, reason):
        ev = {"id": self._next_id, "ts": ts, "zone": z.zone, "engine": engine,
              "from_stage": old, "to_stage": new, "reason": reason,
              "scenario": z.scenario, "label": z.label,
              "scenario_start_ts": z.scenario_start_ts}
        self._next_id += 1
        self.events.append(ev)
        return ev

    @staticmethod
    def _sustained(z):
        # sustained is judged at the last message time, so a node that went silent
        # does not become "sustained" just because the clock keeps running
        return any(z.last_ts - t0 >= SUSTAINED_SECONDS for k, t0 in z.since.items() if k in z.elevated)

    def _target(self, z):
        n = len(z.elevated) + (1 if z.silent else 0)   # silence = one extra elevated type
        sus = self._sustained(z)
        extra = " (incl. silence)" if z.silent else ""
        if z.override == "suppress":
            return 0, "officer override: suppress"
        if z.override == "escalate":
            return 3, "officer override: escalate"
        if z.button:
            return 3, "officer pressed confirm button"
        if sus and n >= 2:
            return 3, "sustained and %d sensor types elevated%s" % (n, extra)
        if sus:
            return 2, "one sensor type sustained %d s" % SUSTAINED_SECONDS
        if n >= 2:
            return 2, "%d sensor types elevated together%s" % (n, extra)
        if n == 1:
            return 1, "one sensor type elevated, not sustained"
        return 0, "nothing elevated"

    def _score(self, z):
        if z.override == "suppress":
            return 0
        s = 20 * min(3, len(z.elevated) + (1 if z.silent else 0))
        if self._sustained(z): s += 20
        if z.button or z.override == "escalate": s += 20
        return min(100, s)

    def _apply(self, z, now):
        out = []
        target, reason = self._target(z)
        if target > z.stage or (z.override == "suppress" and z.stage != 0):
            out.append(self._log(z, now, "staged", z.stage, target, reason))
            z.stage, z.last_change_ts = target, now
        elif (target < z.stage and not z.elevated and not z.button and not z.silent
              and now - max(z.last_elev_ts, z.last_change_ts) >= DECAY_SECONDS):
            out.append(self._log(z, now, "staged", z.stage, z.stage - 1,
                                 "decay: nothing elevated for %d s" % DECAY_SECONDS))
            z.stage -= 1
            z.last_change_ts = now
        z.score = self._score(z)
        return out

    def process(self, msg):
        """Handle one validated message. Returns the list of new events."""
        zid, ts = msg["zone"], int(msg["ts"])
        z = self.zones.setdefault(zid, Zone(zid, last_ts=ts, last_change_ts=ts))
        z.simulated = bool(msg.get("simulated"))
        z.scenario, z.label = msg.get("scenario"), msg.get("label")
        z.scenario_start_ts = msg.get("scenario_start_ts")
        z.last_ts = ts
        z.silent = False                                   # a message ends silence
        el = {k for k in TYPES if msg["elevated"].get(k)}
        for k in TYPES:                                    # track continuous elevation
            if k in el: z.since.setdefault(k, ts)
            else: z.since.pop(k, None)
        z.elevated, z.button = el, bool(msg.get("button"))
        if el or z.button: z.last_elev_ts = ts
        out = self._apply(z, ts)
        new_b = 3 if (el or z.button) else 0               # baseline: Stage 3 on any elevation
        if new_b != z.baseline_stage:
            out.append(self._log(z, ts, "baseline", z.baseline_stage, new_b,
                                 "any sensor elevated" if new_b else "nothing elevated"))
            z.baseline_stage = new_b
        return out

    def tick(self, now):
        """Call about once a second: silence detection and decay. Returns new events."""
        out = []
        for z in self.zones.values():
            if not z.silent and z.stage >= 1 and now - z.last_ts >= SILENCE_SECONDS:
                z.silent = True
            out += self._apply(z, now)
        return out

    def set_override(self, zone, action, now):
        z = self.zones.setdefault(zone, Zone(zone, last_ts=now, last_change_ts=now))
        z.override = None if action == "clear" else action
        return self._apply(z, now)

    def snapshot(self):
        res = [{"zone": z.zone, "stage": z.stage, "baseline_stage": z.baseline_stage,
                "elevated_types": sorted(z.elevated) + (["silence"] if z.silent else []),
                "score": z.score, "last_seen_ts": z.last_ts, "silent": z.silent,
                "simulated": z.simulated, "override": z.override}
               for z in self.zones.values()]
        return sorted(res, key=lambda d: d["zone"])
