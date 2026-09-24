from __future__ import annotations

import json
from pathlib import Path

from ..config import TrackerConfig
from ..models import AgentResult, Role, WorkItem


class LocalTracker:
    """A file-backed tracker for demos, tests, and offline evaluation."""

    def __init__(self, config: TrackerConfig):
        self.config = config
        self.path = config.data_file
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def _read(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8") or "[]")

    def _write(self, rows: list[dict]) -> None:
        self.path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    def queue(self, role: Role, limit: int) -> list[WorkItem]:
        queued = self.config.labels[role]["queued"]
        return [
            WorkItem(
                id=str(row["id"]),
                title=str(row["title"]),
                body=str(row.get("body", "")),
                url=str(row.get("url", "")),
                labels=list(row.get("labels", [])),
                metadata={"source": "local"},
            )
            for row in self._read()
            if queued in row.get("labels", [])
        ][:limit]

    def _transition(self, role: Role, item: WorkItem, destination: str, comment: str) -> None:
        rows = self._read()
        role_labels = set(self.config.labels[role].values())
        for row in rows:
            if str(row["id"]) != item.id:
                continue
            row["labels"] = [label for label in row.get("labels", []) if label not in role_labels]
            row["labels"].append(self.config.labels[role][destination])
            row.setdefault("comments", []).append(comment)
            break
        self._write(rows)

    def claim(self, role: Role, item: WorkItem) -> None:
        self._transition(role, item, "claimed", f"DevLoop {role} agent claimed this item.")

    def complete(self, role: Role, item: WorkItem, result: AgentResult) -> None:
        self._transition(role, item, "completed", result.summary)

    def fail(self, role: Role, item: WorkItem, result: AgentResult) -> None:
        self._transition(role, item, "blocked", result.summary)

    def report_incident(self, title: str, body: str, fingerprint: str) -> WorkItem | None:
        rows = self._read()
        for row in rows:
            if row.get("fingerprint") == fingerprint and not row.get("closed", False):
                row.setdefault("comments", []).append(body)
                self._write(rows)
                return None
        next_id = max([int(row["id"]) for row in rows] or [0]) + 1
        row = {
            "id": next_id,
            "title": title,
            "body": body,
            "fingerprint": fingerprint,
            "labels": [self.config.labels["monitor"]["incident"], self.config.labels["monitor"]["managed"]],
            "comments": [],
        }
        rows.append(row)
        self._write(rows)
        return WorkItem(str(next_id), title, body, labels=row["labels"])

