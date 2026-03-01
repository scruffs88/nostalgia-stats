# nostalgia-stats

A simple FastAPI service and worker for tracking historical statistics from an Icecast status JSON endpoint and storing snapshots in Postgres.

## Features

- Polls `https://live.radionostalgia.ro:8443/status-json.xsl` every minute (configurable) and persists data.
- Stores raw payload in `JSONB` for flexibility.
- Automatic schema creation on startup.
- Dashboard with current data and hourly statistics.
- API endpoints for current snapshot and stats with timezone-aware queries.

## Getting started

### Prerequisites

- Python 3.11+ (uses `zoneinfo` from the standard library)
- PostgreSQL (can run locally in Docker)

> **Note:** we pin `pydantic<2` in `requirements.txt` to avoid migration issues; newer versions move `BaseSettings` out of the core package.

### Local development

1. Clone the repository and change into it:
   ```bash
   git clone <repo-url> nostalgia-stats
   cd nostalgia-stats
   ```

2. Create a local Postgres instance (example using Docker):
   ```bash
   docker run --name nostalgia-db -e POSTGRES_PASSWORD=secret -p 5432:5432 -d postgres:15
   ```

3. Install dependencies in a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Set the `DATABASE_URL` environment variable (and optionally others):
   ```bash
   export DATABASE_URL="postgresql://postgres:secret@localhost:5432/postgres"
   export POLL_SECONDS=60             # optional
   export STATUS_URL="https://live.radionostalgia.ro:8443/status-json.xsl"  # optional
   ```

5. Run the worker in one terminal and the web service in another:
   ```bash
   # terminal 1
   python -m app.worker

   # terminal 2
   uvicorn app.web:app --host 0.0.0.0 --port 8000
   ```

6. Visit `http://localhost:8000` to see the dashboard.

### Railway deployment

1. Push this repo to Railway (create a new project).
2. Add the PostgreSQL plugin from the Railway dashboard; note the `DATABASE_URL` that Railway provides.
3. Create two services (or two deployment commands) using the **same repository**:
   - **web** service with the start command: `uvicorn app.web:app --host 0.0.0.0 --port $PORT`
   - **worker** service with the start command: `python -m app.worker`
4. Make sure both services have the `DATABASE_URL` environment variable set (Railway usually injects it automatically from the plugin).
5. Deploy.

> The schema is created automatically when either process starts, so the first process to spin up will initialize the database.


## API

- `GET /api/now` – latest snapshot JSON.
- `GET /api/stats/hourly?days=7&tz=Europe/Bucharest` – hourly aggregation over the past `days` days in local timezone.
- `GET /api/stats/today?tz=Europe/Bucharest` – average and max listeners for local "today".

## Notes

- Timezone conversions are done in SQL using `AT TIME ZONE` so local-hour grouping and "today" calculations respect the requested zone.
- Raw JSON payload kept in the `raw_json` column for future schema evolution.

Enjoy!
