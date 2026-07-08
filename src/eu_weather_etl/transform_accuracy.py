"""Transform for the accuracy ETL: score past forecasts against actuals.

For every (capital, forecaster, lead_days, metric) combination the hourly
forecast series is aligned with the hourly ERA5 series by timestamp, and the
errors are aggregated over the target day into bias / MAE / RMSE.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from eu_weather_etl.capitals import Capital
from eu_weather_etl.extract_accuracy import HOURLY_METRICS
from eu_weather_etl.forecasters import Forecaster

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AccuracyRecord:
    snapshot_id: UUID
    snapshot_at: datetime
    capital: str
    country: str
    forecaster: str
    forecaster_label: str
    target_date: date
    lead_days: int
    metric: str
    n_hours: int
    forecast_mean: float
    actual_mean: float
    bias: float
    mae: float
    rmse: float


def _series(raw: dict, key: str) -> dict[str, float]:
    """Extract an hourly series as {iso_timestamp: value}, dropping nulls."""
    hourly = raw.get("hourly") or {}
    times = hourly.get("time") or []
    values = hourly.get(key) or []
    return {t: v for t, v in zip(times, values) if v is not None}


def _score(
    capital: Capital,
    forecaster: Forecaster,
    forecast_raw: dict,
    actual_raw: dict,
    lead_days: int,
    metric: str,
    snapshot_id: UUID,
    snapshot_at: datetime,
    target_date: date,
) -> AccuracyRecord | None:
    forecast = _series(forecast_raw, f"{metric}_previous_day{lead_days}")
    actual = _series(actual_raw, metric)
    hours = sorted(forecast.keys() & actual.keys())
    if not hours:
        return None

    diffs = [forecast[h] - actual[h] for h in hours]
    n = len(hours)
    return AccuracyRecord(
        snapshot_id=snapshot_id,
        snapshot_at=snapshot_at,
        capital=capital.name,
        country=capital.country,
        forecaster=forecaster.model_id,
        forecaster_label=forecaster.label,
        target_date=target_date,
        lead_days=lead_days,
        metric=metric,
        n_hours=n,
        forecast_mean=sum(forecast[h] for h in hours) / n,
        actual_mean=sum(actual[h] for h in hours) / n,
        bias=sum(diffs) / n,
        mae=sum(abs(d) for d in diffs) / n,
        rmse=math.sqrt(sum(d * d for d in diffs) / n),
    )


def compute_accuracy(
    forecast_triples: list[tuple[Capital, Forecaster, dict]],
    actual_pairs: list[tuple[Capital, dict]],
    max_lead_days: int,
    snapshot_id: UUID,
    snapshot_at: datetime,
    target_date: date,
) -> list[AccuracyRecord]:
    actuals_by_capital = {capital.name: raw for capital, raw in actual_pairs}
    records: list[AccuracyRecord] = []
    for capital, forecaster, forecast_raw in forecast_triples:
        actual_raw = actuals_by_capital.get(capital.name)
        if actual_raw is None:
            logger.warning("No actuals for %s; skipping.", capital.name)
            continue
        for metric in HOURLY_METRICS:
            for lead_days in range(1, max_lead_days + 1):
                try:
                    record = _score(
                        capital,
                        forecaster,
                        forecast_raw,
                        actual_raw,
                        lead_days,
                        metric,
                        snapshot_id,
                        snapshot_at,
                        target_date,
                    )
                except Exception:  # noqa: BLE001 - one bad series shouldn't sink the run
                    logger.exception(
                        "Failed to score %s/%s lead=%d for %s",
                        forecaster.model_id,
                        metric,
                        lead_days,
                        capital.name,
                    )
                    continue
                if record is not None:
                    records.append(record)
    return records
