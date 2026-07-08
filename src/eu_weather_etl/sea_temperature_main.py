"""Entry point: load daily sea temperature for major coastal cities."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

from eu_weather_etl.db import connect
from eu_weather_etl.extract_sea_temperature import fetch_sea_temperatures
from eu_weather_etl.load_sea_temperature import load_sea_temperatures
from eu_weather_etl.migrate import run_migrations
from eu_weather_etl.sea_places import SEA_PLACES
from eu_weather_etl.transform_sea_temperature import transform_all

logger = logging.getLogger(__name__)


def run(
    forecast_days: int = 7,
    past_days: int = 0,
    skip_migrations: bool = False,
) -> int:
    """Execute extract -> transform -> load. Returns rows upserted."""
    fetched_at = datetime.now(timezone.utc)
    logger.info(
        "Starting sea-temperature ETL at %s for %d places",
        fetched_at.isoformat(),
        len(SEA_PLACES),
    )

    with connect() as conn:
        if not skip_migrations:
            run_migrations(conn)

        pairs = fetch_sea_temperatures(
            list(SEA_PLACES),
            forecast_days=forecast_days,
            past_days=past_days,
        )
        records = transform_all(pairs, fetched_at)
        upserted = load_sea_temperatures(conn, records)

    logger.info("Sea-temperature ETL complete: %d rows upserted.", upserted)
    return upserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--forecast-days",
        type=int,
        default=7,
        choices=range(0, 9),
        help="Number of forecast days to fetch, 0-8 (default: 7).",
    )
    parser.add_argument(
        "--past-days",
        type=int,
        default=0,
        choices=range(0, 93),
        help="Number of recent past days to fetch, 0-92 (default: 0).",
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
    run(
        forecast_days=args.forecast_days,
        past_days=args.past_days,
        skip_migrations=args.skip_migrations,
    )


if __name__ == "__main__":
    main()