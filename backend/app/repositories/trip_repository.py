from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass
class TripRecord:
    trip_id: str
    user_id: str
    destination: str
    origin: str
    status: str = "draft"
    metadata: dict[str, Any] = field(default_factory=dict)


class InMemoryTripRepository:
    """Small repository implementation used before a live database is configured."""

    def __init__(self):
        self._records: dict[str, TripRecord] = {}

    def create(self, record: TripRecord) -> TripRecord:
        self._records[record.trip_id] = record
        return record

    def get_by_id(self, trip_id: str) -> TripRecord | None:
        return self._records.get(trip_id)

    def list_by_user(self, user_id: str) -> list[TripRecord]:
        return [record for record in self._records.values() if record.user_id == user_id]

    def update(self, trip_id: str, **kwargs: Any) -> TripRecord | None:
        record = self._records.get(trip_id)
        if record is None:
            return None
        for key, value in kwargs.items():
            setattr(record, key, value)
        return record

    def delete(self, trip_id: str) -> bool:
        return self._records.pop(trip_id, None) is not None

    def list(self) -> Iterable[TripRecord]:
        return list(self._records.values())
