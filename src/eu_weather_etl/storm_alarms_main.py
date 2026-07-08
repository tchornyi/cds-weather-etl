"""Entry point: load global storm alarms from GDACS."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

from eu_weather_etl.db import connect
from eu_weather_etl.extract_storm_alarms import DEFAULT_FEED_URL, fetch_storm_alarms
from eu_weather_etl.load_storm_alarms import load_storm_alarms
from eu_weather_etl.migrate import run_migrations
from eu_weather_etl.transform_storm_alarms import transform_storm_alarms

logger = logging.getLogger(__name__)


def run(feed_url: str = DEFAULT_FEED_URL, skip_migrations: bool = False) -> int:
    """Execute extract -> transform -> load. Returns rows upserted."""
    fetched_at = datetime.now(timezone.utc)
    logger.info("Starting storm-alarms ETL at %s", fetched_at.isoformat())

    with connect() as conn:
        if not skip_migrations:
            run_migrations(conn)

        xml_text = fetch_storm_alarms(feed_url)
        records = transform_storm_alarms(xml_text, fetched_at)
        upserted = load_storm_alarms(conn, records)

    logger.info("Storm-alarms ETL complete: %d rows upserted.", upserted)
    return upserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feed-url",
        default=DEFAULT_FEED_URL,
        help="GDACS RSS feed URL (default: tropical cyclones from the last week).",
    )
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
    run(feed_url=args.feed_url, skip_migrations=args.skip_migrations)


if __name__ == "__main__":
    main()