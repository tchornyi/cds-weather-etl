-- Forecast accuracy table: each accuracy ETL run inserts one row per
-- (capital, forecaster, lead_days, metric) for a single target date, all rows
-- sharing the same snapshot_id / snapshot_at. Errors are aggregated over the
-- 24 hours of the target date (UTC), comparing what each model forecast
-- lead_days in advance against ERA5 reanalysis actuals.

CREATE TABLE IF NOT EXISTS forecasts_accuracy (
    id                  BIGSERIAL       PRIMARY KEY,
    snapshot_id         UUID            NOT NULL,
    snapshot_at         TIMESTAMPTZ     NOT NULL,
    capital             TEXT            NOT NULL,
    country             TEXT            NOT NULL,
    forecaster          TEXT            NOT NULL,  -- Open-Meteo model id, e.g. ecmwf_ifs025
    forecaster_label    TEXT            NOT NULL,  -- human-readable agency name
    target_date         DATE            NOT NULL,  -- the day being verified (UTC)
    lead_days           SMALLINT        NOT NULL,  -- forecast issued N days before target_date
    metric              TEXT            NOT NULL,  -- temperature_2m | relative_humidity_2m | wind_speed_10m
    n_hours             SMALLINT        NOT NULL,  -- hours with both forecast and actual present
    forecast_mean       DOUBLE PRECISION,
    actual_mean         DOUBLE PRECISION,
    bias                DOUBLE PRECISION,          -- mean(forecast - actual)
    mae                 DOUBLE PRECISION,          -- mean absolute error
    rmse                DOUBLE PRECISION,          -- root mean squared error
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_forecasts_accuracy_snapshot_id
    ON forecasts_accuracy (snapshot_id);

CREATE INDEX IF NOT EXISTS ix_forecasts_accuracy_forecaster_metric
    ON forecasts_accuracy (forecaster, metric, target_date);

CREATE INDEX IF NOT EXISTS ix_forecasts_accuracy_target_date
    ON forecasts_accuracy (target_date);
