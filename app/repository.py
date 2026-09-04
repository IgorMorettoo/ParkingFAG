from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.request import Request, urlopen

from .domain import ParkingReading


class MemoryReadingRepository:
    def __init__(self) -> None:
        self._readings: list[dict[str, Any]] = []

    def save(self, reading: ParkingReading) -> dict[str, Any]:
        record = {"id": len(self._readings) + 1, **reading.to_dict()}
        self._readings.append(record)
        return record

    def latest(self) -> dict[str, Any] | None:
        return self._readings[-1] if self._readings else None


class SupabaseReadingRepository:
    def __init__(
        self,
        url: str,
        service_role_key: str,
        transport: Callable[..., Any] = urlopen,
    ) -> None:
        self.endpoint = f"{url.rstrip('/')}/rest/v1/parking_readings"
        self.key = service_role_key
        self.transport = transport

    def _request(self, method: str, *, query: str = "", body: dict[str, Any] | None = None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            f"{self.endpoint}{query}",
            data=data,
            method=method,
            headers={
                "apikey": self.key,
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
        )
        with self.transport(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def save(self, reading: ParkingReading) -> dict[str, Any]:
        result = self._request("POST", body=reading.to_dict())
        return result[0]

    def latest(self) -> dict[str, Any] | None:
        result = self._request(
            "GET", query="?select=*&order=captured_at.desc&limit=1"
        )
        return result[0] if result else None
