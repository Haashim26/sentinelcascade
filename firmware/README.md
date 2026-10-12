PART A: ESP32 firmware (owner: Haashim Aslam)

ESP32 reads vibration, temperature and rain sensors, filters noise on the device (edge), and publishes JSON messages over MQTT.

Milestones:
- [ ] A1 sample_messages.json shared with the team
- [ ] A2 sensors wired and readable in Serial Monitor
- [ ] A3 edge filter (baseline, smoothing, elevated flags)
- [ ] A4 WiFi + MQTT publishing, offline buffering
- [ ] A5 verified with MQTT Explorer

WiFi details go in `secrets.h` (git-ignored). Copy `secrets.h.example` to `secrets.h` and fill it in.
