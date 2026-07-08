"""Extract sea-surface temperatures from the Open-Meteo Marine API."""

from __future__ import annotations

import logging

import httpx

from eu_weather_etl.sea_places import SeaPlace

logger = logging.getLogger(__name__)

API_URL = "https://marine-api.open-meteo.com/v1/marine"
BATCH_SIZE = 20
REQUEST_TIMEOUT = 60.0
HOURLY_FIELDS = "sea_surface_temperature"


def _request_batch(
    client: httpx.Client,
    batch: list[SeaPlace],
    forecast_days: int,
    past_days: int,
) -> list[dict]:
    params = {
        "latitude": ",".join(str(place.latitude) for place in batch),
        "longitude": ",".join(str(place.longitude) for place in batch),
        "hourly": HOURLY_FIELDS,
        "timezone": "auto",
        "forecast_days": forecast_days,
        "past_days": past_days,
        "cell_selection": "sea",
    }
    response = client.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else [payload]


def fetch_sea_temperatures(
    places: list[SeaPlace],
    forecast_days: int = 7,
    past_days: int = 0,
) -> list[tuple[SeaPlace, dict]]:
    """Return (place, raw_api_result) pairs for requested coastal places."""
    results: list[tuple[SeaPlace, dict]] = []
    with httpx.Client(headers={"User-Agent": "eu-weather-etl/0.1"}) as client:
        for start in range(0, len(places), BATCH_SIZE):
            batch = places[start : start + BATCH_SIZE]
            logger.info(
                "Fetching sea temperatures for %d places (%d-%d of %d)",
                len(batch),
                start + 1,
                start + len(batch),
                len(places),
            )
            raws = _request_batch(client, batch, forecast_days, past_days)
            for place, raw in zip(batch, raws):
                results.append((place, raw))
    return results