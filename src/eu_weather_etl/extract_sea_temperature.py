"""Extract sea-surface temperatures from the Open-Meteo Marine API."""

from __future__ import annotations

import email.utils
import logging
import os
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from eu_weather_etl.sea_places import SeaPlace

logger = logging.getLogger(__name__)

API_URL = "https://marine-api.open-meteo.com/v1/marine"
BATCH_SIZE = 20
REQUEST_TIMEOUT = 60.0
HOURLY_FIELDS = "sea_surface_temperature"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
DEFAULT_RETRY_ATTEMPTS = 4
DEFAULT_RETRY_INITIAL_DELAY_SECONDS = 15.0
DEFAULT_RETRY_BACKOFF = 2.0
DEFAULT_RETRY_JITTER_SECONDS = 1.0
DEFAULT_BATCH_DELAY_SECONDS = 1.0


@dataclass(frozen=True)
class RetryOptions:
    max_attempts: int = DEFAULT_RETRY_ATTEMPTS
    initial_delay_seconds: float = DEFAULT_RETRY_INITIAL_DELAY_SECONDS
    backoff: float = DEFAULT_RETRY_BACKOFF
    jitter_seconds: float = DEFAULT_RETRY_JITTER_SECONDS

    @classmethod
    def from_env(cls) -> "RetryOptions":
        return cls(
            max_attempts=_parse_positive_int_env(
                "SEA_TEMPERATURE_RETRY_ATTEMPTS",
                DEFAULT_RETRY_ATTEMPTS,
            ),
            initial_delay_seconds=_parse_non_negative_float_env(
                "SEA_TEMPERATURE_RETRY_INITIAL_DELAY_SECONDS",
                DEFAULT_RETRY_INITIAL_DELAY_SECONDS,
            ),
            backoff=_parse_positive_float_env(
                "SEA_TEMPERATURE_RETRY_BACKOFF",
                DEFAULT_RETRY_BACKOFF,
            ),
            jitter_seconds=_parse_non_negative_float_env(
                "SEA_TEMPERATURE_RETRY_JITTER_SECONDS",
                DEFAULT_RETRY_JITTER_SECONDS,
            ),
        )

    def delay_for_attempt(self, attempt_number: int) -> float:
        delay = self.initial_delay_seconds * (self.backoff ** (attempt_number - 1))
        if self.jitter_seconds > 0:
            delay += random.uniform(0, self.jitter_seconds)
        return delay


def _request_batch(
    client: httpx.Client,
    batch: list[SeaPlace],
    forecast_days: int,
    past_days: int,
    retry_options: RetryOptions | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict]:
    retry_options = retry_options or RetryOptions.from_env()
    params = {
        "latitude": ",".join(str(place.latitude) for place in batch),
        "longitude": ",".join(str(place.longitude) for place in batch),
        "hourly": HOURLY_FIELDS,
        "timezone": "auto",
        "forecast_days": forecast_days,
        "past_days": past_days,
        "cell_selection": "sea",
    }
    for attempt in range(1, retry_options.max_attempts + 1):
        try:
            response = client.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, list) else [payload]
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code not in RETRYABLE_STATUS_CODES or attempt == retry_options.max_attempts:
                raise
            delay = _retry_delay_seconds(exc.response, retry_options, attempt)
            logger.warning(
                "Open-Meteo Marine returned HTTP %s for %d places on attempt %d/%d; "
                "retrying in %.1fs.",
                status_code,
                len(batch),
                attempt,
                retry_options.max_attempts,
                delay,
            )
            sleep(delay)
        except httpx.TransportError as exc:
            if attempt == retry_options.max_attempts:
                raise
            delay = retry_options.delay_for_attempt(attempt)
            logger.warning(
                "Open-Meteo Marine request failed for %d places on attempt %d/%d: %s; "
                "retrying in %.1fs.",
                len(batch),
                attempt,
                retry_options.max_attempts,
                exc,
                delay,
            )
            sleep(delay)

    raise RuntimeError("Retry loop exhausted unexpectedly for Open-Meteo Marine request.")


def fetch_sea_temperatures(
    places: list[SeaPlace],
    forecast_days: int = 7,
    past_days: int = 0,
    retry_options: RetryOptions | None = None,
    sleep: Callable[[float], None] = time.sleep,
    batch_delay_seconds: float | None = None,
    batch_size: int | None = None,
) -> list[tuple[SeaPlace, dict]]:
    """Return (place, raw_api_result) pairs for requested coastal places."""
    retry_options = retry_options or RetryOptions.from_env()
    batch_delay_seconds = (
        _parse_non_negative_float_env(
            "SEA_TEMPERATURE_BATCH_DELAY_SECONDS",
            DEFAULT_BATCH_DELAY_SECONDS,
        )
        if batch_delay_seconds is None
        else batch_delay_seconds
    )
    batch_size = batch_size or _parse_positive_int_env("SEA_TEMPERATURE_BATCH_SIZE", BATCH_SIZE)
    results: list[tuple[SeaPlace, dict]] = []
    with httpx.Client(headers={"User-Agent": "eu-weather-etl/0.1"}) as client:
        for start in range(0, len(places), batch_size):
            if start and batch_delay_seconds:
                logger.debug(
                    "Sleeping %.1fs before next sea-temperature batch.",
                    batch_delay_seconds,
                )
                sleep(batch_delay_seconds)
            batch = places[start : start + batch_size]
            logger.info(
                "Fetching sea temperatures for %d places (%d-%d of %d)",
                len(batch),
                start + 1,
                start + len(batch),
                len(places),
            )
            raws = _request_batch(
                client,
                batch,
                forecast_days,
                past_days,
                retry_options=retry_options,
                sleep=sleep,
            )
            for place, raw in zip(batch, raws):
                results.append((place, raw))
    return results


def _retry_delay_seconds(
    response: httpx.Response,
    retry_options: RetryOptions,
    attempt_number: int,
) -> float:
    retry_after = _retry_after_seconds(response)
    if retry_after is not None:
        return retry_after
    return retry_options.delay_for_attempt(attempt_number)


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        pass

    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())


def _parse_positive_int_env(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning("%s must be an integer; using default %s.", name, default)
        return default
    if value <= 0:
        logger.warning("%s must be greater than zero; using default %s.", name, default)
        return default
    return value


def _parse_positive_float_env(name: str, default: float) -> float:
    value = _parse_float_env(name, default)
    if value <= 0:
        logger.warning("%s must be greater than zero; using default %s.", name, default)
        return default
    return value


def _parse_non_negative_float_env(name: str, default: float) -> float:
    value = _parse_float_env(name, default)
    if value < 0:
        logger.warning("%s must be zero or greater; using default %s.", name, default)
        return default
    return value


def _parse_float_env(name: str, default: float) -> float:
    raw_value = os.environ.get(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return float(raw_value)
    except ValueError:
        logger.warning("%s must be a number; using default %s.", name, default)
        return default
