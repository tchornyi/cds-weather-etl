"""Load GDACS storm-alarm records with upsert semantics."""

from __future__ import annotations

import logging

import psycopg

from eu_weather_etl.transform_storm_alarms import StormAlarmRecord

logger = logging.getLogger(__name__)

_UPSERT_SQL = """
INSERT INTO storm_alarms (
    source, source_alarm_id, event_type, event_id, episode_id, name, title,
    description, link, alert_level, severity_value, severity_unit, country,
    iso3, latitude, longitude, from_date, to_date, published_at, fetched_at
) VALUES (
    %(source)s, %(source_alarm_id)s, %(event_type)s, %(event_id)s,
    %(episode_id)s, %(name)s, %(title)s, %(description)s, %(link)s,
    %(alert_level)s, %(severity_value)s, %(severity_unit)s, %(country)s,
    %(iso3)s, %(latitude)s, %(longitude)s, %(from_date)s, %(to_date)s,
    %(published_at)s, %(fetched_at)s
)
ON CONFLICT (source, source_alarm_id) DO UPDATE SET
    event_type = EXCLUDED.event_type,
    event_id = EXCLUDED.event_id,
    episode_id = EXCLUDED.episode_id,
    name = EXCLUDED.name,
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    link = EXCLUDED.link,
    alert_level = EXCLUDED.alert_level,
    severity_value = EXCLUDED.severity_value,
    severity_unit = EXCLUDED.severity_unit,
    country = EXCLUDED.country,
    iso3 = EXCLUDED.iso3,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    from_date = EXCLUDED.from_date,
    to_date = EXCLUDED.to_date,
    published_at = EXCLUDED.published_at,
    fetched_at = EXCLUDED.fetched_at,
    updated_at = now()
"""


def load_storm_alarms(
    conn: psycopg.Connection,
    records: list[StormAlarmRecord],
) -> int:
    """Upsert all records in a single transaction. Returns affected row count."""
    if not records:
        logger.warning("No storm-alarm records to load; skipping upsert.")
        return 0

    rows = [vars(record) for record in records]
    with conn.transaction():
        with conn.cursor() as cur:
            cur.executemany(_UPSERT_SQL, rows)
    logger.info("Upserted %d rows into storm_alarms.", len(rows))
    return len(rows)