"""Load: bulk-insert forecast accuracy records as one snapshot."""

from __future__ import annotations

import logging

import psycopg

from eu_weather_etl.transform_accuracy import AccuracyRecord

logger = logging.getLogger(__name__)

_INSERT_SQL = """
INSERT INTO forecasts_accuracy (
    snapshot_id, snapshot_at, capital, country, forecaster, forecaster_label,
    target_date, lead_days, metric, n_hours,
    forecast_mean, actual_mean, bias, mae, rmse
) VALUES (
    %(snapshot_id)s, %(snapshot_at)s, %(capital)s, %(country)s, %(forecaster)s,
    %(forecaster_label)s, %(target_date)s, %(lead_days)s, %(metric)s, %(n_hours)s,
    %(forecast_mean)s, %(actual_mean)s, %(bias)s, %(mae)s, %(rmse)s
)
"""


def load_accuracy(conn: psycopg.Connection, records: list[AccuracyRecord]) -> int:
    """Insert all records in a single transaction. Returns the row count."""
    if not records:
        logger.warning("No accuracy records to load; skipping insert.")
        return 0

    rows = [vars(record) for record in records]
    with conn.transaction():
        with conn.cursor() as cur:
            cur.executemany(_INSERT_SQL, rows)
    logger.info("Inserted %d rows into forecasts_accuracy.", len(rows))
    return len(rows)
