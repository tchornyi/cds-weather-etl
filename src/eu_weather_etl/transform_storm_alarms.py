"""Transform GDACS RSS items into upsertable storm-alarm records."""

from __future__ import annotations

import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

SOURCE = "GDACS"
DEFAULT_EVENT_TYPE = "TC"
_HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class StormAlarmRecord:
    source: str
    source_alarm_id: str
    event_type: str | None
    event_id: str | None
    episode_id: str | None
    name: str | None
    title: str
    description: str | None
    link: str | None
    alert_level: str | None
    severity_value: float | None
    severity_unit: str | None
    country: str | None
    iso3: str | None
    latitude: float | None
    longitude: float | None
    from_date: datetime | None
    to_date: datetime | None
    published_at: datetime | None
    fetched_at: datetime


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child(element: ET.Element, name: str) -> ET.Element | None:
    name = name.lower()
    for child in element:
        if _local_name(child.tag) == name:
            return child
    return None


def _child_text(element: ET.Element, *names: str) -> str | None:
    for name in names:
        child = _child(element, name)
        if child is not None and child.text:
            return child.text.strip()
    return None


def _clean_text(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _HTML_TAG_RE.sub(" ", unescape(value))
    cleaned = " ".join(cleaned.split())
    return cleaned or None


def _to_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    value = value.strip()
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        parsed = None
    if parsed is not None:
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    for fmt in (
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    logger.warning("Could not parse GDACS datetime: %s", value)
    return None


def _query_value(link: str | None, name: str) -> str | None:
    if not link:
        return None
    values = parse_qs(urlparse(link).query).get(name)
    return values[0] if values else None


def _coordinates(item: ET.Element) -> tuple[float | None, float | None]:
    latitude = _to_float(_child_text(item, "lat", "latitude"))
    longitude = _to_float(_child_text(item, "long", "lon", "longitude"))
    point = _child_text(item, "point")
    if point and (latitude is None or longitude is None):
        parts = point.replace(",", " ").split()
        if len(parts) >= 2:
            latitude = latitude if latitude is not None else _to_float(parts[0])
            longitude = longitude if longitude is not None else _to_float(parts[1])
    return latitude, longitude


def _severity(item: ET.Element) -> tuple[float | None, str | None]:
    element = _child(item, "severity")
    if element is None:
        return None, None
    value = _to_float(element.attrib.get("value") or (element.text or "").strip())
    unit = element.attrib.get("unit")
    return value, unit


def _source_alarm_id(
    event_type: str | None,
    event_id: str | None,
    episode_id: str | None,
    guid: str | None,
    link: str | None,
    title: str,
    published_at: datetime | None,
) -> str:
    if event_type and event_id and episode_id:
        return f"{event_type}:{event_id}:{episode_id}"
    if event_type and event_id:
        return f"{event_type}:{event_id}"
    if guid:
        return guid
    if link:
        return link

    seed = "|".join(
        part
        for part in (
            title,
            published_at.isoformat() if published_at else "",
        )
        if part
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _record_from_item(item: ET.Element, fetched_at: datetime) -> StormAlarmRecord:
    title = _clean_text(_child_text(item, "title")) or "Untitled GDACS storm alarm"
    description = _clean_text(_child_text(item, "description"))
    link = _child_text(item, "link")
    guid = _child_text(item, "guid")
    published_at = _parse_datetime(_child_text(item, "pubDate", "pubdate"))
    event_type = (
        _child_text(item, "eventtype")
        or _query_value(link, "eventtype")
        or DEFAULT_EVENT_TYPE
    )
    event_id = _child_text(item, "eventid") or _query_value(link, "eventid")
    episode_id = _child_text(item, "episodeid") or _query_value(link, "episodeid")
    severity_value, severity_unit = _severity(item)
    latitude, longitude = _coordinates(item)

    return StormAlarmRecord(
        source=SOURCE,
        source_alarm_id=_source_alarm_id(
            event_type,
            event_id,
            episode_id,
            guid,
            link,
            title,
            published_at,
        ),
        event_type=event_type,
        event_id=event_id,
        episode_id=episode_id,
        name=_clean_text(_child_text(item, "eventname", "name")),
        title=title,
        description=description,
        link=link,
        alert_level=_child_text(item, "alertlevel"),
        severity_value=severity_value,
        severity_unit=severity_unit,
        country=_clean_text(_child_text(item, "country")),
        iso3=_child_text(item, "iso3"),
        latitude=latitude,
        longitude=longitude,
        from_date=_parse_datetime(_child_text(item, "fromdate")),
        to_date=_parse_datetime(_child_text(item, "todate")),
        published_at=published_at,
        fetched_at=fetched_at,
    )


def transform_storm_alarms(xml_text: str, fetched_at: datetime) -> list[StormAlarmRecord]:
    """Return normalized records from a GDACS RSS XML document."""
    root = ET.fromstring(xml_text)
    records: list[StormAlarmRecord] = []
    for item in (node for node in root.iter() if _local_name(node.tag) == "item"):
        try:
            records.append(_record_from_item(item, fetched_at))
        except Exception:  # noqa: BLE001 - one bad item should not sink the run
            logger.exception("Failed to transform a GDACS storm alarm item")
    return records