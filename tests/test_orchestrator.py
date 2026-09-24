import json
import tempfile
import unittest
from pathlib import Path

from devloop_agents.config import load_config
from devloop_agents.orchestrator import Orchestrator


class OrchestratorSafetyTest(unittest.TestCase):
    def test_dry_run_provider_never_mutates_tracker_even_with_apply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            issues = root / "issues.json"
            issues.write_text(
                json.dumps([{"id": 1, "title": "Safe dry run", "labels": ["agent:code"]}]),
                encoding="utf-8",
            )
            config = root / "devloop.toml"
            config.write_text(
                """
[project]
name = "Test"
workspace = "."

[tracker]
provider = "local"
data_file = "issues.json"

[runner]
provider = "dry-run"

[storage]
state_path = "state.db"
events_path = "events.jsonl"
artifacts_path = "artifacts"
""",
                encoding="utf-8",
            )
            before = issues.read_text(encoding="utf-8")
            result = Orchestrator(load_config(config)).run_cycle("coder", apply=True)
            self.assertEqual(result, 0)
            self.assertEqual(issues.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
