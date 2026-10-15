"""Shared typed contracts. Stdlib-only so they are testable without third-party installs.
(When FastAPI/Pydantic are available these map 1:1 onto Pydantic schemas.)"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from typing import Any, Optional
import re


class ValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass
class TripSpec:
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[date] = None
    return_date: Optional[date] = None
    duration_days: Optional[int] = None
    travelers: int = 1
    budget: Optional[float] = None
    currency: str = "USD"
    interests: list[str] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    client_date: Optional[date] = None

    REQUIRED = ("origin", "destination", "budget", "currency")

    def __post_init__(self):
        from datetime import timedelta
        if self.departure_date and self.duration_days and not self.return_date:
            self.return_date = self.departure_date + timedelta(days=self.duration_days)
        elif self.departure_date and self.return_date and not self.duration_days:
            self.duration_days = max(1, (self.return_date - self.departure_date).days)
        self.validate()

    def missing(self) -> list[str]:
        """Fields the concierge must still ask about."""
        m = [f for f in self.REQUIRED if not getattr(self, f)]
        if not (self.departure_date or self.duration_days):
            m.append("departure_date_or_duration")
        return m

    def validate(self, reference_today: Optional[date] = None) -> "TripSpec":
        errs = []
        if self.travelers < 1:
            errs.append("travelers must be >= 1")
        if self.budget is not None and self.budget <= 0:
            errs.append("budget must be > 0")
        if self.currency and not re.fullmatch(r"[A-Z]{3}", self.currency):
            errs.append("currency must be a 3-letter ISO code")

        if self.origin and self.destination:
            if self.origin.strip().lower() == self.destination.strip().lower():
                errs.append("Destination cannot be the same as origin")

        # Dynamic determination of today with international timezone boundary awareness
        utc_today = datetime.now(timezone.utc).date()
        local_today = date.today()
        effective_today = reference_today if reference_today is not None else (
            self.client_date if self.client_date is not None else min(local_today, utc_today)
        )

        if self.departure_date:
            if self.departure_date < effective_today:
                errs.append(
                    f"Departure date ({self.departure_date.isoformat()}) cannot be in the past. "
                    f"Earliest allowed departure date is {effective_today.isoformat()}."
                )

        if self.departure_date and self.return_date:
            if self.return_date < self.departure_date:
                errs.append(
                    f"Return date ({self.return_date.isoformat()}) cannot be before departure date ({self.departure_date.isoformat()})."
                )
            elif self.duration_days is not None:
                cal_nights = (self.return_date - self.departure_date).days
                cal_days = cal_nights + 1
                if self.duration_days not in (cal_nights, cal_days):
                    errs.append(
                        f"Inconsistent duration: duration_days ({self.duration_days}) does not match departure_date "
                        f"and return_date ({cal_nights} nights / {cal_days} calendar days)"
                    )

        if self.duration_days is not None and self.duration_days < 1:
            errs.append("duration_days must be >= 1")

        if errs:
            raise ValidationError(errs)
        return self

    @classmethod
    def from_dict(cls, d: dict, reference_today: Optional[date] = None) -> "TripSpec":
        d = dict(d)
        for k in ("departure_date", "return_date", "client_date"):
            if isinstance(d.get(k), str):
                try:
                    d[k] = date.fromisoformat(d[k])
                except ValueError:
                    raise ValidationError([f"Invalid {k} format: not an ISO date"])
        allowed = set(cls.__dataclass_fields__) - {"REQUIRED"}
        unknown = set(d) - allowed
        if unknown:
            raise ValidationError([f"unknown fields: {sorted(unknown)}"])
        try:
            return cls(**d).validate(reference_today=reference_today)
        except TypeError as e:
            raise ValidationError([str(e)])

    def to_dict(self) -> dict:
        out = asdict(self)
        for k in ("departure_date", "return_date", "client_date"):
            if out.get(k):
                out[k] = out[k].isoformat()
        return out


@dataclass
class ProviderResult:
    """Every provider call returns this. `status` is never faked:
    ok | unconfigured | error. `source` labels where data came from."""
    provider: str
    status: str
    data: Any = None
    message: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def ok(self) -> bool:
        return self.status == "ok"
