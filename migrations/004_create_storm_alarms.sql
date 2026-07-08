-- Global storm alarms from GDACS tropical cyclone feeds.
-- Source alarm IDs are stable per GDACS event/episode and are upserted.

CREATE TABLE IF NOT EXISTS storm_alarms (
    id                  BIGSERIAL        PRIMARY KEY,
    source              TEXT             NOT NULL,
    source_alarm_id     TEXT             NOT NULL,
    event_type          TEXT,
    event_id            TEXT,
    episode_id          TEXT,
    name                TEXT,
    title               TEXT             NOT NULL,
    description         TEXT,
    link                TEXT,
    alert_level         TEXT,
    severity_value      DOUBLE PRECISION,
    severity_unit       TEXT,
    country             TEXT,
    iso3                TEXT,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    from_date           TIMESTAMPTZ,
    to_date             TIMESTAMPTZ,
    published_at        TIMESTAMPTZ,
    fetched_at          TIMESTAMPTZ      NOT NULL,
    created_at          TIMESTAMPTZ      NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ      NOT NULL DEFAULT now(),

    CONSTRAINT uq_storm_alarms_source_alarm
        UNIQUE (source, source_alarm_id)
);

CREATE INDEX IF NOT EXISTS ix_storm_alarms_alert_level
    ON storm_alarms (alert_level);

CREATE INDEX IF NOT EXISTS ix_storm_alarms_event
    ON storm_alarms (event_type, event_id);

CREATE INDEX IF NOT EXISTS ix_storm_alarms_published_at
    ON storm_alarms (published_at);