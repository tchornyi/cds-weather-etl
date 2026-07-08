"""Extract global tropical-cyclone alarms from the GDACS RSS feed."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

DEFAULT_FEED_URL = "https://www.gdacs.org/xml/rss_tc_7d.xml"
REQUEST_TIMEOUT = 60.0


def fetch_storm_alarms(feed_url: str = DEFAULT_FEED_URL) -> str:
    """Return the raw GDACS tropical-cyclone RSS XML."""
    logger.info("Fetching storm alarms from %s", feed_url)
    with httpx.Client(headers={"User-Agent": "eu-weather-etl/0.1"}) as client:
        response = client.get(feed_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text