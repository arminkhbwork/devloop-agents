import json
import tempfile
import unittest
from pathlib import Path

from devloop_agents.adapters.local import LocalTracker
from devloop_agents.config import DEFAULT_LABELS, TrackerConfig
from devloop_agents.models import AgentResult


class LocalTrackerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "issues.json"
        self.path.write_text(
            json.dumps([{"id": 7, "title": "Work", "labels": ["agent:code", "priority:high"]}]),
            encoding="utf-8",
        )
        self.tracker = LocalTracker(TrackerConfig(data_file=self.path, labels=DEFAULT_LABELS))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_transitions_preserve_unrelated_labels(self) -> None:
        item = self.tracker.queue("coder", 1)[0]
        self.tracker.claim("coder", item)
        row = json.loads(self.path.read_text(encoding="utf-8"))[0]
        self.assertIn("priority:high", row["labels"])
        self.assertIn("agent:in-progress", row["labels"])
        self.tracker.complete("coder", item, AgentResult("completed", "Done"))
        row = json.loads(self.path.read_text(encoding="utf-8"))[0]
        self.assertIn("agent:review", row["labels"])

    def test_incident_is_deduplicated_by_fingerprint(self) -> None:
        created = self.tracker.report_incident("Down", "First", "stable-fingerprint")
        duplicate = self.tracker.report_incident("Down", "Again", "stable-fingerprint")
        self.assertIsNotNone(created)
        self.assertIsNone(duplicate)
        rows = json.loads(self.path.read_text(encoding="utf-8"))
        incidents = [row for row in rows if row.get("fingerprint") == "stable-fingerprint"]
        self.assertEqual(len(incidents), 1)
        self.assertIn("Again", incidents[0]["comments"])


if __name__ == "__main__":
    unittest.main()

