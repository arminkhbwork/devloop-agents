from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Iterable

from .models import Event

_SENSITIVE = re.compile(
    r"(?i)(authorization|api[_-]?key|access[_-]?token|token|secret|password)([\"'=: ]+)([^\s\"']+)"
)


def redact(value: str) -> str:
    return _SENSITIVE.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", value)


def redact_values(value: str, secrets: list[str]) -> str:
    redacted = redact(value)
    for secret in sorted({secret for secret in secrets if len(secret) >= 8}, key=len, reverse=True):
        redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


class EventStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: Event) -> None:
        payload = event.to_dict()
        payload["message"] = redact(payload["message"])
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(serialized + "\n")

    def read(self, limit: int = 200) -> list[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        events: list[dict] = []
        for line in lines:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def costs(self) -> Iterable[float]:
        for event in self.read(limit=10000):
            cost = event.get("data", {}).get("cost_usd")
            if isinstance(cost, (int, float)):
                yield float(cost)
