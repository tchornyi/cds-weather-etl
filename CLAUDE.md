# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this is

A small, self-contained **ETL** that takes a point-in-time **snapshot** of current
weather for every European capital and stores it in PostgreSQL. Each run inserts
one row per capital, all sharing a single `snapshot_id` / `snapshot_at`, into the
table **`eu_caps_weather_logs`**.

- **Extract** — `extract.py`: HTTP calls to the free [Open-Meteo](https://open-meteo.com)
  forecast API (no API key). Capitals are batched (comma-separated coordinates)
  to minimise requests.
- **Transform** — `transform.py`: normalises raw payloads into flat
  `WeatherRecord`s (temperature, wind speed, wind direction, humidity, sunrise,
  sunset), attaching the location's UTC offset to all timestamps.
- **Load** — `load.py`: one bulk `executemany` insert inside a single transaction.
- **Migrate** — `migrate.py`: forward-only SQL migration runner; tracks applied
  files in `schema_migrations`. The target table is created here, never by hand.

## Layout

```
migrations/                         # *.sql, applied in filename order
  001_create_eu_caps_weather_logs.sql
src/eu_weather_etl/
  config.py      # reads DB creds from env (DATABASE_URL or PG* vars)
  capitals.py    # static list of European capitals + coordinates
  db.py          # psycopg connection helper
  migrate.py     # migration runner (entry point: eu-weather-migrate)
  extract.py     # Open-Meteo HTTP client
  transform.py   # raw payload -> WeatherRecord
  load.py        # bulk insert
  main.py        # orchestrates E->T->L (entry point: eu-weather-etl)
```

## Running (uv)

This project runs under [uv](https://docs.astral.sh/uv/). All commands resolve
dependencies from `pyproject.toml` into an ephemeral environment.

```bash
# Configure the database connection (env vars; see .env.example)
cp .env.example .env        # then edit values

# Run a full ETL cycle. Applies pending migrations first (skipping any already
# applied), then extracts -> transforms -> loads. This is the only command needed.
uv run eu-weather-etl

# Optional: run migrations on their own
uv run eu-weather-migrate

# Optional: skip migrations on this run / change verbosity
uv run eu-weather-etl --skip-migrations --log-level DEBUG
```

## Configuration

Database credentials come **only** from the environment (`config.py`):

When deployed by SEAD CDS, database credentials come from an attached shared
**Connection**, injected as `{PREFIX}_HOST`, `{PREFIX}_PORT`, `{PREFIX}_DB`,
`{PREFIX}_USER`, `{PREFIX}_PASSWORD`, `{PREFIX}_URI`. `CDS_DB_PREFIX` names the
prefix to read (default `DB`); `{PREFIX}_URI` alone is enough. Resolution order:

1. `CDS_DB_PREFIX`-prefixed Connection vars (`{PREFIX}_URI`, else the parts).
2. `DATABASE_URL` — a full libpq connection string.
3. `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGSSLMODE`.

2 and 3 are the fallback for local runs and pre-Connections deployments.

A local `.env` file is auto-loaded; real environment variables always override it.

## Conventions

- **Schema changes go through migrations.** Add a new `NNN_*.sql` file with the
  next number; never edit an already-applied migration or alter the table by hand.
- Each ETL run is an immutable snapshot — append-only, never updates/deletes.
- Timestamps are stored as `TIMESTAMPTZ`. The API returns local times plus a
  `utc_offset_seconds`; `transform.py` makes them timezone-aware before insert.
- A single capital failing to transform is logged and skipped, not fatal.
