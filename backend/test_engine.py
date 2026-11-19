from engine import Engine, SUSTAINED_SECONDS, DECAY_SECONDS, SILENCE_SECONDS

T0 = 1_760_000_000

def msg(ts, vib=False, temp=False, rain=False, button=False, zone="zone2", kind=None):
    anyel = vib or temp or rain
    return {"type": kind or ("reading" if anyel or button else "heartbeat"), "zone": zone, "node": "n", "ts": ts,
            "vibration": 0, "temp_c": 25, "rain": 0,
            "elevated": {"vibration": vib, "temp": temp, "rain": rain},
            "button": button, "simulated": True, "scenario": None, "label": None, "scenario_start_ts": None}

def run(e, msgs, until):
    """feed messages in time order and tick every second up to `until`"""
    msgs = sorted(msgs, key=lambda m: m["ts"]); i = 0
    for t in range(msgs[0]["ts"], until + 1):
        while i < len(msgs) and msgs[i]["ts"] == t:
            e.process(msgs[i]); i += 1
        e.tick(t)
    return e

def z(e): return e.zones["zone2"]

def test_brief_spike_stays_stage1():
    e = run(Engine(), [msg(T0 + s, vib=True) for s in range(4)] + [msg(T0 + 4)], T0 + 8)
    assert max(ev["to_stage"] for ev in e.events if ev["engine"] == "staged") == 1
    assert z(e).baseline_stage == 0 and any(ev["engine"] == "baseline" and ev["to_stage"] == 3 for ev in e.events)

def test_two_sensors_together_is_stage2_then_3_when_sustained():
    e = run(Engine(), [msg(T0 + s, vib=True, rain=True) for s in range(15)], T0 + 14)
    st = [(ev["ts"] - T0, ev["to_stage"]) for ev in e.events if ev["engine"] == "staged"]
    assert st == [(0, 2), (SUSTAINED_SECONDS, 3)]

def test_one_sensor_sustained_is_stage2_only():
    e = run(Engine(), [msg(T0 + s, vib=True) for s in range(30)], T0 + 29)
    assert z(e).stage == 2

def test_button_gives_stage3_immediately():
    e = Engine(); e.process(msg(T0, button=True))
    assert z(e).stage == 3

def test_decay_one_level_per_15s():
    e = run(Engine(), [msg(T0 + s, vib=True, rain=True) for s in range(12)] + [msg(T0 + 12)], T0 + 12 + 3 * DECAY_SECONDS + 2)
    downs = [(ev["ts"] - T0, ev["to_stage"]) for ev in e.events if ev["engine"] == "staged" and "decay" in ev["reason"]]
    assert [s for _, s in downs] == [2, 1, 0]
    assert downs[0][0] >= 12 + DECAY_SECONDS - 1 and z(e).stage == 0

def test_silence_counts_as_extra_type_and_escalates():
    e = run(Engine(), [msg(T0 + s, vib=True) for s in range(12)], T0 + 11 + SILENCE_SECONDS + 1)
    assert z(e).silent and z(e).stage == 3     # sustained + silence = 2 types
    assert "silence" in e.snapshot()[0]["elevated_types"]

def test_silence_after_brief_spike_gives_stage2():
    e = run(Engine(), [msg(T0, vib=True), msg(T0 + 1, vib=True)], T0 + 1 + SILENCE_SECONDS + 1)
    assert z(e).stage == 2

def test_no_silence_alarm_for_normal_zone():
    e = run(Engine(), [msg(T0)], T0 + 300)
    assert z(e).stage == 0 and not z(e).silent

def test_message_ends_silence():
    e = run(Engine(), [msg(T0, vib=True)], T0 + SILENCE_SECONDS + 1)
    assert z(e).silent
    e.process(msg(T0 + SILENCE_SECONDS + 5)); assert not z(e).silent

def test_baseline_fires_immediately_and_clears():
    e = Engine(); e.process(msg(T0, temp=True)); assert z(e).baseline_stage == 3 and z(e).stage == 1
    e.process(msg(T0 + 2)); assert z(e).baseline_stage == 0

def test_override_escalate_suppress_clear():
    e = Engine(); e.process(msg(T0))
    e.set_override("zone2", "escalate", T0 + 1); assert z(e).stage == 3
    e.set_override("zone2", "suppress", T0 + 2); assert z(e).stage == 0
    e.process(msg(T0 + 3, vib=True, rain=True, button=True)); assert z(e).stage == 0
    e.set_override("zone2", "clear", T0 + 4); assert z(e).stage == 3     # button still pressed

def test_sustained_resets_when_sensor_drops():
    e = run(Engine(), [msg(T0 + s, vib=True) for s in range(8)] + [msg(T0 + 8)] + [msg(T0 + 9 + s, vib=True) for s in range(8)], T0 + 17)
    assert max(ev["to_stage"] for ev in e.events if ev["engine"] == "staged") == 1
