-- Sea temperature table: one row per monitored coastal place and local date.
-- Values are upserted because a forecast date can be refreshed by later API runs.

CREATE TABLE IF NOT EXISTS sea_temperature (
    id                  BIGSERIAL        PRIMARY KEY,
    region              TEXT             NOT NULL,
    place               TEXT             NOT NULL,
    country             TEXT             NOT NULL,
    latitude            DOUBLE PRECISION NOT NULL,
    longitude           DOUBLE PRECISION NOT NULL,
    temperature_date    DATE             NOT NULL,
    temperature_c       DOUBLE PRECISION NOT NULL,
    min_temperature_c   DOUBLE PRECISION,
    max_temperature_c   DOUBLE PRECISION,
    sample_count        SMALLINT         NOT NULL,
    timezone            TEXT,
    utc_offset_seconds  INTEGER,
    source              TEXT             NOT NULL,
    fetched_at          TIMESTAMPTZ      NOT NULL,
    created_at          TIMESTAMPTZ      NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ      NOT NULL DEFAULT now(),

    CONSTRAINT uq_sea_temperature_place_date
        UNIQUE (region, country, place, temperature_date)
);

CREATE INDEX IF NOT EXISTS ix_sea_temperature_region_date
    ON sea_temperature (region, temperature_date);

CREATE INDEX IF NOT EXISTS ix_sea_temperature_place_date
    ON sea_temperature (place, temperature_date);