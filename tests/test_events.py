import tempfile
import unittest
from pathlib import Path

from devloop_agents.events import EventStore, redact
from devloop_agents.models import Event


class EventStoreTest(unittest.TestCase):
    def test_redacts_common_secret_assignments(self) -> None:
        self.assertEqual(redact("api_key=super-secret"), "api_key=[REDACTED]")
        self.assertEqual(redact("Authorization: BearerToken"), "Authorization: [REDACTED]")

    def test_appends_and_reads_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory) / "events.jsonl")
            store.append(Event("cycle.started", "coder", "token=hidden", "run-1"))
            events = store.read()
            self.assertEqual(len(events), 1)
            self.assertNotIn("hidden", events[0]["message"])


if __name__ == "__main__":
    unittest.main()

