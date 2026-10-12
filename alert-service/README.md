PART C: Alert service (owner: Irfan Ahmed)

Sends SMS through Twilio. `POST /alert` (stage 2 = officials only, stage 3 = residents and officials), `GET /alerts`. Logs every alert to a Supabase table. `DRY_RUN=true` logs instead of sending, to save trial credit.

Milestones:
- [ ] C1 alert service with Twilio and dry-run mode
- [ ] C2 deployed on Render

Copy `.env.example` to `.env` to run locally.
