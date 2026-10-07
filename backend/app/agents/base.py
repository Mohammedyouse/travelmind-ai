from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


@dataclass
class AgentOutput:
    name: str
    status: str
    summary: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name or self.status not in {"ok", "needs_input", "unconfigured", "error"}:
            raise ValueError("agent output requires a name and supported status")
        if not isinstance(self.summary, str) or not isinstance(self.data, dict):
            raise ValueError("agent output summary and data have invalid types")
        for field_name in ("missing_fields", "errors", "recommendations"):
            values = getattr(self, field_name)
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise ValueError(f"agent output {field_name} must be a list of strings")


class TravelAgent:
    """Shared base for TravelMind AI specialist agents."""

    name: str = "base_agent"
    description: str = "Generic travel agent"
    requires: tuple[str, ...] = ()

    def validate_context(self, context: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        for field_name in self.requires:
            if field_name not in context or context.get(field_name) in (None, "", [], {}):
                missing.append(field_name)
        return missing

    def run(self, context: dict[str, Any]) -> AgentOutput:
        raise NotImplementedError

    def _build_output(
        self,
        *,
        status: str,
        summary: str,
        data: dict[str, Any] | None = None,
        missing_fields: Iterable[str] = (),
        errors: Iterable[str] = (),
        recommendations: Iterable[str] = (),
    ) -> AgentOutput:
        return AgentOutput(
            name=self.name,
            status=status,
            summary=summary,
            data=data or {},
            missing_fields=list(missing_fields),
            errors=list(errors),
            recommendations=list(recommendations),
        )
