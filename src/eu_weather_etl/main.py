"""Entry point: run one full ETL cycle producing a single weather snapshot."""

from __future__ import annotations

import os
import argparse
import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from eu_weather_etl.capitals import EUROPEAN_CAPITALS
from eu_weather_etl.db import connect
from eu_weather_etl.extract import fetch_weather
from eu_weather_etl.load import load_snapshot
from eu_weather_etl.migrate import run_migrations
from eu_weather_etl.telemetry import record_rows_affected
from eu_weather_etl.transform import transform_all

logger = logging.getLogger(__name__)


def run(skip_migrations: bool = False) -> int:
    """Execute extract -> transform -> load. Returns rows inserted."""
    snapshot_id = uuid4()
    snapshot_at = datetime.now(timezone.utc)
    logger.info("Starting snapshot %s at %s", snapshot_id, snapshot_at.isoformat())

    with connect() as conn:
        if not skip_migrations:
            run_migrations(conn)

        pairs = fetch_weather(list(EUROPEAN_CAPITALS))
        records = transform_all(pairs, snapshot_id, snapshot_at)

        # Emulate long-running work.
        sleep_time = os.environ.get("SIMULATE_LONG_WORK_SEC")
        if sleep_time:
            logger.info(f"Simulating long-running work for {sleep_time}s...")
            time.sleep(float(sleep_time))

        inserted = load_snapshot(conn, records)
        record_rows_affected(
            inserted,
            pipeline="load-eu-caps-weather",
            table="eu_caps_weather_logs",
            operation="insert",
        )

    logger.info("Snapshot %s complete: %d rows.", snapshot_id, inserted)
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Do not run pending migrations before loading.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level (default: INFO).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run(skip_migrations=args.skip_migrations)


if __name__ == "__main__":
    main()
