"""Transform hourly marine API payloads into daily sea-temperature rows."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime

from eu_weather_etl.sea_places import SeaPlace

logger = logging.getLogger(__name__)

SOURCE = "Open-Meteo Marine"


@dataclass(frozen=True)
class SeaTemperatureRecord:
    region: str
    place: str
    country: str
    latitude: float
    longitude: float
    temperature_date: date
    temperature_c: float
    min_temperature_c: float
    max_temperature_c: float
    sample_count: int
    timezone: str | None
    utc_offset_seconds: int | None
    source: str
    fetched_at: datetime


def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


def to_records(
    place: SeaPlace,
    raw: dict,
    fetched_at: datetime,
) -> list[SeaTemperatureRecord]:
    hourly = raw.get("hourly") or {}
    times = hourly.get("time") or []
    temperatures = hourly.get("sea_surface_temperature") or []
    by_date: dict[date, list[float]] = {}

    for raw_time, temperature in zip(times, temperatures):
        if temperature is None:
            continue
        try:
            temperature_date = _parse_date(raw_time)
        except ValueError:
            logger.warning("Skipping invalid sea-temperature timestamp: %s", raw_time)
            continue
        by_date.setdefault(temperature_date, []).append(float(temperature))

    records: list[SeaTemperatureRecord] = []
    for temperature_date, values in sorted(by_date.items()):
        records.append(
            SeaTemperatureRecord(
                region=place.region,
                place=place.place,
                country=place.country,
                latitude=place.latitude,
                longitude=place.longitude,
                temperature_date=temperature_date,
                temperature_c=sum(values) / len(values),
                min_temperature_c=min(values),
                max_temperature_c=max(values),
                sample_count=len(values),
                timezone=raw.get("timezone"),
                utc_offset_seconds=raw.get("utc_offset_seconds"),
                source=SOURCE,
                fetched_at=fetched_at,
            )
        )
    return records


def transform_all(
    pairs: list[tuple[SeaPlace, dict]],
    fetched_at: datetime,
) -> list[SeaTemperatureRecord]:
    records: list[SeaTemperatureRecord] = []
    for place, raw in pairs:
        try:
            records.extend(to_records(place, raw, fetched_at))
        except Exception:  # noqa: BLE001 - one bad place should not sink the run
            logger.exception("Failed to transform sea-temperature payload for %s", place.place)
    return records