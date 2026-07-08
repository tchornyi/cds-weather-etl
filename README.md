# sds-poc-etl

Simple Python ETL that snapshots current weather for **all European capitals**
into a PostgreSQL table, `eu_caps_weather_logs`. Each run appends one immutable
snapshot (one row per capital, sharing a `snapshot_id`).

Data source: the free, key-less [Open-Meteo](https://open-meteo.com) forecast API.
Fields captured: **temperature, wind speed, wind direction, humidity, sunrise,
and sunset**.

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.11+ is provisioned by uv)
- A reachable PostgreSQL database

## Quick start

```bash
# 1. Provide database credentials via environment variables
cp .env.example .env        # edit the values to point at your database

# 2. Take a weather snapshot. This single command applies any pending
#    migrations first (creating the table on a fresh database), skips
#    migrations that are already applied, then loads the snapshot.
uv run eu-weather-etl
```

> Migrations run automatically as part of the ETL — one command is all you need.
> `uv run eu-weather-migrate` exists only if you want to apply migrations on
> their own, and `uv run eu-weather-etl --skip-migrations` skips them for a run.

Inspect the result:

```sql
SELECT snapshot_at, capital, temperature_c, wind_speed_kmh,
       wind_direction_deg, humidity_pct, sunrise, sunset
FROM   eu_caps_weather_logs
ORDER  BY snapshot_at DESC, capital
LIMIT  10;
```


## Additional ETLs

```bash
# Daily sea-surface temperature by city/date for Mediterranean and Black Sea places.
# Existing rows are updated for the same region/country/place/date.
uv run sea-temperature-etl

# Global storm alarms from the GDACS tropical-cyclone feed.
# Existing alarms are updated by source alarm ID.
uv run storm-alarms-etl
```

New tables are created by migrations:

- `sea_temperature`: one row per monitored place and local date, with mean/min/max sea-surface temperature.
- `storm_alarms`: one row per GDACS tropical-cyclone alarm/event episode.

## Configuration

Credentials are read from the environment (a local `.env` is auto-loaded):

| Variable        | Purpose                                            |
| --------------- | -------------------------------------------------- |
| `DATABASE_URL`  | Full libpq connection string (wins if set)         |
| `PGHOST`        | Database host                                      |
| `PGPORT`        | Port (default 5432)                                |
| `PGDATABASE`    | Database name                                      |
| `PGUSER`        | Username                                           |
| `PGPASSWORD`    | Password                                           |
| `PGSSLMODE`     | Optional libpq sslmode (e.g. `require`)            |

## How it works

`extract` (Open-Meteo HTTP) → `transform` (normalise to `WeatherRecord`) →
`load` (bulk insert one snapshot). The target table is created by the migration
runner, never by hand. See [CLAUDE.md](CLAUDE.md) for architecture and conventions.

## Schema: `eu_caps_weather_logs`

| Column               | Type          | Notes                              |
| -------------------- | ------------- | ---------------------------------- |
| `id`                 | `BIGSERIAL`   | Primary key                        |
| `snapshot_id`        | `UUID`        | One value per ETL run              |
| `snapshot_at`        | `TIMESTAMPTZ` | Run start time (UTC)               |
| `capital`            | `TEXT`        | Capital city name                  |
| `country`            | `TEXT`        | Country name                       |
| `latitude`           | `DOUBLE`      | City latitude                      |
| `longitude`          | `DOUBLE`      | City longitude                     |
| `temperature_c`      | `DOUBLE`      | Air temperature, °C                |
| `wind_speed_kmh`     | `DOUBLE`      | Wind speed, km/h                   |
| `wind_direction_deg` | `DOUBLE`      | Wind direction, degrees            |
| `humidity_pct`       | `DOUBLE`      | Relative humidity, %               |
| `sunrise`            | `TIMESTAMPTZ` | Local sunrise (tz-aware)           |
| `sunset`             | `TIMESTAMPTZ` | Local sunset (tz-aware)            |
| `observed_at`        | `TIMESTAMPTZ` | API observation time              |
| `created_at`         | `TIMESTAMPTZ` | Row insert time (default `now()`)  |
