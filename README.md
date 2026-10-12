# SentinelCascade

Staged-confidence emergency alert system. Instead of firing a wide-area alert on one noisy sensor reading, SentinelCascade waits for sustained or multi-sensor evidence and escalates in stages, so alerts can be sent automatically without crying wolf.

## Flow

ESP32 and simulator -> MQTT broker -> **ingestion service (Part A)** -> **decision engine (Part B)** -> **alert service and dashboard (Part C)**

## Team and ownership

| Part | Owner | Folders | Cloud service |
|---|---|---|---|
| A | Haashim Aslam | `firmware/`, `ingestion-service/` | Ingestion service (Render + Supabase) |
| B | Lalit Kishore | `backend/`, `simulator/` | Decision engine (Render + Upstash Redis + Supabase) |
| C | Irfan Ahmed | `alert-service/`, `dashboard/`, `analysis/` | Alert service (Render + Supabase + Twilio), dashboard (Vercel) |

Rule: commit only to your own folders. Review a teammate's Pull Request: A reviews B, B reviews C, C reviews A.

## Docs

- `docs/CONTRACT.md`: message format, stage rules and API shapes shared by all parts
- `docs/` also holds the project overview PDF and the team plan

## Secrets

Never commit passwords, keys or tokens. Copy each `.env.example` to `.env` and fill it in locally. `.env` and `secrets.h` are git-ignored.
