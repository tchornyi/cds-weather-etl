"""Entry point: score past forecasts against actuals for one target date.

For every European capital, fetches what each forecaster predicted 1..N days
in advance for the target date, compares it with ERA5 reanalysis actuals, and
stores aggregated errors (bias / MAE / RMSE) in the forecasts_accuracy table.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from eu_weather_etl.capitals import EUROPEAN_CAPITALS
from eu_weather_etl.db import connect
from eu_weather_etl.extract_accuracy import fetch_actuals, fetch_forecasts
from eu_weather_etl.forecasters import FORECASTERS
from eu_weather_etl.load_accuracy import load_accuracy
from eu_weather_etl.migrate import run_migrations
from eu_weather_etl.transform_accuracy import compute_accuracy

logger = logging.getLogger(__name__)

# ERA5 actuals are published with roughly a five-day delay; add headroom.
DEFAULT_TARGET_LAG_DAYS = 8
DEFAULT_MAX_LEAD_DAYS = 7


def run(
    target_date: date,
    max_lead_days: int = DEFAULT_MAX_LEAD_DAYS,
    skip_migrations: bool = False,
) -> int:
    """Execute extract -> transform -> load. Returns rows inserted."""
    snapshot_id = uuid4()
    snapshot_at = datetime.now(timezone.utc)
    logger.info(
        "Starting accuracy snapshot %s: target date %s, leads 1-%d, %d forecasters",
        snapshot_id,
        target_date.isoformat(),
        max_lead_days,
        len(FORECASTERS),
    )

    with connect() as conn:
        if not skip_migrations:
            run_migrations(conn)

        capitals = list(EUROPEAN_CAPITALS)
        actual_pairs = fetch_actuals(capitals, target_date)
        forecast_triples = fetch_forecasts(capitals, FORECASTERS, target_date, max_lead_days)
        records = compute_accuracy(
            forecast_triples, actual_pairs, max_lead_days, snapshot_id, snapshot_at, target_date
        )
        inserted = load_accuracy(conn, records)

    logger.info("Accuracy snapshot %s complete: %d rows.", snapshot_id, inserted)
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-date",
        type=date.fromisoformat,
        default=None,
        help=(
            "Day to verify, as YYYY-MM-DD (UTC). Defaults to "
            f"{DEFAULT_TARGET_LAG_DAYS} days ago so ERA5 actuals are available."
        ),
    )
    parser.add_argument(
        "--max-lead-days",
        type=int,
        default=DEFAULT_MAX_LEAD_DAYS,
        choices=range(1, 8),
        help="Score forecasts issued 1..N days before the target date (default: 7).",
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
    target_date = args.target_date or (
        datetime.now(timezone.utc) - timedelta(days=DEFAULT_TARGET_LAG_DAYS)
    ).date()
    run(target_date, max_lead_days=args.max_lead_days, skip_migrations=args.skip_migrations)


if __name__ == "__main__":
    main()
