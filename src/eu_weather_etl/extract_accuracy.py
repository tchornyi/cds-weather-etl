"""Extract for the accuracy ETL: past forecasts and observed actuals.

Two free, keyless Open-Meteo endpoints are combined:

- The Previous Runs API serves what each model *forecast in earlier runs* for a
  given hour: ``temperature_2m_previous_day3`` is the value the model predicted
  three days ahead of time. That lets us score forecasts retroactively instead
  of collecting them for weeks.
- The Archive API serves ERA5 reanalysis, used as ground truth. ERA5 is
  published with roughly a five-day delay, so callers should verify a target
  date at least ~8 days in the past.

Both endpoints accept comma-separated coordinate lists, so capitals are
batched like in ``extract.py``. Forecast models are requested one at a time to
keep response keys unambiguous; a model that errors is logged and skipped.
"""

from __future__ import annotations

import logging
from datetime import date

import httpx

from eu_weather_etl.capitals import Capital
from eu_weather_etl.forecasters import Forecaster

logger = logging.getLogger(__name__)

PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
# Hourly responses are much larger than current-weather ones; keep batches small.
BATCH_SIZE = 10
REQUEST_TIMEOUT = 60.0

# Metrics compared across forecasters. Values match Open-Meteo hourly variable
# names and are also stored verbatim in the forecasts_accuracy.metric column.
HOURLY_METRICS: tuple[str, ...] = (
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
)

_COMMON_PARAMS = {
    "wind_speed_unit": "kmh",
    "timezone": "UTC",
}


def _batches(capitals: list[Capital]) -> list[list[Capital]]:
    return [capitals[i : i + BATCH_SIZE] for i in range(0, len(capitals), BATCH_SIZE)]


def _request(client: httpx.Client, url: str, batch: list[Capital], params: dict) -> list[dict]:
    params = {
        "latitude": ",".join(str(c.latitude) for c in batch),
        "longitude": ",".join(str(c.longitude) for c in batch),
        **_COMMON_PARAMS,
        **params,
    }
    response = client.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    # The API returns a bare object for a single location and a list for many.
    return payload if isinstance(payload, list) else [payload]


def fetch_forecasts(
    capitals: list[Capital],
    forecasters: tuple[Forecaster, ...],
    target_date: date,
    max_lead_days: int,
) -> list[tuple[Capital, Forecaster, dict]]:
    """Return (capital, forecaster, raw_api_result) triples of past forecasts.

    Each raw result carries hourly series named ``<metric>_previous_day<N>``
    covering the 24 hours of ``target_date`` (UTC).
    """
    hourly_vars = ",".join(
        f"{metric}_previous_day{lead}"
        for metric in HOURLY_METRICS
        for lead in range(1, max_lead_days + 1)
    )
    day = target_date.isoformat()
    results: list[tuple[Capital, Forecaster, dict]] = []
    with httpx.Client(headers={"User-Agent": "eu-weather-etl/0.1"}) as client:
        for forecaster in forecasters:
            for batch in _batches(capitals):
                logger.info(
                    "Fetching %s forecasts for %d capitals (target %s, leads 1-%d)",
                    forecaster.model_id,
                    len(batch),
                    day,
                    max_lead_days,
                )
                try:
                    raws = _request(
                        client,
                        PREVIOUS_RUNS_URL,
                        batch,
                        {
                            "hourly": hourly_vars,
                            "start_date": day,
                            "end_date": day,
                            "models": forecaster.model_id,
                        },
                    )
                except httpx.HTTPError:  # one bad model shouldn't sink the run
                    logger.exception(
                        "Failed to fetch forecasts from %s; skipping batch",
                        forecaster.model_id,
                    )
                    continue
                for capital, raw in zip(batch, raws):
                    results.append((capital, forecaster, raw))
    return results


def fetch_actuals(capitals: list[Capital], target_date: date) -> list[tuple[Capital, dict]]:
    """Return (capital, raw_api_result) pairs of ERA5 actuals for target_date."""
    day = target_date.isoformat()
    results: list[tuple[Capital, dict]] = []
    with httpx.Client(headers={"User-Agent": "eu-weather-etl/0.1"}) as client:
        for batch in _batches(capitals):
            logger.info("Fetching ERA5 actuals for %d capitals (target %s)", len(batch), day)
            raws = _request(
                client,
                ARCHIVE_URL,
                batch,
                {
                    "hourly": ",".join(HOURLY_METRICS),
                    "start_date": day,
                    "end_date": day,
                },
            )
            for capital, raw in zip(batch, raws):
                results.append((capital, raw))
    return results
