from __future__ import annotations

from typing import Protocol

from ..models import AgentResult, Role, WorkItem


class Tracker(Protocol):
    def queue(self, role: Role, limit: int) -> list[WorkItem]: ...

    def claim(self, role: Role, item: WorkItem) -> None: ...

    def complete(self, role: Role, item: WorkItem, result: AgentResult) -> None: ...

    def fail(self, role: Role, item: WorkItem, result: AgentResult) -> None: ...

    def report_incident(self, title: str, body: str, fingerprint: str) -> WorkItem | None: ...

