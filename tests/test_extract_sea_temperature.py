import unittest
from unittest.mock import patch

import httpx

from eu_weather_etl.extract_sea_temperature import (
    RetryOptions,
    _request_batch,
    fetch_sea_temperatures,
)
from eu_weather_etl.sea_places import SeaPlace


class _FakeResponse:
    def __init__(self, status_code: int, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}
        self.request = httpx.Request("GET", "https://example.test/marine")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code} error",
                request=self.request,
                response=self,
            )

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def get(self, url, *, params, timeout):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class SeaTemperatureExtractTests(unittest.TestCase):
    def test_retries_429_and_respects_retry_after(self):
        place = SeaPlace("Mediterranean", "Barcelona", "Spain", 41.373, 2.188)
        client = _FakeClient(
            [
                _FakeResponse(429, headers={"Retry-After": "0.25"}),
                _FakeResponse(
                    200,
                    payload={"hourly": {"time": [], "sea_surface_temperature": []}},
                ),
            ]
        )
        sleeps: list[float] = []

        records = _request_batch(
            client,
            [place],
            forecast_days=1,
            past_days=0,
            retry_options=RetryOptions(
                max_attempts=2,
                initial_delay_seconds=10.0,
                backoff=2.0,
                jitter_seconds=0.0,
            ),
            sleep=sleeps.append,
        )

        self.assertEqual(client.calls, 2)
        self.assertEqual(sleeps, [0.25])
        self.assertEqual(records, [{"hourly": {"time": [], "sea_surface_temperature": []}}])

    def test_retries_transport_errors(self):
        place = SeaPlace("Black Sea", "Odesa", "Ukraine", 46.4825, 30.7233)
        request = httpx.Request("GET", "https://example.test/marine")
        client = _FakeClient(
            [
                httpx.ConnectError("network hiccup", request=request),
                _FakeResponse(200, payload=[]),
            ]
        )
        sleeps: list[float] = []

        records = _request_batch(
            client,
            [place],
            forecast_days=1,
            past_days=0,
            retry_options=RetryOptions(
                max_attempts=2,
                initial_delay_seconds=3.0,
                backoff=2.0,
                jitter_seconds=0.0,
            ),
            sleep=sleeps.append,
        )

        self.assertEqual(client.calls, 2)
        self.assertEqual(sleeps, [3.0])
        self.assertEqual(records, [])

    def test_fetch_waits_between_batches(self):
        places = (
            SeaPlace("Mediterranean", "Barcelona", "Spain", 41.373, 2.188),
            SeaPlace("Black Sea", "Odesa", "Ukraine", 46.4825, 30.7233),
        )
        fake_client = _FakeClient(
            [
                _FakeResponse(200, payload={"latitude": places[0].latitude}),
                _FakeResponse(200, payload={"latitude": places[1].latitude}),
            ]
        )
        sleeps: list[float] = []

        with patch("eu_weather_etl.extract_sea_temperature.httpx.Client", return_value=fake_client):
            pairs = fetch_sea_temperatures(
                list(places),
                forecast_days=1,
                past_days=0,
                retry_options=RetryOptions(jitter_seconds=0.0),
                sleep=sleeps.append,
                batch_delay_seconds=1.5,
                batch_size=1,
            )

        self.assertEqual(fake_client.calls, 2)
        self.assertEqual(sleeps, [1.5])
        self.assertEqual([place.place for place, _ in pairs], ["Barcelona", "Odesa"])


if __name__ == "__main__":
    unittest.main()
