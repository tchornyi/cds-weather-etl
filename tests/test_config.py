"""Database configuration resolution (`eu_weather_etl.config`).

Covers the CDS shared-Connection contract — the portal injects an attached
Connection as {PREFIX}_HOST/_PORT/_DB/_USER/_PASSWORD/_URI, with CDS_DB_PREFIX
naming which attachment this ETL reads — and the legacy DATABASE_URL / PG*
fallback kept for local runs.
"""

from __future__ import annotations

import pytest

from eu_weather_etl.config import database_connection_kwargs

CONNECTION_VARS = (
    "CDS_DB_PREFIX",
    "DB_URI", "DB_HOST", "DB_PORT", "DB_DB", "DB_USER", "DB_PASSWORD",
    "WEATHER_URI", "WEATHER_HOST", "WEATHER_PORT", "WEATHER_DB",
    "WEATHER_USER", "WEATHER_PASSWORD",
    "DATABASE_URL", "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGSSLMODE",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """A developer .env is auto-loaded at import time — start from a blank slate."""
    for name in CONNECTION_VARS:
        monkeypatch.delenv(name, raising=False)


def test_connection_uri_wins_over_database_url(monkeypatch):
    monkeypatch.setenv("CDS_DB_PREFIX", "WEATHER")
    monkeypatch.setenv("WEATHER_URI", "postgres://c:s@connhost:5432/weather_observation")
    monkeypatch.setenv("DATABASE_URL", "postgresql://legacy@legacyhost/legacy")

    assert database_connection_kwargs() == {
        "conninfo": "postgres://c:s@connhost:5432/weather_observation"
    }


def test_connection_parts_are_assembled_when_uri_absent(monkeypatch):
    monkeypatch.setenv("CDS_DB_PREFIX", "WEATHER")
    monkeypatch.setenv("WEATHER_HOST", "connhost")
    monkeypatch.setenv("WEATHER_PORT", "6432")
    monkeypatch.setenv("WEATHER_DB", "weather_observation")
    monkeypatch.setenv("WEATHER_USER", "c")
    monkeypatch.setenv("WEATHER_PASSWORD", "s")

    assert database_connection_kwargs() == {
        "host": "connhost",
        "dbname": "weather_observation",
        "user": "c",
        "port": 6432,
        "password": "s",
    }


def test_db_env_prefix_defaults_to_DB(monkeypatch):
    monkeypatch.setenv("DB_URI", "postgres://c:s@connhost:5432/weather_observation")
    assert database_connection_kwargs() == {
        "conninfo": "postgres://c:s@connhost:5432/weather_observation"
    }


def test_partial_connection_vars_fall_back_to_legacy_config(monkeypatch):
    # Prefix set but incomplete — must not shadow a working DATABASE_URL.
    monkeypatch.setenv("CDS_DB_PREFIX", "WEATHER")
    monkeypatch.setenv("WEATHER_HOST", "connhost")
    monkeypatch.setenv("DATABASE_URL", "postgresql://legacy@legacyhost/legacy")

    assert database_connection_kwargs() == {"conninfo": "postgresql://legacy@legacyhost/legacy"}


def test_legacy_pg_vars_still_supported(monkeypatch):
    monkeypatch.setenv("PGHOST", "legacyhost")
    monkeypatch.setenv("PGDATABASE", "weather_observation")
    monkeypatch.setenv("PGUSER", "sds")
    monkeypatch.setenv("PGPASSWORD", "sds")
    monkeypatch.setenv("PGSSLMODE", "prefer")

    assert database_connection_kwargs() == {
        "host": "legacyhost",
        "dbname": "weather_observation",
        "user": "sds",
        "password": "sds",
        "sslmode": "prefer",
    }


def test_error_names_the_connection_prefix_when_nothing_is_configured(monkeypatch):
    monkeypatch.setenv("CDS_DB_PREFIX", "WEATHER")
    with pytest.raises(RuntimeError, match="WEATHER_URI"):
        database_connection_kwargs()
