"""Load sea-temperature records with upsert semantics."""

from __future__ import annotations

import logging

import psycopg

from eu_weather_etl.transform_sea_temperature import SeaTemperatureRecord

logger = logging.getLogger(__name__)

_UPSERT_SQL = """
INSERT INTO sea_temperature (
    region, place, country, latitude, longitude, temperature_date,
    temperature_c, min_temperature_c, max_temperature_c, sample_count,
    timezone, utc_offset_seconds, source, fetched_at
) VALUES (
    %(region)s, %(place)s, %(country)s, %(latitude)s, %(longitude)s,
    %(temperature_date)s, %(temperature_c)s, %(min_temperature_c)s,
    %(max_temperature_c)s, %(sample_count)s, %(timezone)s,
    %(utc_offset_seconds)s, %(source)s, %(fetched_at)s
)
ON CONFLICT (region, country, place, temperature_date) DO UPDATE SET
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    temperature_c = EXCLUDED.temperature_c,
    min_temperature_c = EXCLUDED.min_temperature_c,
    max_temperature_c = EXCLUDED.max_temperature_c,
    sample_count = EXCLUDED.sample_count,
    timezone = EXCLUDED.timezone,
    utc_offset_seconds = EXCLUDED.utc_offset_seconds,
    source = EXCLUDED.source,
    fetched_at = EXCLUDED.fetched_at,
    updated_at = now()
"""


def load_sea_temperatures(
    conn: psycopg.Connection,
    records: list[SeaTemperatureRecord],
) -> int:
    """Upsert all records in a single transaction. Returns affected row count."""
    if not records:
        logger.warning("No sea-temperature records to load; skipping upsert.")
        return 0

    rows = [vars(record) for record in records]
    with conn.transaction():
        with conn.cursor() as cur:
            cur.executemany(_UPSERT_SQL, rows)
    logger.info("Upserted %d rows into sea_temperature.", len(rows))
    return len(rows)