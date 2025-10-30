
# A3 Study Upgrade (Flask)

This fork adds:
- Own backend + DB (Postgres via `DATABASE_URL` or local SQLite)
- MTurk-compatible endpoints (`/study/*`) with per-worker tracking
- Randomized N trials per participant from your A2 dataset
- Two conditions: control vs ai (pass `?condition=control|ai`)
- Completion code flow and JSON export

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Local DB
flask db upgrade

# Seed trials (expects list of JSON objects; fields are up to your task)
flask seed-trials resources/sample_trials.json

# Run
flask run
```

## Env Vars

- `SECRET_KEY`: session/csrf
- `DATABASE_URL`: e.g. `postgresql://user:pass@host/db`
- `STUDY_TRIALS_PER_PARTICIPANT`: default 8

## Deploy (Render)

- Create a new Web Service from this repo
- Build command: `pip install -r requirements.txt && flask db upgrade`
- Start command: `gunicorn minisurvey:app`
- Add env vars: `SECRET_KEY`, `DATABASE_URL`

## MTurk (Requester Sandbox)

- Use **ExternalQuestion** or Linked Survey template.
- Point to: `https://your-app/study?condition=control` (and another link with `ai`)
- MTurk will append `workerId`, `assignmentId`, `hitId`, `turkSubmitTo`.

## Data Export

- Admin JSON: `/study/admin`
- Responses JSON: `/study/export`
