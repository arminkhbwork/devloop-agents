from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

Role = Literal["coder", "qa", "monitor"]
ResultStatus = Literal["completed", "blocked", "failed", "skipped", "dry_run"]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class WorkItem:
    id: str
    title: str
    body: str = ""
    url: str = ""
    labels: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentResult:
    status: ResultStatus
    summary: str
    details: str = ""
    pull_request_url: str | None = None
    cost_usd: float | None = None
    turns: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Event:
    event: str
    role: Role
    message: str
    run_id: str
    item_id: str | None = None
    level: Literal["info", "warning", "error"] = "info"
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

